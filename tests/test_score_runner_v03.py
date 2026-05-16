import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import score_runner


class ScoreRunnerV03Test(unittest.TestCase):
    def test_format_only_fail_scores_four(self):
        self.assertEqual(
            score_runner.compute_score(
                hard_fail=False,
                required_missing_count=0,
                forbidden_present_count=0,
                format_pass=False,
            ),
            4,
        )

    def test_sentence_tolerance_defaults_to_two(self):
        rubric = {
            "format_requirements": {
                "language": "ko",
                "min_sentences": 3,
                "max_sentences": 4,
            }
        }
        response = "첫 문장. 둘째 문장. 셋째 문장. 넷째 문장. 다섯째 문장. 여섯째 문장."
        result = score_runner.check_format(response, rubric, {})
        self.assertTrue(result["pass"])
        self.assertEqual(result["issues"], [])

    def test_required_marker_object(self):
        rubric = {
            "format_requirements": {
                "language": "ko",
                "required_marker": {"text": "[확인 필요]", "min_count": 1},
            }
        }
        missing = score_runner.check_format("어지러움만 기록됨.", rubric, {})
        present = score_runner.check_format("어지러움 원인 [확인 필요].", rubric, {})
        self.assertFalse(missing["pass"])
        self.assertIn("MISSING_REQUIRED_ELEMENT", missing["tags"])
        self.assertTrue(present["pass"])

    def test_d01_change_noun_is_not_forbidden_in_v03(self):
        prompts = json.loads((ROOT / "prompts" / "test_suite_v0.3.json").read_text(encoding="utf-8"))
        d01 = next(test for test in prompts["tests"] if test["id"] == "D_01")
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "d_smoke_gpt_oss_20b_low.json").read_text(encoding="utf-8")
        )
        response_record = next(test for test in fixture["tests"] if test["id"] == "D_01")
        scored = score_runner.score_one(d01, response_record, prompts)
        self.assertEqual(scored["forbidden_present"], [])
        self.assertEqual(scored["score"], 5)


if __name__ == "__main__":
    unittest.main()
