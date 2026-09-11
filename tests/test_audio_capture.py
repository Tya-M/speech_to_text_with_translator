"""
Тесты отказоустойчивости AudioCapture.
"""

import unittest
from unittest.mock import patch

import numpy as np

from audio.capture import AudioCapture, AudioDevice


class _FakeStream:
    def __init__(self):
        self.stopped = False
        self.closed = False

    def is_active(self) -> bool:
        return True

    def read(self, chunk_size: int, exception_on_overflow: bool = False) -> bytes:
        return b"\x00" * chunk_size

    def stop_stream(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


class _InactiveStream(_FakeStream):
    def is_active(self) -> bool:
        return False


class _FakePyAudio:
    def __init__(self, fail_on: set[int], fallback_ok_index: int):
        self.fail_on = fail_on
        self.fallback_ok_index = fallback_ok_index
        self.calls: list[int | None] = []
        self.stream = _FakeStream()

    def open(self, **kwargs):
        idx = kwargs.get("input_device_index")
        self.calls.append(idx)
        if idx in self.fail_on:
            raise OSError("[Errno -9986] Internal PortAudio error")
        if idx != self.fallback_ok_index:
            raise OSError(f"Unexpected device index: {idx}")
        return self.stream


class TestAudioCapture(unittest.TestCase):
    def test_start_capture_retries_with_default_device_when_selected_fails(self):
        """Если сохранённое устройство недоступно, захват должен переключиться на fallback."""
        capture = AudioCapture(device_index=7)
        fake_pa = _FakePyAudio(fail_on={7}, fallback_ok_index=2)
        capture._pyaudio = fake_pa

        with patch.object(AudioCapture, "_capture_loop", lambda self: None):
            with patch.object(
                capture,
                "get_default_input_device",
                lambda: AudioDevice(index=2, name="Default Mic", channels=1, sample_rate=16000, is_input=True),
            ):
                self.assertTrue(capture.start_capture())
                self.assertEqual(fake_pa.calls, [7, 2])

        capture.stop_capture()

    def test_stop_capture_closes_resources_after_worker_failure(self):
        capture = AudioCapture()
        stream = _FakeStream()
        capture._stream = stream
        capture._is_capturing = False

        capture.stop_capture()

        self.assertTrue(stream.stopped)
        self.assertTrue(stream.closed)

    def test_inactive_stream_marks_capture_stopped(self):
        capture = AudioCapture()
        capture._stream = _InactiveStream()
        capture._is_capturing = True
        failures = []
        capture.set_error_callback(failures.append)

        # _capture_loop is normally started by start_capture; this assertion
        # focuses on the failure-state transition after an inactive stream.
        capture._capture_thread = type("Thread", (), {
            "stopped": lambda self: False,
        })()
        capture._capture_loop()

        self.assertFalse(capture.is_capturing)
        self.assertEqual(failures, ["Аудиопоток стал неактивен"])

    def test_sensitivity_applies_clipped_pcm_gain(self):
        capture = AudioCapture(sensitivity=2000)
        samples = np.array([10000, -20000, 20000], dtype=np.int16)

        amplified = np.frombuffer(capture._apply_sensitivity(samples.tobytes()), dtype=np.int16)

        np.testing.assert_array_equal(amplified, [20000, -32768, 32767])

    def test_audio_constructor_normalizes_native_parameters(self):
        capture = AudioCapture(sample_rate=0, chunk_size=1, device_index=-4, sensitivity="bad")

        self.assertEqual(capture.sample_rate, AudioCapture.DEFAULT_RATE)
        self.assertEqual(capture.chunk_size, AudioCapture.CHUNK_SIZE)
        self.assertIsNone(capture.device_index)
        self.assertEqual(capture.sensitivity, 1000)
