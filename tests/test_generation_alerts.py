"""Offline and content-moderation dialogs, without opening a real message box."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from rotator.notify import (
    alert_generation_failure,
    is_content_moderated,
    is_offline_failure,
)

_MODERATED = (
    "Generation failed: xAI images HTTP 400: "
    '{"code":"imagine:content-moderated","error":"Generated image rejected by content moderation."}'
)
_DNS = (
    "Generation failed: gtm-research failed: "
    "xAI chat network error: [Errno 11001] getaddrinfo failed"
)
_SSL = (
    "Generation failed: <urlopen error [SSL: UNEXPECTED_EOF_WHILE_READING] "
    "EOF occurred in violation of protocol>"
)
_CREDITS = (
    "Generation failed: xAI chat HTTP 403: used all available credits "
    "or reached its monthly spending limit"
)


class TestFailureKinds(unittest.TestCase):
    def test_offline_matches_dns_and_dropped_download(self):
        self.assertTrue(is_offline_failure(_DNS))
        self.assertTrue(is_offline_failure(_SSL))
        self.assertTrue(is_offline_failure("xAI images network error: timed out"))

    def test_offline_does_not_steal_other_failures(self):
        self.assertFalse(is_offline_failure(_MODERATED))
        self.assertFalse(is_offline_failure(_CREDITS))
        self.assertFalse(is_offline_failure("Could not parse JSON from model"))
        self.assertFalse(is_offline_failure("xAI chat HTTP 403: invalid api key"))
        self.assertFalse(is_offline_failure(""))

    def test_moderation_phrase(self):
        self.assertTrue(is_content_moderated(_MODERATED))
        self.assertFalse(is_content_moderated(_DNS))

    def test_dialog_picks_one_cause(self):
        cases = (
            (_CREDITS, "No xAI credits"),
            (_MODERATED, "Image blocked"),
            (_DNS, "Couldn't reach xAI"),
            (_SSL, "Couldn't reach xAI"),
        )
        for message, title in cases:
            with patch("rotator.notify.show_alert", return_value=True) as show:
                self.assertTrue(alert_generation_failure(message))
                self.assertEqual(show.call_args.args[0], title)
                show.assert_called_once()

        with patch("rotator.notify.show_alert", return_value=True) as show:
            self.assertFalse(
                alert_generation_failure("Generation failed: Could not parse JSON from model")
            )
            show.assert_not_called()
