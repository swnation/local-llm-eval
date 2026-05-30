import io
import json
import logging
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import hpz2_ollama_compat_llamacpp_shim as shim


def _json_bytes(payload):
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class ServerThread:
    def __init__(self, server):
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    @property
    def url(self):
        host, port = self.server.server_address
        return f"http://127.0.0.1:{port}"


class FakeLlamaHandler(BaseHTTPRequestHandler):
    response_status = HTTPStatus.OK
    response_payload = {
        "choices": [{"message": {"content": '{"summary":"ok","citations":["[rule:drug:sme]"]}'}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
    }
    requests = []

    def log_message(self, format, *args):
        return

    def _send_json(self, status, payload):
        data = _json_bytes(payload)
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        FakeLlamaHandler.requests.append(
            {
                "path": self.path,
                "payload": json.loads(body.decode("utf-8")),
            }
        )
        self._send_json(self.response_status, self.response_payload)


def make_fake_llama_server(status=HTTPStatus.OK, payload=None):
    FakeLlamaHandler.response_status = status
    FakeLlamaHandler.response_payload = payload or {
        "choices": [{"message": {"content": '{"summary":"ok","citations":["[rule:drug:sme]"]}'}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
    }
    FakeLlamaHandler.requests = []
    return ThreadingHTTPServer(("127.0.0.1", 0), FakeLlamaHandler)


def make_shim_server(upstream_base_url, *, model_map=None, schema_mode="json_object"):
    config = shim.ShimConfig(
        upstream_base_url=shim.normalize_upstream_base_url(upstream_base_url),
        model_map=model_map or {},
        request_timeout_seconds=5,
        health_timeout_seconds=2,
        schema_mode=schema_mode,
    )
    return shim.ShimHTTPServer(("127.0.0.1", 0), config)


def post_json(url, payload):
    request = urllib.request.Request(
        url,
        data=_json_bytes(payload),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def get_json(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


class Hpz2OllamaCompatShimTest(unittest.TestCase):
    def test_generate_translates_to_chat_completions_and_returns_ollama_response(self):
        with ServerThread(make_fake_llama_server()) as llama_server:
            with ServerThread(
                make_shim_server(
                    llama_server.url + "/v1",
                    model_map={"hpz2-primary": "hpz2-l2-qwen36-35b-a3b"},
                )
            ) as shim_server:
                status, body = post_json(
                    shim_server.url + "/api/generate",
                    {
                        "model": "hpz2-primary",
                        "system": "SYSTEM_TEXT",
                        "prompt": "PROMPT_TEXT",
                        "stream": False,
                        "format": {"type": "object"},
                    },
                )

        self.assertEqual(status, 200)
        self.assertEqual(body["response"], '{"summary":"ok","citations":["[rule:drug:sme]"]}')
        self.assertTrue(body["done"])
        self.assertEqual(body["prompt_eval_count"], 11)
        self.assertEqual(body["eval_count"], 7)

        self.assertEqual(len(FakeLlamaHandler.requests), 1)
        upstream = FakeLlamaHandler.requests[0]
        self.assertEqual(upstream["path"], "/v1/chat/completions")
        self.assertEqual(upstream["payload"]["model"], "hpz2-l2-qwen36-35b-a3b")
        self.assertEqual(
            upstream["payload"]["messages"],
            [
                {"role": "system", "content": "SYSTEM_TEXT"},
                {"role": "user", "content": "PROMPT_TEXT"},
            ],
        )
        self.assertFalse(upstream["payload"]["stream"])
        self.assertEqual(upstream["payload"]["response_format"], {"type": "json_object"})

    def test_json_schema_mode_forwards_emr_format_schema(self):
        explain_schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "citations": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["summary", "citations"],
            "additionalProperties": False,
        }
        with ServerThread(make_fake_llama_server()) as llama_server:
            with ServerThread(
                make_shim_server(
                    llama_server.url + "/v1",
                    schema_mode="json_schema",
                )
            ) as shim_server:
                status, body = post_json(
                    shim_server.url + "/api/generate",
                    {
                        "model": "hpz2-l2-qwen36-35b-a3b",
                        "system": "SYSTEM_TEXT",
                        "prompt": "PROMPT_TEXT",
                        "stream": False,
                        "format": explain_schema,
                    },
                )

        self.assertEqual(status, 200)
        self.assertEqual(body["response"], '{"summary":"ok","citations":["[rule:drug:sme]"]}')
        self.assertEqual(len(FakeLlamaHandler.requests), 1)
        upstream = FakeLlamaHandler.requests[0]
        self.assertEqual(
            upstream["payload"]["response_format"],
            {
                "type": "json_schema",
                "json_schema": {
                    "name": "explain_response",
                    "strict": True,
                    "schema": explain_schema,
                },
            },
        )

    def test_json_schema_mode_requires_format_schema_without_upstream_call(self):
        with ServerThread(make_fake_llama_server()) as llama_server:
            with ServerThread(
                make_shim_server(
                    llama_server.url + "/v1",
                    schema_mode="json_schema",
                )
            ) as shim_server:
                request = urllib.request.Request(
                    shim_server.url + "/api/generate",
                    data=_json_bytes({"model": "m", "prompt": "p", "stream": False}),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=5)
                body = caught.exception.read().decode("utf-8")

        self.assertEqual(caught.exception.code, 400)
        self.assertIn("format schema must be a JSON object", body)
        self.assertEqual(FakeLlamaHandler.requests, [])

    def test_none_schema_mode_omits_response_format(self):
        with ServerThread(make_fake_llama_server()) as llama_server:
            with ServerThread(
                make_shim_server(llama_server.url + "/v1", schema_mode="none")
            ) as shim_server:
                status, _body = post_json(
                    shim_server.url + "/api/generate",
                    {
                        "model": "hpz2-l2-qwen36-35b-a3b",
                        "prompt": "PROMPT_TEXT",
                        "stream": False,
                    },
                )

        self.assertEqual(status, 200)
        self.assertNotIn("response_format", FakeLlamaHandler.requests[0]["payload"])

    def test_streaming_request_fails_closed_without_upstream_call(self):
        with ServerThread(make_fake_llama_server()) as llama_server:
            with ServerThread(make_shim_server(llama_server.url + "/v1")) as shim_server:
                request = urllib.request.Request(
                    shim_server.url + "/api/generate",
                    data=_json_bytes({"model": "m", "prompt": "p", "stream": True}),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=5)
                body = caught.exception.read().decode("utf-8")

        self.assertEqual(caught.exception.code, 400)
        self.assertIn("stream=true is not supported", body)
        self.assertEqual(FakeLlamaHandler.requests, [])

    def test_upstream_404_maps_to_model_not_found_for_emr_client(self):
        with ServerThread(make_fake_llama_server(status=HTTPStatus.NOT_FOUND, payload={"error": "model not found"})) as llama_server:
            with ServerThread(make_shim_server(llama_server.url + "/v1")) as shim_server:
                request = urllib.request.Request(
                    shim_server.url + "/api/generate",
                    data=_json_bytes({"model": "missing-model", "prompt": "p", "stream": False}),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=5)
                body = caught.exception.read().decode("utf-8")

        self.assertEqual(caught.exception.code, 404)
        self.assertIn("model not found", body.lower())

    def test_health_reports_upstream_status(self):
        with ServerThread(make_fake_llama_server()) as llama_server:
            with ServerThread(make_shim_server(llama_server.url + "/v1")) as shim_server:
                status, body = get_json(shim_server.url + "/health")

        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["upstream"]["status"], "ok")
        self.assertEqual(body["target"], llama_server.url + "/v1")

    def test_logs_do_not_include_prompt_system_or_response_content(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("hpz2_ollama_compat_llamacpp_shim")
        old_level = logger.level
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        try:
            payload = {
                "choices": [{"message": {"content": "SECRET_RESPONSE_TOKEN"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
            with ServerThread(make_fake_llama_server(payload=payload)) as llama_server:
                with ServerThread(make_shim_server(llama_server.url + "/v1")) as shim_server:
                    post_json(
                        shim_server.url + "/api/generate",
                        {
                            "model": "model",
                            "system": "SECRET_SYSTEM_TOKEN",
                            "prompt": "SECRET_PROMPT_TOKEN",
                            "stream": False,
                        },
                    )
        finally:
            logger.removeHandler(handler)
            logger.setLevel(old_level)

        logs = stream.getvalue()
        self.assertNotIn("SECRET_SYSTEM_TOKEN", logs)
        self.assertNotIn("SECRET_PROMPT_TOKEN", logs)
        self.assertNotIn("SECRET_RESPONSE_TOKEN", logs)
        self.assertIn("request_complete", logs)

    def test_loopback_only_validation(self):
        self.assertEqual(shim.validate_listen_host("127.0.0.1"), "127.0.0.1")
        with self.assertRaises(ValueError):
            shim.validate_listen_host("0.0.0.0")
        with self.assertRaises(ValueError):
            shim.normalize_upstream_base_url("http://192.168.0.1:18080/v1")


if __name__ == "__main__":
    unittest.main()
