import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import h2_c1_retrieval_only_probe as probe
import hpz2_llamacpp_h2_endpoint_runner as endpoint_runner


class RetrievalOnlyProbeTests(unittest.TestCase):
    def test_merge_weight_kg_matches_endpoint_context_merge(self):
        context = {"age": 3}
        merged = probe.merge_weight_kg(context, {"weight_kg": 15})
        self.assertEqual(merged["weight_kg"], 15)
        self.assertNotIn("weight_kg", context)

    def test_h2_old_aug_keeps_age_weight_dose_note_without_readding_codes(self):
        query = probe.old_aug_query(
            "dexisy a090 typow dexisy",
            {
                "age": 3,
                "weight_kg": 15.0,
                "orders": ["dexisy", "typow"],
                "order_details": [
                    {"code": "dexisy", "dose": "6.5mL TID", "_note": "15kg; BW range"},
                    {"code": "typow", "dose": "AAP TID"},
                ],
            },
        )
        self.assertIn("age 3", query)
        self.assertIn("3세", query)
        self.assertIn("weight_kg 15", query)
        self.assertIn("15kg", query)
        self.assertIn("dose 6.5mL TID", query)
        self.assertIn("15kg; BW range", query)
        self.assertNotIn("dexisy dose 6.5mL TID", query)

    def test_h2_current_variant_matches_endpoint_runner_augmentation(self):
        context = {
            "age": 3,
            "weight_kg": 15,
            "orders": ["dexisy", "typow"],
            "order_details": [{"code": "dexisy", "dose": "6.5mL TID"}],
        }
        case = {"expected_citations_includes_at_least": ["rule:drug:dexisy"]}
        variants = probe.base_variant_specs(
            base_query="dexisy a090",
            context=context,
            case=case,
            top_k=5,
            min_similarity=0.45,
            lexical_rerank=False,
        )
        current = next(item for item in variants if item["variant_id"] == "h2_current_aug")
        self.assertEqual(
            current["query"],
            endpoint_runner.augment_h2_retrieval_query("dexisy a090", context),
        )

    def test_primary_order_aug_uses_expected_rule_drug_code(self):
        context = {
            "age": 3,
            "weight_kg": 15,
            "order_details": [
                {"code": "typow", "dose": "AAP TID"},
                {"code": "dexisy", "dose": "6.5mL TID", "_note": "15kg; BW range"},
            ],
        }
        case = {"expected_citations_includes_at_least": ["rule:drug:dexisy"]}
        query = probe.primary_order_query("a090 dexisy typow", context, case)
        self.assertIn("dexisy dose 6.5mL TID", query)
        self.assertIn("dexisy 15kg; BW range", query)
        self.assertNotIn("typow dose AAP TID", query)

    def test_expected_rank_and_hit_at_k_summary(self):
        results = [
            {"source_id": "kb:a", "similarity": 0.9, "lexical_overlap": 1},
            {"source_id": "rule:drug:dexisy", "similarity": 0.8, "lexical_overlap": 2},
        ]
        summary = probe.summarize_variant(
            {"variant_id": "test", "query": "q", "top_k": 5, "min_similarity": 0.45, "lexical_rerank": False},
            results,
            ["rule:drug:dexisy", "kb:missing"],
        )
        self.assertEqual(summary["expected_source_rank"]["rule:drug:dexisy"], 2)
        self.assertIsNone(summary["expected_source_rank"]["kb:missing"])
        self.assertEqual(summary["hit_at_5"]["source_ids"], ["rule:drug:dexisy"])
        self.assertFalse(summary["hit_at_5"]["all"])
        self.assertEqual(summary["owner_hint"], "partial_retrieval_reachability")

    def test_retrieved_metadata_excludes_chunk_content(self):
        rows = probe.retrieved_metadata(
            [
                {
                    "source_id": "kb:source",
                    "similarity": 0.7,
                    "lexical_overlap": 3,
                    "chunk": {"content": "do not serialize"},
                }
            ],
            ["kb:source"],
        )
        self.assertEqual(rows[0]["source_id"], "kb:source")
        self.assertNotIn("chunk", rows[0])
        self.assertNotIn("content", rows[0])

    def test_preflight_paths_fails_closed_when_cache_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            emr = Path(tmp)
            (emr / "rag_index" / "_build").mkdir(parents=True)
            (emr / "rag_index" / "chunks").mkdir(parents=True)
            with self.assertRaises(probe.ProbeConfigError):
                probe.preflight_paths(emr)

    def test_snapshot_tree_detects_added_dirs_and_changed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("one", encoding="utf-8")

            before = probe.snapshot_tree(root)

            (root / "a.txt").write_text("changed-length", encoding="utf-8")
            (root / "b.txt").write_text("new", encoding="utf-8")
            (root / "subdir").mkdir()

            diff = probe.diff_tree_snapshots(before, probe.snapshot_tree(root))

        self.assertIn("a.txt", diff["changed"])
        self.assertIn("b.txt", diff["added"])
        self.assertIn("subdir/", diff["added"])

    def test_assert_emr_ignored_cache_unchanged_raises_on_rag_index_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            emr = Path(tmp)
            rag_index = emr / "rag_index"
            rag_index.mkdir()

            before = probe.emr_ignored_cache_snapshot(emr)
            (rag_index / "_build").mkdir()
            (rag_index / "_build" / "new-cache.bin").write_bytes(b"cache")
            after = probe.emr_ignored_cache_snapshot(emr)

        with self.assertRaisesRegex(probe.ProbeConfigError, "EMR ignored cache changed"):
            probe.assert_emr_ignored_cache_unchanged(before, after)

    def test_offline_env_is_forced_before_retriever_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = probe.set_offline_embedding_env(Path(tmp))
        self.assertEqual(env["HF_HUB_OFFLINE"], "1")
        self.assertEqual(env["TRANSFORMERS_OFFLINE"], "1")

    def test_import_emr_retrieval_disables_bytecode_before_imports(self):
        real_import = __import__
        previous_bytecode = sys.dont_write_bytecode
        previous_env = os.environ.get("PYTHONDONTWRITEBYTECODE")

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "app.llm.prompt_builder":
                self.assertTrue(sys.dont_write_bytecode)
                self.assertEqual(os.environ.get("PYTHONDONTWRITEBYTECODE"), "1")
                return types.SimpleNamespace(build_retrieval_query=lambda *_args, **_kwargs: "")
            if name == "app.rag.retriever":
                self.assertTrue(sys.dont_write_bytecode)
                self.assertEqual(os.environ.get("PYTHONDONTWRITEBYTECODE"), "1")
                return types.SimpleNamespace(Retriever=object)
            return real_import(name, globals, locals, fromlist, level)

        try:
            sys.dont_write_bytecode = False
            os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
            with patch("builtins.__import__", side_effect=fake_import):
                build_query, retriever_cls = probe.import_emr_retrieval(Path("C:/example/EMR_AI_24clinic"))
            self.assertEqual(build_query(), "")
            self.assertIs(retriever_cls, object)
        finally:
            sys.dont_write_bytecode = previous_bytecode
            if previous_env is None:
                os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
            else:
                os.environ["PYTHONDONTWRITEBYTECODE"] = previous_env


if __name__ == "__main__":
    unittest.main()
