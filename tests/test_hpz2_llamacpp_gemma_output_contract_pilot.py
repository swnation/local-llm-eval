import copy
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import hpz2_llamacpp_gemma_output_contract_pilot as runner


CONFIG = json.loads((ROOT / "models_config_hpz2_llamacpp_phase2_l2_v0.1.json").read_text(encoding="utf-8"))


class FakeProc:
    pid = 4242
    returncode = None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = 0

    def wait(self, timeout=None):
        self.returncode = 0
        return 0

    def kill(self):
        self.returncode = -9


class GemmaLlamaCppOutputContractPilotTests(unittest.TestCase):
    def run_real_args(self, tmp: str) -> Namespace:
        return Namespace(
            config="models_config_hpz2_llamacpp_phase2_l2_v0.1.json",
            output_root=tmp,
            fallback_args=False,
            confirm_hpz2=True,
            confirm_gemma_llamacpp_output_contract_pilot=True,
        )

    def read_payload(self, tmp: str) -> dict:
        result_dirs = sorted(Path(tmp).glob("gemma_llamacpp_output_contract_pilot_*"))
        self.assertEqual(len(result_dirs), 1)
        return json.loads((result_dirs[0] / "gemma_llamacpp_output_contract_results.json").read_text(encoding="utf-8"))

    def test_json_schema_payload_shape_is_nested(self):
        payload = runner.response_format_payload("json_schema")
        self.assertEqual(payload["type"], "json_schema")
        schema = payload["json_schema"]
        self.assertTrue(schema["strict"])
        self.assertEqual(schema["schema"]["required"], ["summary", "citations"])
        self.assertFalse(schema["schema"]["additionalProperties"])

    def test_static_validation_rejects_mmproj_or_non_qat_path(self):
        model = copy.deepcopy(runner.QAT_MODELS[0])
        model["model_path"] = r"C:\models\gemma-mmproj.gguf"
        errors = runner.validate_static(CONFIG, [model], runner.CONTRACTS)
        self.assertTrue(any("QAT Q4_0 text GGUF" in error for error in errors))
        self.assertTrue(any("mmproj" in error for error in errors))

    def test_strict_json_rejects_markdown_fence(self):
        parsed, status = runner.strict_json_object("```json\n{}\n```")
        self.assertIsNone(parsed)
        self.assertEqual(status, "markdown_fence_present")

    def test_g2_requires_exact_bracketed_demo_citation(self):
        clean = {"summary": "ok", "citations": [runner.DEMO_CITATION]}
        score = runner.score_g2(
            {
                "status": "ok",
                "text": json.dumps(clean),
                "reasoning_text": "",
                "output_channel_status": "content",
                "content_chars": 1,
                "reasoning_chars": 0,
            }
        )
        self.assertEqual(score["pass_status"], "PASS")
        self.assertTrue(score["endpoint_eligible"])

        bare = {"summary": "ok", "citations": [runner.DEMO_SOURCE_ID]}
        score = runner.score_g2(
            {
                "status": "ok",
                "text": json.dumps(bare),
                "reasoning_text": "",
                "output_channel_status": "content",
                "content_chars": 1,
                "reasoning_chars": 0,
            }
        )
        self.assertEqual(score["failure_owner"], "native_contract")
        self.assertFalse(score["citations_exact"])

    def test_reasoning_only_is_output_channel_policy(self):
        response = {
            "status": "ok",
            "text": "",
            "reasoning_text": "hidden reasoning",
            "output_channel_status": "reasoning_only_output",
            "content_chars": 0,
            "reasoning_chars": 16,
        }
        score = runner.score_g1(response)
        self.assertEqual(score["failure_owner"], "output_channel_policy")
        self.assertFalse(score["raw_model_output_stored"])

    def test_repeated_token_loop_is_runtime_reasoning_control_failure(self):
        response = {
            "status": "ok",
            "text": " ".join(["<unused49>"] * 4),
            "reasoning_text": "",
            "output_channel_status": "content",
            "content_chars": 44,
            "reasoning_chars": 0,
        }
        score = runner.score_g1(response)
        self.assertEqual(score["failure_owner"], "runtime_template_or_reasoning_control")

    def test_phi_scan_includes_reasoning_text(self):
        response = {
            "status": "ok",
            "text": "safe final",
            "reasoning_text": "phone 010-1234-5678",
            "output_channel_status": "content",
            "content_chars": 10,
            "reasoning_chars": 19,
        }
        score = runner.score_g1(response)
        self.assertEqual(score["failure_owner"], "PHI")
        self.assertTrue(any("phone" in hit for hit in score["phi_like_hits"]))

    def test_preflight_blocks_base_failure_stale_port_and_shim(self):
        with patch.object(runner, "base_preflight_pass", return_value=(False, "LM Studio is not No Models Loaded")):
            ok, reason = runner.gemma_preflight_pass(CONFIG, {"base": {}, "runtime": {"ok": True}, "files": []})
        self.assertFalse(ok)
        self.assertEqual(reason, "LM Studio is not No Models Loaded")

        with patch.object(runner, "base_preflight_pass", return_value=(True, "")):
            ok, reason = runner.gemma_preflight_pass(
                CONFIG,
                {"base": {}, "runtime": {"ok": True, "ports": [{"LocalPort": 18080}], "shim_processes": []}, "files": []},
            )
        self.assertFalse(ok)
        self.assertIn("port 18080/18081", reason)

        with patch.object(runner, "base_preflight_pass", return_value=(True, "")):
            ok, reason = runner.gemma_preflight_pass(
                CONFIG,
                {"base": {}, "runtime": {"ok": True, "ports": [], "shim_processes": [{"ProcessId": 123}]}, "files": []},
            )
        self.assertFalse(ok)
        self.assertIn("stale shim", reason)

    def test_runtime_snapshot_excludes_own_powershell_probe(self):
        def fake_powershell(script, timeout=60):
            self.assertIn("$_.ProcessId -ne $PID", script)
            return {"returncode": 0, "stdout": '{"ports":[],"shim_processes":[]}'}

        with patch.object(runner, "powershell", side_effect=fake_powershell):
            snapshot = runner.runtime_snapshot()

        self.assertTrue(snapshot["ok"])
        self.assertEqual(snapshot["ports"], [])
        self.assertEqual(snapshot["shim_processes"], [])

    def test_dry_run_does_not_start_subprocess(self):
        with patch.object(runner.subprocess, "Popen") as popen:
            rc = runner.dry_run(CONFIG, runner.QAT_MODELS[:1], runner.CONTRACTS)
        self.assertEqual(rc, 0)
        popen.assert_not_called()

    def test_run_real_refuses_without_both_confirms_before_subprocess(self):
        args = Namespace(
            config="models_config_hpz2_llamacpp_phase2_l2_v0.1.json",
            output_root=None,
            fallback_args=False,
            confirm_hpz2=True,
            confirm_gemma_llamacpp_output_contract_pilot=False,
        )
        with patch.object(runner.subprocess, "Popen") as popen:
            rc = runner.run_real(args, CONFIG, runner.QAT_MODELS[:1], runner.CONTRACTS)
        self.assertEqual(rc, 2)
        popen.assert_not_called()

    def test_run_real_writes_metadata_only_for_clean_g2(self):
        response = {
            "status": "ok",
            "text": json.dumps({"summary": "ok", "citations": [runner.DEMO_CITATION]}),
            "reasoning_text": "",
            "output_channel_status": "content",
            "extraction_channel": "content",
            "content_chars": 69,
            "reasoning_chars": 0,
            "message_keys": ["content"],
            "finish_reason": "stop",
            "usage": {"completion_tokens": 10},
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(runner, "now_stamp", return_value="20260607_000000"), \
                patch.object(runner, "gemma_preflight", return_value={"ok": True}), \
                patch.object(runner, "gemma_preflight_pass", return_value=(True, "")), \
                patch.object(runner, "memory_snapshot", return_value={"ok": True}), \
                patch.object(runner, "wait_for_server", return_value={"ok": True}), \
                patch.object(runner, "call_chat_completion", return_value=response), \
                patch.object(runner.subprocess, "Popen", return_value=FakeProc()), \
                patch.object(runner.time, "sleep"):
                rc = runner.run_real(self.run_real_args(tmp), CONFIG, runner.QAT_MODELS[:1], [runner.CONTRACTS[1]])
            payload = self.read_payload(tmp)

        self.assertEqual(rc, 0)
        self.assertFalse(payload["raw_model_output_stored"])
        cell = payload["models"][0]["cells"][0]
        self.assertEqual(cell["pass_status"], "PASS")
        self.assertTrue(cell["endpoint_eligible"])
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn('"summary": "ok"', serialized)

    def test_final_preflight_failure_stops_after_run(self):
        response = {
            "status": "ok",
            "text": "final answer",
            "reasoning_text": "",
            "output_channel_status": "content",
            "extraction_channel": "content",
            "content_chars": 12,
            "reasoning_chars": 0,
            "message_keys": ["content"],
            "finish_reason": "stop",
            "usage": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(runner, "now_stamp", return_value="20260607_000001"), \
                patch.object(runner, "gemma_preflight", side_effect=[{"start": True}, {"final": True}]), \
                patch.object(runner, "gemma_preflight_pass", side_effect=[(True, ""), (False, "port 18080/18081 listener detected before run")]), \
                patch.object(runner, "memory_snapshot", return_value={"ok": True}), \
                patch.object(runner, "wait_for_server", return_value={"ok": True}), \
                patch.object(runner, "call_chat_completion", return_value=response), \
                patch.object(runner.subprocess, "Popen", return_value=FakeProc()), \
                patch.object(runner.time, "sleep"):
                rc = runner.run_real(self.run_real_args(tmp), CONFIG, runner.QAT_MODELS[:1], [runner.CONTRACTS[0]])
            payload = self.read_payload(tmp)

        self.assertEqual(rc, 1)
        self.assertTrue(payload["stopped_early"])
        self.assertIn("final_preflight_failed", payload["stop_reason"])


if __name__ == "__main__":
    unittest.main()
