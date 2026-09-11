"""Regression test for flushing an unfinished GigaAM utterance."""

import unittest

import numpy as np

from recognition.gigaam_engine import GigaAMRecognizer
from utils.config import RecognitionConfig


class _FakeModel:
    def transcribe(self, path):
        return "Финальная фраза"


class TestGigaAMFinalize(unittest.TestCase):
    def test_finalize_stream_flushes_pending_speech(self):
        recognizer = GigaAMRecognizer(RecognitionConfig())
        recognizer._is_loaded = True
        recognizer._model = _FakeModel()

        silence = np.zeros(512, dtype=np.int16).tobytes()
        speech = np.full(int(0.4 * 16000), 2000, dtype=np.int16).tobytes()
        list(recognizer.recognize_stream(silence))
        list(recognizer.recognize_stream(speech))

        results = list(recognizer.finalize_stream())

        self.assertEqual([result.text for result in results], ["Финальная фраза"])
        self.assertFalse(recognizer._has_speech)


if __name__ == "__main__":
    unittest.main()
