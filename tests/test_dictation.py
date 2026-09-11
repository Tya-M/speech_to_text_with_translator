"""Regression tests for dictation worker boundaries."""

import queue
import threading
import unittest

from pynput import keyboard

from input_injection.dictation import DictationService
from utils.threading_utils import RecognitionResult


class _FakeRecognizer:
    def __init__(self, text, name="Fake"):
        self.text = text
        self._name = name

    @property
    def name(self):
        return self._name

    def recognize(self, data):
        if not self.text:
            return None
        return RecognitionResult(
            text=self.text,
            is_final=True,
            engine=self._name.lower(),
        )


class TestDictationWorkers(unittest.TestCase):
    def _service_for_hotkey_test(self, mode="hold"):
        service = object.__new__(DictationService)
        service.trigger = keyboard.Key.f9
        service.mode = mode
        service._listener = None
        service._running = True
        service._recording = threading.Event()
        service._control_queue = queue.Queue()
        return service

    def test_hotkey_callbacks_only_enqueue_audio_actions(self):
        service = self._service_for_hotkey_test()

        service._on_press(keyboard.Key.f9)
        service._on_release(keyboard.Key.f9)

        self.assertEqual(service._control_queue.get_nowait(), "begin")
        self.assertEqual(service._control_queue.get_nowait(), "finish")

    def test_transcription_worker_processes_requests_in_order(self):
        service = object.__new__(DictationService)
        service._transcription_queue = queue.Queue()
        processed = []
        service._transcribe_and_type = processed.append

        worker = threading.Thread(target=service._transcription_loop)
        worker.start()
        service._transcription_queue.put(b"first")
        service._transcription_queue.put(b"second")
        service._transcription_queue.put(None)
        service._transcription_queue.join()
        worker.join(timeout=1.0)

        self.assertFalse(worker.is_alive())
        self.assertEqual(processed, [b"first", b"second"])

    def test_parakeet_mode_prefers_russian_candidate_for_cyrillic_speech(self):
        service = object.__new__(DictationService)
        service.engine = "parakeet"
        service.recognizer = _FakeRecognizer("hello world", "Parakeet")
        service._secondary_recognizer = _FakeRecognizer("Привет мир", "GigaAM")
        service.on_status = lambda message: None

        result = service._recognize_cursor(b"audio")

        self.assertEqual(result.text, "Привет мир")

    def test_parakeet_mode_keeps_english_candidate_for_latin_speech(self):
        service = object.__new__(DictationService)
        service.engine = "parakeet"
        service.recognizer = _FakeRecognizer("hello world", "Parakeet")
        service._secondary_recognizer = _FakeRecognizer("", "GigaAM")
        service.on_status = lambda message: None

        result = service._recognize_cursor(b"audio")

        self.assertEqual(result.text, "hello world")

    def test_parakeet_service_creates_russian_fallback(self):
        from input_injection.dictation import GigaAMRecognizer

        service = DictationService(engine="parakeet")

        self.assertIsInstance(service._secondary_recognizer, GigaAMRecognizer)
        self.assertTrue(service._owns_secondary_recognizer)


if __name__ == "__main__":
    unittest.main()
