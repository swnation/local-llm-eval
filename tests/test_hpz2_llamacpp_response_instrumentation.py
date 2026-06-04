import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from hpz2_lmstudio_phase2_l2_semantic_runner import evaluate_semantic_lanes, extract_chat_message
from hpz2_llamacpp_h2_output_contract_calibration_runner import output_channel_policy_scoring


class Hpz2LlamacppResponseInstrumentationTests(unittest.TestCase):
    def test_extract_chat_message_detects_reasoning_only_output(self):
        parsed = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "reasoning_content": '{"summary":"hidden","citations":["rule:a"]}',
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1},
        }

        result = extract_chat_message(parsed)

        self.assertEqual(result["text"], "")
        self.assertEqual(result["output_channel_status"], "reasoning_only_output")
        self.assertEqual(result["extraction_channel"], "none")
        self.assertGreater(result["reasoning_chars"], 0)
        self.assertIn("reasoning_content", result["message_keys"])
        self.assertEqual(result["finish_reason"], "stop")

    def test_extract_chat_message_treats_whitespace_content_as_reasoning_only(self):
        parsed = {
            "choices": [
                {
                    "message": {
                        "content": " \n\t",
                        "reasoning_content": '{"summary":"hidden","citations":["rule:a"]}',
                    }
                }
            ]
        }

        result = extract_chat_message(parsed)

        self.assertEqual(result["text"], " \n\t")
        self.assertEqual(result["output_channel_status"], "reasoning_only_output")
        self.assertEqual(result["extraction_channel"], "none")
        self.assertGreater(result["reasoning_chars"], 0)

    def test_extract_chat_message_prefers_final_content(self):
        parsed = {
            "choices": [
                {
                    "message": {
                        "content": '{"summary":"ok","citations":["rule:a"]}',
                        "reasoning_content": "scratchpad",
                    }
                }
            ]
        }

        result = extract_chat_message(parsed)

        self.assertEqual(result["output_channel_status"], "content")
        self.assertEqual(result["extraction_channel"], "content")
        self.assertIn('"summary":"ok"', result["text"])
        self.assertEqual(result["reasoning_text"], "scratchpad")

    def test_evaluate_semantic_lanes_short_circuits_reasoning_only(self):
        l2_case = {
            "case_metric_profile": "demo",
            "metric_risk_notes": "",
            "evidence_pack": [{"source_id": "rule:a", "text": "demo"}],
            "acceptable_citation_set": {"required_all": ["rule:a"]},
        }
        eval_case = {
            "expected_summary_keywords": ["demo"],
            "acceptable_citation_set": {"required_all": ["rule:a"]},
        }

        result = evaluate_semantic_lanes(
            text="",
            l2_case=l2_case,
            eval_case=eval_case,
            eval_set={"cases": []},
            output_channel_status="reasoning_only_output",
        )

        self.assertEqual(
            result["lanes"]["semantic_rag_lane"]["failure_owner"],
            "output_channel_policy",
        )
        self.assertEqual(
            result["lanes"]["native_contract_lane"]["parse_status"],
            "not_scored_reasoning_only_output",
        )
        self.assertEqual(result["r2_metric_hooks"]["response_completeness"], "reasoning_only_output")

    def test_output_channel_policy_scoring_quarantines_as_policy_failure(self):
        contract = {"id": "C1"}
        case = {"required_sources": ["rule:a"]}

        result = output_channel_policy_scoring(contract, case, "reasoning_only_output")

        self.assertEqual(result["parse_status"], "not_scored_reasoning_only_output")
        self.assertEqual(result["failure_owner"], "output_channel_policy")
        self.assertFalse(result["normalizer_pass"])
        self.assertEqual(result["required_sources_missing"], ["rule:a"])


if __name__ == "__main__":
    unittest.main()
