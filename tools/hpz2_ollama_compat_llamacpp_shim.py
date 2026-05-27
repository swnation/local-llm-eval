#!/usr/bin/env python3
"""Ollama-compatible local shim for HP Z2 llama.cpp L5 smoke runs.

This server intentionally implements only the narrow contract used by
EMR_AI_24clinic's current ollama_client.py:

  POST /api/generate with stream=false

It translates that request to llama.cpp's OpenAI-compatible
/v1/chat/completions endpoint, then returns an Ollama-shaped JSON response.
The shim never logs prompt, system, response, or request bodies.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse


UrlOpen = Callable[..., object]
LOGGER = logging.getLogger("hpz2_ollama_compat_llamacpp_shim")
LOOPBACK_HOSTS = {"127.0.0.1", "localhost"}


class ClientRequestError(ValueError):
    def __init__(self, status: HTTPStatus, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class UpstreamError(RuntimeError):
    def __init__(self, status: HTTPStatus, message: str, *, upstream_status: int | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.upstream_status = upstream_status


@dataclass(frozen=True)
class ShimConfig:
    upstream_base_url: str = "http://127.0.0.1:18080/v1"
    request_timeout_seconds: float = 300.0
    health_timeout_seconds: float = 2.0
    default_model: str = ""
    model_map: dict[str, str] = field(default_factory=dict)
    max_tokens: int = 8192
    temperature: float = 0.0
    max_request_bytes: int = 4 * 1024 * 1024
    schema_mode: str = "json_object"
    urlopen: UrlOpen = urllib.request.urlopen


class ShimHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], config: ShimConfig):
        super().__init__(server_address, OllamaCompatHandler)
        self.config = config


def normalize_upstream_base_url(raw_url: str) -> str:
    parsed = urlparse(str(raw_url).strip())
    if parsed.scheme != "http":
        raise ValueError("upstream must use http")
    if parsed.hostname not in LOOPBACK_HOSTS:
        raise ValueError("upstream must be localhost or 127.0.0.1")
    if parsed.port is None:
        raise ValueError("upstream must include a port")
    if parsed.params or parsed.query or parsed.fragment:
        raise ValueError("upstream must not include params, query, or fragment")

    path = (parsed.path or "").rstrip("/")
    if path == "":
        path = "/v1"
    if path != "/v1":
        raise ValueError("upstream path must be empty or /v1")
    return f"http://{parsed.hostname}:{parsed.port}{path}"


def validate_listen_host(host: str) -> str:
    normalized = str(host).strip()
    if normalized not in LOOPBACK_HOSTS:
        raise ValueError("listen host must be localhost or 127.0.0.1")
    return normalized


def parse_model_map(items: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"model map must be alias=target: {item}")
        alias, target = item.split("=", 1)
        alias = alias.strip()
        target = target.strip()
        if not alias or not target:
            raise ValueError(f"model map must have non-empty alias and target: {item}")
        result[alias] = target
    return result


def chat_completions_url(config: ShimConfig) -> str:
    return config.upstream_base_url.rstrip("/") + "/chat/completions"


def health_url(config: ShimConfig) -> str:
    return config.upstream_base_url.removesuffix("/v1").rstrip("/") + "/health"


def utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def map_model_name(request_model: str, config: ShimConfig) -> str:
    model = request_model.strip()
    if model in config.model_map:
        return config.model_map[model]
    if not model and config.default_model:
        return config.default_model
    return model


def build_chat_completion_payload(ollama_payload: dict[str, Any], config: ShimConfig) -> tuple[dict[str, Any], str, str]:
    if not isinstance(ollama_payload, dict):
        raise ClientRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")

    stream = ollama_payload.get("stream", False)
    if stream is not False:
        raise ClientRequestError(HTTPStatus.BAD_REQUEST, "stream=true is not supported by this shim")

    prompt = ollama_payload.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        raise ClientRequestError(HTTPStatus.BAD_REQUEST, "prompt must be a non-empty string")

    system = ollama_payload.get("system", "")
    if system is None:
        system = ""
    if not isinstance(system, str):
        raise ClientRequestError(HTTPStatus.BAD_REQUEST, "system must be a string when provided")

    request_model = str(ollama_payload.get("model", "")).strip()
    mapped_model = map_model_name(request_model, config)
    if not mapped_model:
        raise ClientRequestError(HTTPStatus.BAD_REQUEST, "model must be provided or default-model must be set")

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    chat_payload: dict[str, Any] = {
        "model": mapped_model,
        "messages": messages,
        "stream": False,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    if config.schema_mode == "json_object":
        chat_payload["response_format"] = {"type": "json_object"}
    return chat_payload, request_model, mapped_model


def _read_response_body(response: object) -> bytes:
    if hasattr(response, "__enter__"):
        with response as handle:
            return handle.read()
    return response.read()


def _http_status(response: object) -> int:
    if hasattr(response, "status"):
        return int(response.status)
    if hasattr(response, "getcode"):
        return int(response.getcode())
    return 200


def call_upstream_chat(chat_payload: dict[str, Any], config: ShimConfig) -> tuple[str, dict[str, Any], int]:
    request = urllib.request.Request(
        chat_completions_url(config),
        data=json_bytes(chat_payload),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        response = config.urlopen(request, timeout=config.request_timeout_seconds)
        status = _http_status(response)
        body = _read_response_body(response)
    except urllib.error.HTTPError as exc:
        try:
            raw_body = exc.read(8192).decode("utf-8", errors="replace").lower()
        except Exception:
            raw_body = ""
        if exc.code == 404 or "model not found" in raw_body:
            raise UpstreamError(HTTPStatus.NOT_FOUND, "model not found", upstream_status=exc.code) from exc
        raise UpstreamError(HTTPStatus.BAD_GATEWAY, "upstream llama.cpp request failed", upstream_status=exc.code) from exc
    except (socket.timeout, TimeoutError) as exc:
        raise UpstreamError(HTTPStatus.GATEWAY_TIMEOUT, "upstream llama.cpp request timed out") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            raise UpstreamError(HTTPStatus.GATEWAY_TIMEOUT, "upstream llama.cpp request timed out") from exc
        raise UpstreamError(HTTPStatus.SERVICE_UNAVAILABLE, "upstream llama.cpp is unavailable") from exc

    if status >= 400:
        raise UpstreamError(HTTPStatus.BAD_GATEWAY, "upstream llama.cpp request failed", upstream_status=status)

    try:
        parsed = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise UpstreamError(HTTPStatus.BAD_GATEWAY, "upstream llama.cpp returned invalid JSON", upstream_status=status) from exc

    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        raise UpstreamError(HTTPStatus.BAD_GATEWAY, "upstream llama.cpp response has no choices", upstream_status=status)
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise UpstreamError(HTTPStatus.BAD_GATEWAY, "upstream llama.cpp response has no message content", upstream_status=status)
    return content, parsed, status


def build_ollama_response(
    *,
    request_model: str,
    mapped_model: str,
    content: str,
    upstream_response: dict[str, Any],
    latency_ns: int,
) -> dict[str, Any]:
    usage = upstream_response.get("usage") if isinstance(upstream_response.get("usage"), dict) else {}
    return {
        "model": request_model or mapped_model,
        "created_at": utc_timestamp(),
        "response": content,
        "done": True,
        "total_duration": latency_ns,
        "load_duration": 0,
        "prompt_eval_count": usage.get("prompt_tokens", 0),
        "eval_count": usage.get("completion_tokens", 0),
    }


def probe_upstream(config: ShimConfig) -> dict[str, Any]:
    request = urllib.request.Request(health_url(config), method="GET")
    start = time.perf_counter_ns()
    try:
        response = config.urlopen(request, timeout=config.health_timeout_seconds)
        status = _http_status(response)
        _read_response_body(response)
        ok = status < 400
        return {
            "status": "ok" if ok else "unavailable",
            "http_status": status,
            "latency_ms": int((time.perf_counter_ns() - start) / 1_000_000),
        }
    except Exception:
        return {
            "status": "unavailable",
            "http_status": None,
            "latency_ms": int((time.perf_counter_ns() - start) / 1_000_000),
        }


def sanitized_log(event: str, **fields: Any) -> None:
    safe_fields = {key: value for key, value in fields.items() if value is not None}
    LOGGER.info("%s %s", event, json.dumps(safe_fields, ensure_ascii=True, sort_keys=True))


class OllamaCompatHandler(BaseHTTPRequestHandler):
    server_version = "HPZ2OllamaCompatShim/0.1"

    @property
    def config(self) -> ShimConfig:
        return self.server.config  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        data = json_bytes(payload)
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_error_json(self, status: HTTPStatus, message: str) -> None:
        self._send_json(status, {"error": message})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path != "/health":
            self._send_error_json(HTTPStatus.NOT_FOUND, "not found")
            return
        upstream = probe_upstream(self.config)
        self._send_json(
            HTTPStatus.OK,
            {
                "status": "ok",
                "upstream": upstream,
                "target": self.config.upstream_base_url,
            },
        )

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/generate":
            self._send_error_json(HTTPStatus.NOT_FOUND, "not found")
            return

        start = time.perf_counter_ns()
        try:
            payload = self._read_request_json()
            chat_payload, request_model, mapped_model = build_chat_completion_payload(payload, self.config)
            content, upstream_response, upstream_status = call_upstream_chat(chat_payload, self.config)
            latency_ns = time.perf_counter_ns() - start
            self._send_json(
                HTTPStatus.OK,
                build_ollama_response(
                    request_model=request_model,
                    mapped_model=mapped_model,
                    content=content,
                    upstream_response=upstream_response,
                    latency_ns=latency_ns,
                ),
            )
            sanitized_log(
                "request_complete",
                status=200,
                upstream_status=upstream_status,
                model=request_model,
                mapped_model=mapped_model,
                latency_ms=int(latency_ns / 1_000_000),
            )
        except ClientRequestError as exc:
            self._send_error_json(exc.status, exc.message)
            sanitized_log("request_rejected", status=int(exc.status), reason=exc.message)
        except UpstreamError as exc:
            self._send_error_json(exc.status, exc.message)
            sanitized_log(
                "request_upstream_failed",
                status=int(exc.status),
                upstream_status=exc.upstream_status,
                reason=exc.message,
                latency_ms=int((time.perf_counter_ns() - start) / 1_000_000),
            )

    def _read_request_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ClientRequestError(HTTPStatus.LENGTH_REQUIRED, "content-length is required")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ClientRequestError(HTTPStatus.BAD_REQUEST, "content-length must be an integer") from exc
        if length < 0 or length > self.config.max_request_bytes:
            raise ClientRequestError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body is too large")
        body = self.rfile.read(length)
        try:
            parsed = json.loads(body.decode("utf-8"))
        except Exception as exc:
            raise ClientRequestError(HTTPStatus.BAD_REQUEST, "request body must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ClientRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        return parsed


def serve(config: ShimConfig, *, listen_host: str, listen_port: int) -> None:
    listen_host = validate_listen_host(listen_host)
    server = ShimHTTPServer((listen_host, listen_port), config)
    sanitized_log("shim_started", listen_host=listen_host, listen_port=listen_port, upstream=config.upstream_base_url)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        sanitized_log("shim_stopped", listen_host=listen_host, listen_port=listen_port)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HP Z2 Ollama-compatible shim for llama.cpp /v1 chat completions")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=18081)
    parser.add_argument("--upstream", default="http://127.0.0.1:18080/v1")
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    parser.add_argument("--health-timeout-seconds", type=float, default=2.0)
    parser.add_argument("--default-model", default="")
    parser.add_argument("--model-map", action="append", default=[], help="Alias mapping in alias=target form")
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--schema-mode", choices=["json-object", "none"], default="json-object")
    parser.add_argument("--max-request-bytes", type=int, default=4 * 1024 * 1024)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(message)s")
    config = ShimConfig(
        upstream_base_url=normalize_upstream_base_url(args.upstream),
        request_timeout_seconds=args.timeout_seconds,
        health_timeout_seconds=args.health_timeout_seconds,
        default_model=args.default_model,
        model_map=parse_model_map(args.model_map),
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        max_request_bytes=args.max_request_bytes,
        schema_mode="json_object" if args.schema_mode == "json-object" else "none",
    )
    serve(config, listen_host=args.listen_host, listen_port=args.listen_port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
