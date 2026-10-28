"""Journal lookup + about text for the currently set wallpaper."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rotator.about import about_caption, about_view, format_about
from rotator.journal import JournalRecord, find_record_for_path, iter_journal_records


REAL_ROOT = Path(__file__).resolve().parents[1]


class TestFormatAbout(unittest.TestCase):
    def test_labels_title_description_detail(self):
        rec = JournalRecord(
            day="2026-08-25",
            theme="gtm",
            status="active",
            title="Oscar",
            filename="2026-08-25_gtm_oscar.png",
            description="Paid digital plus brokers.",
            detail="company=Oscar; industry=health insurance",
        )
        text = format_about(rec, Path(rec.filename))
        self.assertIn("Title\nOscar", text)
        self.assertIn("Description\nPaid digital plus brokers.", text)
        self.assertIn("Detail\ncompany=Oscar; industry=health insurance", text)
        self.assertEqual(about_caption(rec), "Wallpaper · gtm · 2026-08-25")
        view = about_view(rec, Path(rec.filename))
        self.assertEqual(view.kicker, "gtm  ·  2026-08-25")
        self.assertEqual(view.title, "Oscar")
        self.assertEqual(view.description, "Paid digital plus brokers.")
        self.assertEqual(view.detail, "company=Oscar; industry=health insurance")

    def test_missing_journal(self):
        p = Path("mystery.jpg")
        text = format_about(None, p)
        self.assertIn("Title\nmystery.jpg", text)
        self.assertIn("No journal entry", text)
        view = about_view(None, p)
        self.assertEqual(view.kicker, "mystery.jpg")
        self.assertIsNone(view.image)


class TestFindRecordForPath(unittest.TestCase):
    def test_matches_oscar_from_real_journal(self):
        image = REAL_ROOT / "Grok_Daily" / "2026-08-25_gtm_oscar.png"
        rec = find_record_for_path(REAL_ROOT, image)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.title, "Oscar")
        self.assertIn("insurance", rec.description.lower())
        self.assertIn("company=Oscar", rec.detail)

    def test_last_match_wins_in_fixture(self):
        text = (
            "# Wallpaper journal\n\n"
            "## 2026-08-01 · gtm · active\n\n"
            "- **File:** `dup.png`\n"
            "- **Title:** First\n"
            "- **Description:** old\n"
            "- **Source:** gtm-code\n"
            "- **Detail:** company=First\n"
            "\n"
            "## 2026-08-02 · gtm · active\n\n"
            "- **File:** `C:\\abs\\dup.png`\n"
            "- **Title:** Second\n"
            "- **Description:** new\n"
            "- **Source:** gtm-code\n"
            "- **Detail:** company=Second\n"
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "logs").mkdir()
            (root / "logs" / "wallpaper_journal.md").write_text(text, encoding="utf-8")
            recs = iter_journal_records(root)
            self.assertEqual(len(recs), 2)
            rec = find_record_for_path(root, Path("dup.png"))
            self.assertIsNotNone(rec)
            self.assertEqual(rec.title, "Second")


if __name__ == "__main__":
    unittest.main()
