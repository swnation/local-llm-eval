import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import hpz2_llamacpp_h2_endpoint_runner as runner


EVAL_SET = json.loads((ROOT / "prompts" / "rag_aware_eval_set_v0.1.json").read_text(encoding="utf-8"))


class H2EndpointRunnerTests(unittest.TestCase):
    def test_c1_replay_defaults_to_pilot_models(self):
        self.assertEqual(
            runner.select_model_labels(c1_replay=True, primary4_c1_replay=False),
            runner.C1_REPLAY_PILOT_MODELS,
        )

    def test_c1_replay_primary4_expansion_uses_primary_models(self):
        self.assertEqual(
            runner.select_model_labels(c1_replay=True, primary4_c1_replay=True),
            runner.PRIMARY_MODELS,
        )

    def test_c1_replay_selects_locked_cases_in_order(self):
        cases = runner.select_cases(EVAL_SET, c1_replay=True)
        self.assertEqual([case["id"] for case in cases], runner.C1_REPLAY_CASE_IDS)
        self.assertTrue(all(case.get("model_call_expected", True) for case in cases))

    def test_non_replay_keeps_full_eval_set(self):
        cases = runner.select_cases(EVAL_SET, c1_replay=False)
        self.assertEqual(len(cases), len(EVAL_SET["cases"]))

    def test_replay_response_artifacts_store_after_clean_phi_scan(self):
        def clean_scan(text):
            return False, text

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(runner, "RESULT_DIR", Path(tmp)):
                paths, phi_hit = runner.write_replay_response_artifacts(
                    model_label="model/a",
                    case_id="case:1",
                    body={"status": "ok", "summary": "safe", "citations": []},
                    raw_llm_text='{"summary":"safe","citations":[]}',
                    scan_output=clean_scan,
                )
        self.assertFalse(phi_hit)
        self.assertIn("endpoint_response_path", paths)
        self.assertIn("raw_llm_response_path", paths)

    def test_replay_response_artifacts_block_phi_storage(self):
        def phi_scan(text):
            return "PHI" in text, text

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(runner, "RESULT_DIR", Path(tmp)):
                paths, phi_hit = runner.write_replay_response_artifacts(
                    model_label="model/a",
                    case_id="case:1",
                    body={"status": "ok", "summary": "safe", "citations": []},
                    raw_llm_text="PHI",
                    scan_output=phi_scan,
                )
                response_files = list(Path(tmp).rglob("*"))
        self.assertTrue(phi_hit)
        self.assertEqual(paths, {})
        self.assertEqual([path for path in response_files if path.is_file()], [])


if __name__ == "__main__":
    unittest.main()
