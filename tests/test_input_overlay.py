"""Fullscreen Windows Input Experience windows block the desktop."""

from __future__ import annotations

import unittest

from rotator.windows_wallpaper import is_blocking_input_overlay

MONITOR = (0, 0, 1536, 864)


def _overlay(**overrides) -> bool:
    fields = dict(
        class_name="Windows.UI.Core.CoreWindow",
        title="Windows Input Experience",
        process_name="TextInputHost.exe",
        visible=True,
        window=(0, 0, 1536, 864),
        monitors=[MONITOR],
    )
    fields.update(overrides)
    return is_blocking_input_overlay(**fields)


class TestBlockingInputOverlay(unittest.TestCase):
    def test_fullscreen_input_experience_blocks(self):
        self.assertTrue(_overlay())

    def test_localized_title_still_blocks_when_process_matches(self):
        self.assertTrue(_overlay(title=""))

    def test_title_match_blocks_when_process_name_is_unavailable(self):
        self.assertTrue(_overlay(process_name=""))

    def test_touch_keyboard_strip_does_not_block(self):
        self.assertFalse(_overlay(window=(200, 500, 1000, 800)))

    def test_other_fullscreen_window_does_not_block(self):
        self.assertFalse(
            _overlay(class_name="Chrome_WidgetWin_1", title="Browser", process_name="chrome.exe")
        )

    def test_hidden_window_does_not_block(self):
        self.assertFalse(_overlay(visible=False))

    def test_window_covering_one_of_two_monitors_blocks(self):
        monitors = [MONITOR, (1536, 0, 3072, 864)]
        self.assertTrue(_overlay(window=(1536, 0, 3072, 864), monitors=monitors))

    def test_thin_input_bar_does_not_block(self):
        self.assertFalse(_overlay(window=(0, 0, 1521, 3)))


if __name__ == "__main__":
    unittest.main()
