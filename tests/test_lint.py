import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from zh_claim_lint import check


class LintTests(unittest.TestCase):
    def test_flags_new_facts_in_draft_order(self):
        source = "2026年4月9日，样品折扣为8%，预算1.2万元。"
        draft = "公告为第900号公告，2026-04-10执行。\n折扣18%，预算2万元。"
        hits = check(source, draft)
        self.assertEqual([x.text for x in hits], ["第900号公告", "2026-04-10", "18%", "2万元"])
        self.assertEqual((hits[2].line, hits[2].column), (2, 3))
        self.assertEqual(draft[hits[2].start:hits[2].end], "18%")

    def test_normalizes_format_not_value(self):
        self.assertEqual(check("2026年4月9日，1.2万元，8.0％，第9号公告。",
                               "２０２６－０４－０９，12,000元，8%，第９号公告。"), [])

    def test_currencies_and_document_year_are_not_interchangeable(self):
        hits = check("800美元；2026年第12号公告。", "800元；2027年第12号公告。")
        self.assertEqual([x.kind for x in hits], ["money", "notice"])

    def test_bad_dates_are_not_silently_equated_with_valid_dates(self):
        hits = check("2026-02-28", "2026年2月30日")
        self.assertEqual([x.kind for x in hits], ["date"])

    def test_unformatted_numbers_not_claimed_as_supported(self):
        self.assertEqual(check("", "第9章说有三只。"), [])

    def test_partial_matches_and_duplicate_coordinates(self):
        hits = check("118%，12.5元", "18%，不等于18%。\n5元。")
        self.assertEqual([(x.text, x.line, x.column) for x in hits],
                         [("18%", 1, 1), ("18%", 1, 8), ("5元", 2, 1)])

    def test_a_range_is_not_treated_as_two_standalone_claims(self):
        hits = check("8%与10%", "8%–10%")
        self.assertEqual([x.text for x in hits], ["8%–10%"])
        self.assertEqual(check("８％至１０％", "8–10%"), [])

    def test_list_punctuation_does_not_hide_next_claim(self):
        self.assertEqual([x.text for x in check("无数字", "8%，10%，2元")],
                         ["8%", "10%", "2元"])

    def test_negative_and_positive_values_differ(self):
        self.assertEqual(check("利润变化5%", "利润变化-5%")[0].text, "-5%")


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "zh_claim_lint", *args],
                              capture_output=True, text=True, encoding="utf-8", timeout=10)

    def test_review_exit_and_json(self):
        with tempfile.TemporaryDirectory() as folder:
            src = Path(folder, "source.txt")
            draft = Path(folder, "draft.txt")
            src.write_text("\ufeff原值10%。", encoding="utf-8")
            draft.write_text("现值11%。", encoding="utf-8")
            result = self.run_cli(str(src), str(draft), "--format", "json")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(result.stdout)["findings"][0]["text"], "11%")
            self.assertEqual(self.run_cli(str(src), str(src)).returncode, 0)

    def test_missing_and_empty_source_are_usage_errors(self):
        result = self.run_cli("no-such-reference", "no-such-draft")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder, "empty")
            source.write_text(" ", encoding="utf-8")
            result = self.run_cli(str(source), str(source))
            self.assertEqual(result.returncode, 2)
