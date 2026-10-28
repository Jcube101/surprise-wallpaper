"""Literary / painting diversity: bans, aliases, journal history."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rotator.daily import (
    _ban_from_used,
    _gtm_bans,
    _gtm_hits_ban,
    _gtm_used,
    _literary_bans,
    _literary_hits_ban,
    _literary_used,
    _painting_bans,
    _painting_hits_ban,
    _painting_used,
    _same_company,
    _same_painter,
    _same_work,
    ART_UNIQUE_BEFORE_REUSE,
)
from rotator.journal import iter_journal_records, parse_detail_fields


REAL_ROOT = Path(__file__).resolve().parents[1]


class TestNameMatching(unittest.TestCase):
    def test_book_aliases(self):
        self.assertTrue(_same_work("Moby-Dick", "Moby Dick"))
        self.assertTrue(_same_work("The Picture of Dorian Gray", "Dorian Gray"))
        self.assertTrue(_same_work("1984", "Nineteen Eighty-Four"))
        self.assertFalse(_same_work("Jane Eyre", "Pride and Prejudice"))

    def test_painting_aliases(self):
        self.assertTrue(_same_work("The Starry Night", "Starry Night"))
        self.assertTrue(_same_work("The Kiss reimagined", "The Kiss"))
        self.assertTrue(_same_work("Mona Lisa", "La Gioconda"))
        self.assertTrue(_same_work("Girl with a Pearl Earring", "Girl with Pearl Earring"))
        self.assertFalse(_same_work("The Kiss", "The Hay Wain"))

    def test_short_title_does_not_substring_match(self):
        self.assertFalse(_same_work("The Kiss", "The Kiss of Death scene"))

    def test_companies(self):
        self.assertTrue(_same_company("Lemonade", "Lemonade"))
        self.assertTrue(_same_company("Tesla — Energy", "Tesla"))
        self.assertTrue(_same_company("Tesla Energy", "Tesla"))
        self.assertTrue(_same_company("Robinhood — retail investing", "Robinhood — retail investors"))
        self.assertTrue(_same_company("Square", "Block"))
        self.assertFalse(_same_company("Canva", "Canvas"))
        self.assertFalse(_same_company("Stripe", "Datadog"))
        self.assertFalse(_same_company("Teladoc", "Tesla"))

    def test_painters(self):
        self.assertTrue(_same_painter("J.M.W. Turner", "J. M. W. Turner"))
        self.assertTrue(_same_painter("Rembrandt van Rijn", "Rembrandt"))
        self.assertTrue(_same_painter("Caravaggio", "Michelangelo Merisi da Caravaggio"))
        self.assertFalse(_same_painter("Rembrandt", "Turner"))
        self.assertFalse(_same_painter("John Singer Sargent", "John William Waterhouse"))


class TestBansFromRealJournal(unittest.TestCase):
    def test_parses_journal(self):
        recs = iter_journal_records(REAL_ROOT)
        self.assertGreater(len(recs), 20)
        lit = [r for r in recs if r.theme == "literary"]
        self.assertGreaterEqual(len(lit), 10)
        fields = parse_detail_fields(lit[-1].detail)
        self.assertIn("book", fields)

    def test_current_library_bans_repeats(self):
        books, _moments, painters = _literary_used(REAL_ROOT)
        bans = _literary_bans(REAL_ROOT)
        self.assertGreaterEqual(len(bans["books"]), 8)
        self.assertTrue(_same_work("Moby-Dick", next(b for b in books if "moby" in b.lower())))
        self.assertIn(
            True,
            [_same_painter("J.M.W. Turner", p) for p in painters],
        )
        # Under 30 unique books, everything used so far is banned.
        self.assertLess(len(bans["books"]), ART_UNIQUE_BEFORE_REUSE)
        self.assertTrue(_literary_hits_ban({"book": "Moby-Dick", "painter": "Goya"}, bans))
        self.assertTrue(
            _literary_hits_ban(
                {"book": "The Odyssey", "painter": "Rembrandt van Rijn"}, bans
            )
        )
        self.assertFalse(
            _literary_hits_ban({"book": "The Odyssey", "painter": "Goya"}, bans)
        )

        pb = _painting_bans(REAL_ROOT)
        self.assertTrue(_painting_hits_ban({"original_title": "The Kiss", "original_artist": "Fragonard"}, pb))
        self.assertTrue(
            _painting_hits_ban(
                {"original_title": "The Hay Wain", "original_artist": "Vincent van Gogh"},
                pb,
            )
        )
        self.assertFalse(
            _painting_hits_ban(
                {"original_title": "The Hay Wain", "original_artist": "John Constable"},
                pb,
            )
        )

        companies = _gtm_used(REAL_ROOT)
        gb = _gtm_bans(REAL_ROOT)
        self.assertTrue(any(_same_company(c, "Lemonade") for c in companies))
        self.assertTrue(_gtm_hits_ban({"company": "Lemonade"}, gb))
        self.assertTrue(_gtm_hits_ban({"company": "Tesla", "segment": "Energy"}, gb))
        self.assertTrue(_gtm_hits_ban({"company": "Teladoc"}, gb))
        self.assertTrue(_gtm_hits_ban({"company": "Robinhood", "segment": "retail"}, gb))
        self.assertFalse(_gtm_hits_ban({"company": "Duolingo"}, gb))


class TestBanWindow(unittest.TestCase):
    def test_bans_all_until_unique_threshold(self):
        used = ["Moby-Dick", "1984", "Jane Eyre"]
        banned = _ban_from_used(used, _same_work, min_unique=30, window=24)
        self.assertEqual(len(banned), 3)

    def test_window_after_threshold(self):
        used = [f"Book {i}" for i in range(40)]
        banned = _ban_from_used(used, _same_work, min_unique=30, window=24)
        self.assertEqual(len(banned), 24)
        self.assertTrue(_same_work(banned[0], "Book 16"))
        self.assertTrue(_same_work(banned[-1], "Book 39"))


class TestJournalFixture(unittest.TestCase):
    def test_fixture_journal(self):
        text = (
            "# Wallpaper journal\n\n"
            "## 2026-08-01 · literary · active\n\n"
            "- **File:** `x.jpg`\n"
            "- **Title:** Moby-Dick — Ahab's Final Strike\n"
            "- **Description:** spoiler\n"
            "- **Source:** xai-image\n"
            "- **Detail:** author=Herman Melville; book=Moby-Dick; painter=J.M.W. Turner; style_only=true\n"
            "\n"
            "## 2026-08-02 · painting · active\n\n"
            "- **File:** `y.jpg`\n"
            "- **Title:** The Starry Night reimagined\n"
            "- **Description:** sky\n"
            "- **Source:** xai-image\n"
            "- **Detail:** artist=Vincent van Gogh; direction=watercolor\n"
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "logs").mkdir()
            (root / "logs" / "wallpaper_journal.md").write_text(text, encoding="utf-8")
            books, moments, painters = _literary_used(root)
            self.assertEqual(books, ["Moby-Dick"])
            self.assertIn("Ahab", moments[0])
            self.assertTrue(_same_painter(painters[0], "Turner"))
            titles, artists = _painting_used(root)
            self.assertTrue(_same_work(titles[0], "Starry Night"))
            self.assertTrue(_same_painter(artists[0], "Van Gogh"))


if __name__ == "__main__":
    unittest.main()
