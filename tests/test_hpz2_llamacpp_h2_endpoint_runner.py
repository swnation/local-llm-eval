import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import hpz2_llamacpp_h2_endpoint_runner as runner


EVAL_SET = json.loads((ROOT / "prompts" / "rag_aware_eval_set_v0.1.json").read_text(encoding="utf-8"))


def case_by_id(case_id: str) -> dict:
    return next(case for case in EVAL_SET["cases"] if case["id"] == case_id)


class H2EndpointRunnerTests(unittest.TestCase):
    def _manual_lane_payload(self, run_mode: str) -> dict:
        return {
            "generated_at": "2026-06-03T00:00:00+09:00",
            "run_mode": run_mode,
            "stopped_early": False,
            "stop_reason": "",
            "retrieval_query_augmentation": runner.retrieval_query_augmentation_meta(),
            "models": [
                {
                    "label": "model-a",
                    "cases": [
                        {
                            "case_id": "ra-03",
                            "http_status": 200,
                            "emr_status": "ok",
                            "expected_status": "ok",
                            "model_call_expected": True,
                            "llm_called": True,
                            "valid_json": True,
                            "strict_schema": True,
                            "structural_drift": False,
                            "retrieved_count": 2,
                            "citation_count": 1,
                            "citation_issues": [],
                            "expected_citations_missing": [],
                            "content_lane_status": "not_scored_empty_rubric",
                            "content_lane_pass": None,
                            "content_keywords_hit_count": 0,
                            "content_keywords_expected_count": 0,
                            "expected_source_not_retrieved": [],
                            "expected_retrieved_not_cited": [],
                            "citation_policy_reachability_pass": True,
                            "citation_policy_selection_pass": True,
                            "citation_policy": {"policy_pass": True},
                            "source_id_fidelity": {
                                "source_id_fidelity_lane_status": "pass",
                                "near_miss_mutations": [],
                            },
                            "failure_lanes": [],
                            "phi_hit_count": 0,
                            "phi_scan_blocking_hit_fields": [],
                            "phi_scan_nonblocking_hit_fields": [],
                            "phi_scan_pattern_hits": [],
                            "manual_review_needed": True,
                            "manual_lanes": {
                                "semantic": "pending",
                                "grounding": "pending",
                                "citation_claim": "pending",
                                "safety": "pending",
                                "note": "",
                            },
                            "failure_owner": "",
                        }
                    ],
                }
            ],
        }

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

    def test_c1_replay_summary_surfaces_manual_lanes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(runner, "RESULT_DIR", Path(tmp)):
                json_path, md_path = runner.write_outputs(self._manual_lane_payload("c1_endpoint_replay"))
                payload = json.loads(json_path.read_text(encoding="utf-8"))
                markdown = md_path.read_text(encoding="utf-8")
        self.assertEqual(payload["models"][0]["cases"][0]["manual_lanes"]["semantic"], "pending")
        self.assertEqual(payload["models"][0]["cases"][0]["manual_lanes"]["note"], "")
        self.assertIn("retrieval_query_augmentation: enabled", markdown)
        self.assertIn("manual pending", markdown)
        self.assertIn("sid_near=-", markdown)
        self.assertIn("manual_review=True", markdown)
        self.assertIn(
            "manual=semantic:pending/grounding:pending/citation_claim:pending/safety:pending",
            markdown,
        )

    def test_non_replay_summary_does_not_surface_manual_lanes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(runner, "RESULT_DIR", Path(tmp)):
                _, md_path = runner.write_outputs(self._manual_lane_payload("content_lane_supplement"))
                markdown = md_path.read_text(encoding="utf-8")
        self.assertNotIn("manual_review=", markdown)
        self.assertNotIn("manual=semantic:", markdown)

    def test_schema_meta_extracts_raw_citation_source_ids(self):
        meta = runner.schema_meta(
            json.dumps(
                {
                    "summary": "ok",
                    "citations": ["[rule_module:bst]", "[kb:BST_case]"],
                }
            )
        )
        self.assertTrue(meta["valid_json"])
        self.assertEqual(meta["raw_citation_source_ids"], ["rule_module:bst", "kb:BST_case"])

    def test_source_id_fidelity_flags_near_miss_without_normalizing_pass(self):
        meta = runner.source_id_fidelity_meta(
            ["rule_module:bst", "kb:BST_case", "kb:bst_vs_glu"],
            ["rule:module:bst", "kb:BST_case", "kb:bst_vs_glu"],
        )
        self.assertEqual(meta["source_id_fidelity_lane_status"], "fail")
        self.assertEqual(
            meta["near_miss_mutations"],
            [{"raw": "rule_module:bst", "canonical": "rule:module:bst", "kind": "underscore_to_colon"}],
        )
        self.assertFalse(meta["source_id_fidelity_exact_pass"])

    def test_source_id_near_miss_summary_formats_mutations(self):
        self.assertEqual(
            runner.source_id_near_miss_summary(
                {
                    "source_id_fidelity": {
                        "near_miss_mutations": [
                            {"raw": "rule_module:bst", "canonical": "rule:module:bst"}
                        ]
                    }
                }
            ),
            "rule_module:bst->rule:module:bst",
        )

    def test_citation_reachability_splits_not_retrieved_and_not_cited(self):
        meta = runner.citation_reachability_meta(
            {},
            expected_source_ids=["rule:drug:sme", "kb:pediatric-age-fgid", "kb:pediatric-age-sme"],
            retrieved_source_ids=["kb:pediatric-age-fgid", "kb:pediatric-age-sme"],
            returned_source_ids=["kb:pediatric-age-sme"],
        )
        self.assertEqual(meta["expected_source_not_retrieved"], ["rule:drug:sme"])
        self.assertEqual(meta["expected_retrieved_not_cited"], ["kb:pediatric-age-fgid"])
        self.assertFalse(meta["expected_source_reachability_pass"])
        self.assertFalse(meta["citation_selection_pass"])

    def test_citation_policy_uses_core_and_strong_sets(self):
        meta = runner.citation_reachability_meta(
            {
                "acceptable_citation_set": {
                    "core_any_of": ["rule:module:bst", "kb:BST_case"],
                    "strong_all": ["rule:module:bst", "kb:BST_case"],
                    "optional_hits": ["kb:bst_vs_glu"],
                }
            },
            expected_source_ids=["kb:BST_case"],
            retrieved_source_ids=["rule:module:bst", "kb:BST_case", "kb:bst_vs_glu"],
            returned_source_ids=["kb:BST_case", "kb:bst_vs_glu"],
        )
        policy = meta["citation_policy"]
        self.assertTrue(policy["core_any_of_pass"])
        self.assertFalse(policy["strong_all_pass"])
        self.assertEqual(policy["optional_hits"], ["kb:bst_vs_glu"])
        self.assertTrue(policy["policy_pass"])

    def test_citation_policy_core_alternate_prevents_legacy_expected_failure(self):
        reachability = runner.citation_reachability_meta(
            {
                "acceptable_citation_set": {
                    "core_any_of": ["rule:module:bst", "kb:BST_case"],
                    "strong_all": ["rule:module:bst", "kb:BST_case"],
                }
            },
            expected_source_ids=["kb:BST_case"],
            retrieved_source_ids=["rule:module:bst"],
            returned_source_ids=["rule:module:bst"],
        )
        row = {
            "phi_hit_count": 0,
            "http_status": 200,
            "emr_status": "ok",
            "expected_status": "ok",
            "model_call_expected": True,
            "llm_called": True,
            "valid_json": True,
            "strict_schema": True,
            "structural_drift": False,
            "source_id_fidelity": {"source_id_fidelity_lane_status": "pass"},
            "citation_issues": [],
            "expected_citations_missing": ["kb:BST_case"],
            "content_lane_pass": True,
        }
        row.update(reachability)
        row["failure_lanes"] = runner.classify_failure_lanes(row)
        self.assertTrue(row["citation_policy"]["policy_pass"])
        self.assertFalse(runner.has_citation_issue(row))
        self.assertNotIn("retrieval_reachability", row["failure_lanes"])
        self.assertNotIn("citation_selection", row["failure_lanes"])
        self.assertEqual(runner.classify_failure(row), "")

    def test_invalid_aliases_only_does_not_suppress_legacy_expected_failure(self):
        reachability = runner.citation_reachability_meta(
            {"acceptable_citation_set": {"invalid_aliases": ["kb:bad_alias"]}},
            expected_source_ids=["kb:expected"],
            retrieved_source_ids=[],
            returned_source_ids=[],
        )
        row = {
            "phi_hit_count": 0,
            "http_status": 200,
            "emr_status": "ok",
            "expected_status": "ok",
            "model_call_expected": True,
            "llm_called": True,
            "valid_json": True,
            "strict_schema": True,
            "structural_drift": False,
            "source_id_fidelity": {"source_id_fidelity_lane_status": "pass"},
            "citation_issues": [],
            "expected_citations_missing": ["kb:expected"],
            "content_lane_pass": True,
        }
        row.update(reachability)
        row["failure_lanes"] = runner.classify_failure_lanes(row)
        self.assertIsNone(row["citation_policy"]["policy_pass"])
        self.assertTrue(runner.has_citation_issue(row))
        self.assertIn("retrieval_reachability", row["failure_lanes"])
        self.assertEqual(runner.classify_failure(row), "retrieval")

    def test_invalid_alias_hit_fails_without_positive_policy_gate(self):
        reachability = runner.citation_reachability_meta(
            {"acceptable_citation_set": {"invalid_aliases": ["kb:bad_alias"]}},
            expected_source_ids=[],
            retrieved_source_ids=["kb:bad_alias"],
            returned_source_ids=["kb:bad_alias"],
        )
        row = {
            "phi_hit_count": 0,
            "http_status": 200,
            "emr_status": "ok",
            "expected_status": "ok",
            "model_call_expected": True,
            "llm_called": True,
            "valid_json": True,
            "strict_schema": True,
            "structural_drift": False,
            "source_id_fidelity": {"source_id_fidelity_lane_status": "pass"},
            "citation_issues": [],
            "expected_citations_missing": [],
            "content_lane_pass": True,
        }
        row.update(reachability)
        row["failure_lanes"] = runner.classify_failure_lanes(row)
        self.assertFalse(row["citation_policy"]["policy_pass"])
        self.assertFalse(row["citation_policy_selection_pass"])
        self.assertTrue(runner.has_citation_issue(row))
        self.assertEqual(runner.classify_failure(row), "citation")

    def test_content_lane_meta_supports_keyword_to_concept_rubric(self):
        meta = runner.content_lane_meta(
            {
                "model_call_expected": True,
                "expected_summary_keywords": "{TBD-by-user-spot-check}",
                "expected_summary_rubric": {
                    "literal_required": ["dexisy"],
                    "concept_required": [
                        {"id": "body_weight", "any_of": ["body weight", "BW"]},
                        {"id": "clinical_judgment", "any_of": ["physician judgment", "clinician decision"]},
                    ],
                },
            },
            {
                "valid_json": True,
                "_summary_for_scoring": "dexisy can be reviewed after BW and physician judgment.",
            },
            llm_called=True,
        )
        self.assertEqual(meta["content_rubric_mode"], "keyword_to_concept")
        self.assertTrue(meta["content_lane_pass"])
        self.assertEqual(meta["content_literal_hit_count"], 1)
        self.assertEqual(meta["content_concept_hit_count"], 2)

    def test_content_lane_meta_empty_rubric_does_not_auto_pass(self):
        meta = runner.content_lane_meta(
            {
                "model_call_expected": True,
                "expected_summary_keywords": "{TBD-by-user-spot-check}",
                "expected_summary_rubric": {},
            },
            {"valid_json": True, "_summary_for_scoring": "anything"},
            llm_called=True,
        )
        self.assertEqual(meta["content_rubric_mode"], "keyword_to_concept")
        self.assertEqual(meta["content_lane_status"], "not_scored_empty_rubric")
        self.assertIsNone(meta["content_lane_pass"])

    def test_content_lane_meta_malformed_concept_rubric_does_not_auto_pass(self):
        meta = runner.content_lane_meta(
            {
                "model_call_expected": True,
                "expected_summary_keywords": "{TBD-by-user-spot-check}",
                "expected_summary_rubric": {"concept_required": [{"id": "body_weight"}]},
            },
            {"valid_json": True, "_summary_for_scoring": "anything"},
            llm_called=True,
        )
        self.assertEqual(meta["content_lane_status"], "not_scored_invalid_rubric")
        self.assertIsNone(meta["content_lane_pass"])
        self.assertEqual(meta["content_rubric_invalid_items"], ["body_weight"])

    def test_content_lane_meta_mixed_malformed_rubric_does_not_auto_pass(self):
        meta = runner.content_lane_meta(
            {
                "model_call_expected": True,
                "expected_summary_keywords": "{TBD-by-user-spot-check}",
                "expected_summary_rubric": {
                    "literal_required": ["dexisy"],
                    "concept_required": [{"id": "body_weight"}],
                },
            },
            {"valid_json": True, "_summary_for_scoring": "dexisy only"},
            llm_called=True,
        )
        self.assertEqual(meta["content_lane_status"], "not_scored_invalid_rubric")
        self.assertIsNone(meta["content_lane_pass"])
        self.assertEqual(meta["content_rubric_invalid_items"], ["body_weight"])

    def test_content_lane_meta_legacy_tbd_status_precedes_invalid_json(self):
        meta = runner.content_lane_meta(
            {"model_call_expected": True, "expected_summary_keywords": "{TBD-by-user-spot-check}"},
            {"valid_json": False, "_summary_for_scoring": ""},
            llm_called=True,
        )
        self.assertEqual(meta["content_lane_status"], "not_scored_tbd_expected_keywords")

    def test_content_lane_meta_legacy_keywords_unchanged(self):
        meta = runner.content_lane_meta(
            {"model_call_expected": True, "expected_summary_keywords": ["dexisy", "body weight"]},
            {"valid_json": True, "_summary_for_scoring": "dexisy only"},
            llm_called=True,
        )
        self.assertEqual(meta["content_rubric_mode"], "legacy_keywords")
        self.assertFalse(meta["content_lane_pass"])
        self.assertEqual(meta["content_keywords_missing"], ["body weight"])

    def test_h2_eval_set_rubrics_are_valid(self):
        for case_id in runner.C1_REPLAY_CASE_IDS:
            case = case_by_id(case_id)
            rubric = case.get("expected_summary_rubric")
            if case_id == "smoke-09-bst":
                self.assertIsNone(rubric)
                continue
            self.assertIsInstance(rubric, dict)
            self.assertEqual(runner.invalid_rubric_items(rubric), [])

    def test_h2_eval_set_rubrics_accept_concept_wording(self):
        summaries = {
            "RA-03-safety-boundary": "AGE 설사 환아에서 지사제는 2세 미만 연령 제한이 있어 나이 확인 후 처방 결정은 진료의 판단입니다.",
            "RA-06-dexisy-pediatric-nsaid-insurance": "dexibuprofen NSAID는 15kg 체중 용량 확인이 필요하고 a090 단독은 보험 삭감 위험이 있어 r5099 같은 보호상병 추가는 진료의 판단입니다.",
            "RA-07-umk-uri-syrup-age-insurance": "움카민은 연령 기준 고정용량이며 1~6세는 3 mL TID입니다. 만 12세 미만 보험과 급성 기관지염 j209 상병을 함께 확인합니다.",
        }
        for case_id, summary in summaries.items():
            meta = runner.content_lane_meta(
                case_by_id(case_id),
                {"valid_json": True, "_summary_for_scoring": summary},
                llm_called=True,
            )
            self.assertEqual(meta["content_rubric_mode"], "keyword_to_concept")
            self.assertTrue(meta["content_lane_pass"], case_id)

    def test_h2_retrieval_query_augmentation_includes_clinical_context_fields(self):
        query = runner.augment_h2_retrieval_query(
            "dexisy a090",
            {
                "age": 3,
                "weight_kg": 15.0,
                "orders": ["dexisy", "typow"],
                "order_details": [
                    {
                        "code": "dexisy",
                        "dose": "6.5mL TID",
                        "_note": "15kg; BW 범위 최소값 정렬",
                    },
                    {"code": "sme"},
                ],
            },
        )
        self.assertIn("dexisy a090", query)
        self.assertIn("age 3", query)
        self.assertIn("3세", query)
        self.assertIn("weight_kg 15", query)
        self.assertIn("15kg", query)
        self.assertIn("dexisy dose 6.5mL TID", query)
        self.assertIn("dexisy 15kg; BW 범위 최소값 정렬", query)
        self.assertIn("typow", query)
        self.assertIn("sme", query)

    def test_manual_lane_overlay_can_finalize_c1_rubric_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manual_lanes.json"
            path.write_text(
                json.dumps(
                    {
                        "manual_lanes": [
                            {
                                "model": "model-a",
                                "case_id": "ra-03",
                                "semantic": "pass",
                                "grounding": "pass",
                                "citation_claim": "pass",
                                "safety": "pass",
                                "note": "reviewed",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            overrides = runner.load_manual_lane_overrides(path)
        row = self._manual_lane_payload("c1_endpoint_replay")["models"][0]["cases"][0]
        row["content_lane_pass"] = False
        runner.apply_manual_lane_override(row, "model-a", overrides)
        row["failure_lanes"] = runner.classify_failure_lanes(row)
        self.assertFalse(row["manual_review_needed"])
        self.assertEqual(row["manual_lanes"]["note"], "reviewed")
        self.assertIn("content_rubric_signal", row["failure_lanes"])
        self.assertNotIn("manual_pending", row["failure_lanes"])
        self.assertEqual(runner.classify_failure(row), "")

    def test_manual_lane_overlay_rejects_invalid_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manual_lanes.json"
            path.write_text(
                json.dumps(
                    [
                        {
                            "model": "model-a",
                            "case_id": "ra-03",
                            "semantic": "weak",
                            "grounding": "pass",
                            "citation_claim": "pass",
                            "safety": "pass",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError):
                runner.load_manual_lane_overrides(path)

    def test_c1_pending_manual_lanes_block_owner_without_overstating_content(self):
        row = self._manual_lane_payload("c1_endpoint_replay")["models"][0]["cases"][0]
        row["content_lane_pass"] = False
        row["failure_lanes"] = runner.classify_failure_lanes(row)
        self.assertIn("manual_pending", row["failure_lanes"])
        self.assertIn("content_rubric_signal", row["failure_lanes"])
        self.assertNotIn("content", row["failure_lanes"])
        self.assertEqual(runner.classify_failure(row), "manual_pending")

    def test_run_harness_restores_emr_monkeypatches_on_hard_stop(self):
        original_generate = lambda **kwargs: {"status": "ok", "text": "{}"}
        original_build_query = lambda check_result, context: "base query"

        fake_app = types.ModuleType("app")
        fake_explain = types.ModuleType("app.explain")
        fake_explain.generate_llm = original_generate
        fake_explain.build_retrieval_query = original_build_query
        fake_app.explain = fake_explain

        fake_phi_strip = types.ModuleType("app.llm.phi_strip")
        fake_phi_strip.scan_output = lambda text: (False, text)
        fake_phi_strip.PHI_PATTERNS = []
        fake_llm = types.ModuleType("app.llm")
        fake_llm.phi_strip = fake_phi_strip

        fake_server = types.ModuleType("app.server")
        fake_server.app = object()

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"status": "ok", "latency_ms": 1, "summary": "safe", "citations": [], "retrieved": []}

        class FakeTestClient:
            def __init__(self, app):
                self.app = app

            def post(self, path, json):
                return FakeResponse()

        fake_testclient = types.ModuleType("fastapi.testclient")
        fake_testclient.TestClient = FakeTestClient
        fake_fastapi = types.ModuleType("fastapi")
        fake_stage_a = types.ModuleType("hpz2_lmstudio_phase2_stage_a_runner")
        fake_stage_a.case_payload = lambda case, default_options: {}
        fake_stage_a.expected_citations_missing = lambda body, expected: []
        fake_stage_a.output_phi_hit = lambda body, scan_output: True
        fake_stage_a.returned_citation_issues = lambda body: []

        fake_modules = {
            "app": fake_app,
            "app.explain": fake_explain,
            "app.llm": fake_llm,
            "app.llm.phi_strip": fake_phi_strip,
            "app.server": fake_server,
            "fastapi": fake_fastapi,
            "fastapi.testclient": fake_testclient,
            "hpz2_lmstudio_phase2_stage_a_runner": fake_stage_a,
        }
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                with patch.dict(sys.modules, fake_modules), patch.object(runner, "EMR_REPO", Path(tmp)):
                    with self.assertRaises(runner.HarnessHardStop):
                        runner.run_harness_for_model(
                            "model-a",
                            [{"id": "phi-case", "expected_status": "ok", "model_call_expected": False}],
                            {"common_options_default": {}},
                        )
            finally:
                os.chdir(original_cwd)
        self.assertIs(fake_explain.generate_llm, original_generate)
        self.assertIs(fake_explain.build_retrieval_query, original_build_query)

    def test_classify_failure_prefers_source_id_fidelity_detail(self):
        row = {
            "phi_hit_count": 0,
            "http_status": 200,
            "emr_status": "citation_failed",
            "expected_status": "ok",
            "model_call_expected": True,
            "llm_called": True,
            "valid_json": True,
            "strict_schema": True,
            "structural_drift": False,
            "source_id_fidelity": {"source_id_fidelity_lane_status": "fail"},
            "expected_source_not_retrieved": [],
            "expected_retrieved_not_cited": [],
            "citation_issues": ["rule_module:bst"],
            "content_lane_pass": True,
        }
        row["failure_lanes"] = runner.classify_failure_lanes(row)
        self.assertIn("source_id_fidelity", row["failure_lanes"])
        self.assertEqual(runner.classify_failure(row), "citation")


if __name__ == "__main__":
    unittest.main()
