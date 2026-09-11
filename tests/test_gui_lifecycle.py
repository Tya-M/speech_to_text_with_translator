"""Regression tests for GUI callback and engine lifecycle boundaries."""

import threading
import unittest

from app.gui import VoiceTranslatorApp, TranscriptEntry
from utils.threading_utils import EngineManager, RecognitionResult, ThreadSafeQueue


class _FakeRoot:
    def __init__(self):
        self.cancelled = []

    def after_cancel(self, timer_id):
        self.cancelled.append(timer_id)


class _FakeText:
    def __init__(self):
        self.deleted = []
        self.unset_marks = []

    def mark_names(self):
        return ["partial_start"]

    def delete(self, start, end):
        self.deleted.append((start, end))

    def mark_unset(self, name):
        self.unset_marks.append(name)

    def tag_remove(self, tag, start, end):
        pass


class TestGuiLifecycle(unittest.TestCase):
    def _app_for_transcript_test(self):
        app = object.__new__(VoiceTranslatorApp)
        app._transcript_lock = threading.Lock()
        app._transcript_generation = 0
        app.result_queue = ThreadSafeQueue()
        app._partial_timer_id = "timer-1"
        app._pending_partial_text = "старый partial"
        app._last_applied_partial = "старый partial"
        app.transcript = [TranscriptEntry("старый текст")]
        app.root = _FakeRoot()
        app.text_area = _FakeText()
        app._partial_mark_name = "partial_start"
        return app

    def test_clear_invalidates_pending_results_and_partial_callbacks(self):
        app = self._app_for_transcript_test()
        stale = RecognitionResult("старый результат", is_final=True)
        app._enqueue_recognition_result(stale)

        app._clear_transcript()

        self.assertEqual(app._transcript_generation, 1)
        self.assertFalse(app._is_current_result(stale))
        self.assertIsNone(app.result_queue.get_nowait())
        self.assertEqual(app._pending_partial_text, "")
        self.assertIsNone(app._partial_timer_id)
        self.assertEqual(app.transcript, [])
        self.assertEqual(app.root.cancelled, ["timer-1"])

    def test_engine_manager_rejects_nested_switch(self):
        manager = EngineManager()

        with manager.switch_engine():
            self.assertTrue(manager.is_switching)
            with self.assertRaises(RuntimeError):
                with manager.switch_engine():
                    pass

        self.assertFalse(manager.is_switching)

    def test_srt_segments_are_relative_and_non_overlapping(self):
        app = object.__new__(VoiceTranslatorApp)
        app.transcript = [
            TranscriptEntry("first", timestamp=100.0),
            TranscriptEntry("second", timestamp=100.2),
            TranscriptEntry("third", timestamp=101.0),
        ]

        segments = app._srt_segments()

        self.assertEqual((segments[0][1], segments[0][2]), (0.0, 0.5))
        for previous, current in zip(segments, segments[1:]):
            self.assertLessEqual(previous[2], current[1])
        self.assertEqual(app._format_srt_time(61.234), "00:01:01,234")


if __name__ == "__main__":
    unittest.main()
