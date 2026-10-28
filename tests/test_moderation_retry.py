"""Literary and painting each retry Imagine once on content moderation."""

from __future__ import annotations

import unittest
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from rotator.config import Config
from rotator.daily import _gen_literary, _gen_painting

_MODERATED = RuntimeError(
    'xAI images HTTP 400: {"code":"imagine:content-moderated",'
    '"error":"Generated image rejected by content moderation."}'
)


class _Ev:
    est_usd = 0.0


def _cfg(tmp: Path) -> Config:
    daily = tmp / "Grok_Daily"
    daily.mkdir()
    return Config(
        grok_daily_dir=daily,
        curated_dir=tmp / "Curated",
        state_file=tmp / ".last_set.txt",
        log_file=tmp / "rotator.log",
    )


def _chat(plans: list[dict], notes: list[str], users: list[str]):
    def chat_json(system, user, **kwargs):
        notes.append(kwargs.get("note") or "")
        users.append(user)
        plan = plans[min(len(notes) - 1, len(plans) - 1)]
        return dict(plan), _Ev()

    return chat_json


class TestModerationRetry(unittest.TestCase):
    def test_literary_retries_once_then_saves(self):
        first = {
            "book": "The Odyssey",
            "author": "Homer",
            "moment_title": "Stringing the bow",
            "painter": "Vermeer",
            "painter_style_notes": "quiet daylight",
            "scene_prompt": "a man strings a bow in a still room",
            "description": "Quiet daylight.",
            "slug": "odyssey_bow",
        }
        second = {
            **first,
            "book": "Things Fall Apart",
            "moment_title": "The yam harvest",
            "painter": "Millet",
            "slug": "yam_harvest",
        }
        notes: list[str] = []
        users: list[str] = []
        saved: list[str] = []

        def save(prompt, dest, **kwargs):
            saved.append(kwargs.get("note") or "")
            if len(saved) == 1:
                raise _MODERATED
            return Path(dest)

        with TemporaryDirectory() as tmp:
            with (
                patch("rotator.daily.chat_json", _chat([first, second], notes, users)),
                patch("rotator.daily.save_generated", save),
            ):
                path, title, _desc, _detail, _cost = _gen_literary(
                    _cfg(Path(tmp)), Path(tmp), "2026-10-11"
                )
        self.assertEqual(len(saved), 2)
        self.assertEqual(notes, ["literary-plan", "literary-plan-moderation"])
        self.assertIn("DIFFERENT book", users[1])
        self.assertIn("Things Fall Apart", title)
        self.assertTrue(str(path).endswith("yam_harvest_millet.jpg"))

    def test_literary_second_block_propagates(self):
        plan = {
            "book": "The Odyssey",
            "author": "Homer",
            "moment_title": "Stringing the bow",
            "painter": "Vermeer",
            "scene_prompt": "a man strings a bow",
            "description": "Quiet.",
            "slug": "odyssey_bow",
        }
        notes: list[str] = []

        def save(prompt, dest, **kwargs):
            raise _MODERATED

        with TemporaryDirectory() as tmp:
            with (
                patch("rotator.daily.chat_json", _chat([plan, plan], notes, [])),
                patch("rotator.daily.save_generated", save),
            ):
                with self.assertRaises(RuntimeError) as caught:
                    _gen_literary(_cfg(Path(tmp)), Path(tmp), "2026-10-11")
        self.assertIn("content-moderated", str(caught.exception))
        self.assertEqual(notes, ["literary-plan", "literary-plan-moderation"])

    def test_literary_network_error_does_not_retry(self):
        plan = {
            "book": "The Odyssey",
            "author": "Homer",
            "moment_title": "Stringing the bow",
            "painter": "Vermeer",
            "scene_prompt": "a man strings a bow",
            "description": "Quiet.",
            "slug": "odyssey_bow",
        }
        notes: list[str] = []
        saves = {"n": 0}

        def save(prompt, dest, **kwargs):
            saves["n"] += 1
            raise RuntimeError("xAI images network error: [Errno 11001] getaddrinfo failed")

        with TemporaryDirectory() as tmp:
            with (
                patch("rotator.daily.chat_json", _chat([plan], notes, [])),
                patch("rotator.daily.save_generated", save),
            ):
                with self.assertRaises(RuntimeError) as caught:
                    _gen_literary(_cfg(Path(tmp)), Path(tmp), "2026-10-11")
        self.assertIn("getaddrinfo", str(caught.exception))
        self.assertEqual(saves["n"], 1)
        self.assertEqual(notes, ["literary-plan"])

    def test_download_drop_does_not_retry(self):
        plan = {
            "book": "The Odyssey",
            "author": "Homer",
            "moment_title": "Stringing the bow",
            "painter": "Vermeer",
            "scene_prompt": "a man strings a bow",
            "description": "Quiet.",
            "slug": "odyssey_bow",
        }
        saves = {"n": 0}

        def save(prompt, dest, **kwargs):
            saves["n"] += 1
            raise urllib.error.URLError("UNEXPECTED_EOF_WHILE_READING")

        with TemporaryDirectory() as tmp:
            with (
                patch("rotator.daily.chat_json", _chat([plan], [], [])),
                patch("rotator.daily.save_generated", save),
            ):
                with self.assertRaises(urllib.error.URLError):
                    _gen_literary(_cfg(Path(tmp)), Path(tmp), "2026-10-11")
        self.assertEqual(saves["n"], 1)

    def test_painting_second_block_propagates(self):
        plan = {
            "original_title": "The Night Watch",
            "original_artist": "Rembrandt",
            "reimagine_direction": "quiet winter street",
            "image_prompt": "clothed civic guard in winter light",
            "description": "Winter.",
            "slug": "night_watch_winter",
        }
        notes: list[str] = []
        saves = {"n": 0}

        def save(prompt, dest, **kwargs):
            saves["n"] += 1
            raise _MODERATED

        with TemporaryDirectory() as tmp:
            with (
                patch("rotator.daily.chat_json", _chat([plan, plan], notes, [])),
                patch("rotator.daily.save_generated", save),
            ):
                with self.assertRaises(RuntimeError) as caught:
                    _gen_painting(_cfg(Path(tmp)), Path(tmp), "2026-10-11")
        self.assertIn("content-moderated", str(caught.exception))
        self.assertEqual(saves["n"], 2)
        self.assertEqual(notes, ["painting-plan", "painting-plan-moderation"])
