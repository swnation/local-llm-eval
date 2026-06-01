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

import hpz2_llamacpp_h2_output_contract_calibration_runner as runner


FIXTURE = json.loads((ROOT / "prompts" / "h2_output_contract_calibration_v0.1.json").read_text(encoding="utf-8"))
CONFIG = json.loads((ROOT / "models_config_hpz2_llamacpp_phase2_l2_v0.1.json").read_text(encoding="utf-8"))
CASE = FIXTURE["cases"][0]
CONTRACTS = {contract["id"]: contract for contract in FIXTURE["contracts"]}
PILOT_MODELS = [model for model in CONFIG["models"] if model["label"] in runner.PILOT_MODELS]


class OutputContractCalibrationRunnerTests(unittest.TestCase):
    def test_c1_native_contract_passes_with_bracketed_sources(self):
        text = '{"summary":"DEMO는 원내 제한 대상이며 처방 판단은 진료의 영역입니다.","citations":["[rule:drug:demo]"]}'
        result = runner.normalize_output(text, CONTRACTS["C1"], CASE)
        self.assertEqual(result["parse_status"], "json_ok")
        self.assertTrue(result["native_contract_pass"])
        self.assertTrue(result["normalizer_pass"])
        self.assertEqual(result["normalized_citations"], ["rule:drug:demo"])

    def test_normal_scoring_does_not_overwrite_raw_response_stored(self):
        text = '{"summary":"DEMO는 원내 제한 대상이며 처방 판단은 진료의 영역입니다.","citations":["[rule:drug:demo]"]}'
        cell = {"raw_response_stored": True}
        cell.update(runner.normalize_output(text, CONTRACTS["C1"], CASE))
        self.assertTrue(cell["raw_response_stored"])

    def test_c1_bare_source_is_not_native_but_can_normalize(self):
        text = '{"summary":"DEMO는 원내 제한 대상입니다.","citations":["rule:drug:demo"]}'
        result = runner.normalize_output(text, CONTRACTS["C1"], CASE)
        self.assertFalse(result["native_contract_pass"])
        self.assertTrue(result["citation_format_error"])
        self.assertTrue(result["normalizer_pass"])

    def test_c2_bare_source_contract_passes_normalizer_path(self):
        text = '{"summary":"DEMO는 원내 제한 대상입니다.","citations":["rule:drug:demo"]}'
        result = runner.normalize_output(text, CONTRACTS["C2"], CASE)
        self.assertFalse(result["native_contract_pass"])
        self.assertTrue(result["normalizer_pass"])
        self.assertFalse(result["citation_format_error"])

    def test_c3_answer_sources_contract_normalizes(self):
        text = '{"answer":"DEMO는 원내 제한 대상입니다.","sources":["rule:drug:demo"]}'
        result = runner.normalize_output(text, CONTRACTS["C3"], CASE)
        self.assertTrue(result["normalizer_pass"])
        self.assertEqual(result["normalized_summary"], "DEMO는 원내 제한 대상입니다.")

    def test_c4_freeform_inline_citations_extracts_source(self):
        text = "DEMO는 원내 제한 대상이며 처방 판단은 진료의 영역입니다. [rule:drug:demo]"
        result = runner.normalize_output(text, CONTRACTS["C4"], CASE)
        self.assertEqual(result["parse_status"], "freeform_only")
        self.assertTrue(result["normalizer_pass"])
        self.assertEqual(result["normalized_citations"], ["rule:drug:demo"])

    def test_required_source_missing_blocks_normalizer_pass(self):
        case = FIXTURE["cases"][1]
        text = '{"summary":"DEMO는 연령 기준 확인이 필요합니다.","citations":["rule:drug:demo"]}'
        result = runner.normalize_output(text, CONTRACTS["C2"], case)
        self.assertFalse(result["required_sources_pass"])
        self.assertFalse(result["citation_exact_pass"])
        self.assertFalse(result["normalizer_pass"])
        self.assertEqual(result["required_sources_missing"], ["kb:소아_DEMO_용량:007"])

    def test_distractor_source_blocks_citation_exact_pass(self):
        case = FIXTURE["cases"][2]
        text = (
            '{"summary":"DEMO는 보험 예외 기준 확인이 필요합니다.",'
            '"citations":["rule:drug:demo","kb:보험_DEMO_예외_2026-01","kb:성인_DEMO_일반정보"]}'
        )
        result = runner.normalize_output(text, CONTRACTS["C2"], case)
        self.assertFalse(result["distractor_sources_pass"])
        self.assertFalse(result["citation_exact_pass"])
        self.assertFalse(result["normalizer_pass"])

    def test_phi_redacted_scoring_does_not_preserve_summary(self):
        result = runner.phi_redacted_scoring(["patient_name_label"], CONTRACTS["C1"])
        self.assertEqual(result["parse_status"], "not_scored_phi_like_output")
        self.assertEqual(result["normalized_summary"], "")
        self.assertEqual(result["normalized_citations"], [])
        self.assertFalse(result["raw_response_stored"])
        self.assertFalse(result["safety_pass"])

    def test_fixture_phi_like_preflight_blocks_patient_name_label(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture["cases"][0]["task"] = "환자명: 테스트"
        errors = runner.validate_fixture(fixture)
        self.assertTrue(any("PHI-like" in error for error in errors))

    def test_dry_run_does_not_start_subprocess(self):
        with patch.object(runner.subprocess, "Popen") as popen:
            rc = runner.dry_run(CONFIG, FIXTURE, PILOT_MODELS, [CASE], [CONTRACTS["C1"]])
        self.assertEqual(rc, 0)
        popen.assert_not_called()

    def test_run_real_refuses_without_both_confirms_before_subprocess(self):
        args = Namespace(
            config="models_config_hpz2_llamacpp_phase2_l2_v0.1.json",
            fixture="prompts/h2_output_contract_calibration_v0.1.json",
            output_root=None,
            fallback_args=False,
            confirm_hpz2=True,
            confirm_output_contract_calibration=False,
        )
        with patch.object(runner.subprocess, "Popen") as popen:
            rc = runner.run_real(args, CONFIG, FIXTURE, PILOT_MODELS[:1], [CASE], [CONTRACTS["C1"]])
        self.assertEqual(rc, 2)
        popen.assert_not_called()

    def test_write_summary_surfaces_manual_review_lanes(self):
        payload = {
            "generated_at": "2026-06-02T00:00:00",
            "mode": "h2_output_contract_calibration",
            "stopped_early": False,
            "stop_reason": "",
            "models": [
                {
                    "label": "demo-model",
                    "cells": [
                        {
                            "case_id": "OC-01-simple-one-source",
                            "contract_variant": "C1",
                            "api_status": "ok",
                            "parse_status": "json_ok",
                            "native_contract_pass": True,
                            "normalizer_pass": True,
                            "citation_exact_pass": True,
                            "required_sources_pass": True,
                            "semantic_pass": None,
                            "grounding_pass": None,
                            "citation_claim_pass": None,
                            "safety_pass": None,
                            "manual_review_needed": True,
                            "raw_response_stored": True,
                            "failure_owner": "manual_review_needed",
                        }
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = runner.write_summary(Path(tmp), payload)
            text = path.read_text(encoding="utf-8")
        self.assertIn("manual review lanes must be filled", text)
        self.assertIn("semantic", text)
        self.assertIn("grounding", text)
        self.assertIn("claim cite", text)
        self.assertIn("safety", text)
        self.assertIn("manual_review_needed", text)


if __name__ == "__main__":
    unittest.main()
