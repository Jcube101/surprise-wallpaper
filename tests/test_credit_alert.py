"""Detect an xAI credits / spending-limit refusal without showing a dialog."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from rotator.notify import alert_if_credit_block, is_xai_credit_block

# Body returned on 2026-10-10 when desktop New produced no file.
_REFUSAL = (
    "Generation failed: gtm-research:Consumer media / entertainment product ( "
    "failed: xAI chat HTTP 403: "
    '{"code":"permission-denied","error":"Your team has either used all '
    "available credits or reached its monthly spending limit. To continue "
    "making API requests, please purchase more credits or raise your "
    'spending limit."}'
)


class TestCreditBlockDetection(unittest.TestCase):
    def test_real_403_is_a_credit_block(self):
        self.assertTrue(is_xai_credit_block(_REFUSAL))

    def test_image_endpoint_same_body(self):
        self.assertTrue(
            is_xai_credit_block(
                "xAI images HTTP 403: monthly spending limit reached"
            )
        )

    def test_other_failures_are_not_billing(self):
        self.assertFalse(is_xai_credit_block(""))
        self.assertFalse(is_xai_credit_block("XAI_API_KEY required for Grok chat research"))
        self.assertFalse(is_xai_credit_block("xAI chat HTTP 403: invalid api key"))
        self.assertFalse(is_xai_credit_block("xAI chat network error: timed out"))
        self.assertFalse(
            is_xai_credit_block("Generation failed: content-moderated")
        )

    def test_alert_only_for_credit_block(self):
        with patch("rotator.notify.show_alert", return_value=True) as show:
            self.assertTrue(alert_if_credit_block(_REFUSAL))
            show.assert_called_once()
            title, body = show.call_args.args
            self.assertIn("No xAI credits", title)
            self.assertIn("no credits left", body)
            self.assertIn("monthly spending limit", body)
            self.assertIsNone(show.call_args.kwargs.get("timeout_ms"))

        with patch("rotator.notify.show_alert", return_value=True) as show:
            self.assertFalse(alert_if_credit_block("xAI chat network error: timed out"))
            show.assert_not_called()

    def test_scheduled_alert_auto_dismisses(self):
        with patch("rotator.notify.show_alert", return_value=True) as show:
            alert_if_credit_block(_REFUSAL, timeout_ms=300_000)
            self.assertEqual(show.call_args.kwargs["timeout_ms"], 300_000)
