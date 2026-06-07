import json
import unittest

from tools import hpz2_gemma_reasoning_output_contract_pilot as pilot


class GemmaReasoningOutputContractPilotTests(unittest.TestCase):
    def test_lms_ps_empty_requires_valid_empty_array(self):
        self.assertTrue(pilot.lms_ps_is_empty({"returncode": 0, "stdout": "[]"}))
        self.assertFalse(pilot.lms_ps_is_empty({"returncode": 0, "stdout": '[{"model":"loaded"}]'}))
        self.assertFalse(pilot.lms_ps_is_empty({"returncode": 1, "stdout": "[]"}))
        self.assertFalse(pilot.lms_ps_is_empty({"returncode": 0, "stdout": "not-json"}))

    def test_g1_content_passes_without_raw_storage(self):
        data = {
            "choices": [{"finish_reason": "stop", "message": {"content": "짧은 최종 답변입니다."}}],
            "usage": {"completion_tokens": 12},
        }
        result = pilot.summarize_response(
            model_label="m",
            contract="G1",
            max_tokens=512,
            response_format_requested=False,
            http_status=200,
            data=data,
            api_error=None,
            latency_sec=1.0,
        )
        self.assertEqual(result["pass_status"], "PASS")
        self.assertEqual(result["content_chars"], len("짧은 최종 답변입니다."))
        self.assertNotIn("짧은 최종 답변입니다.", json.dumps(result, ensure_ascii=False))

    def test_reasoning_only_is_not_g1_pass(self):
        data = {
            "choices": [{"finish_reason": "length", "message": {"content": "", "reasoning": "숨은 추론"}}],
            "usage": {"completion_tokens_details": {"reasoning_tokens": 25}},
        }
        result = pilot.summarize_response(
            model_label="m",
            contract="G1",
            max_tokens=512,
            response_format_requested=False,
            http_status=200,
            data=data,
            api_error=None,
            latency_sec=1.0,
        )
        self.assertEqual(result["output_channel_status"], "reasoning_only_output")
        self.assertEqual(result["pass_status"], "FAIL")

    def test_g2_requires_exact_json_contract(self):
        content = json.dumps(
            {"summary": "합성 데이터만 사용한 테스트입니다.", "citations": [pilot.DEMO_CITATION]},
            ensure_ascii=False,
        )
        data = {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}
        result = pilot.summarize_response(
            model_label="m",
            contract="G2",
            max_tokens=1024,
            response_format_requested=True,
            http_status=200,
            data=data,
            api_error=None,
            latency_sec=1.0,
        )
        self.assertEqual(result["json_parse_status"], "parsed")
        self.assertEqual(result["json_keys"], ["citations", "summary"])
        self.assertTrue(result["citations_exact"])
        self.assertEqual(result["pass_status"], "PASS")

    def test_g2_rejects_markdown_fence(self):
        data = {"choices": [{"message": {"content": "```json\n{}\n```"}}]}
        result = pilot.summarize_response(
            model_label="m",
            contract="G2",
            max_tokens=1024,
            response_format_requested=True,
            http_status=200,
            data=data,
            api_error=None,
            latency_sec=1.0,
        )
        self.assertEqual(result["json_parse_status"], "markdown_fence_present")
        self.assertEqual(result["pass_status"], "FAIL")

    def test_phi_like_scan_flags_direct_identifiers(self):
        hits = pilot.phi_like_hits("환자명=홍길동, 900101-1234567")
        self.assertGreaterEqual(len(hits), 2)


if __name__ == "__main__":
    unittest.main()
