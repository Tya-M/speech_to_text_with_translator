"""
Тесты отказоустойчивости AudioCapture.
"""

import unittest
from unittest.mock import patch

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
