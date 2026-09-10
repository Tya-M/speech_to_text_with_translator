"""Parakeet Unified English recognizer through sherpa-onnx.

The model is optional. The application keeps working with GigaAM when
``sherpa_onnx`` or the local Parakeet model is not installed.
"""

import importlib.util
import logging
from pathlib import Path
from typing import Generator, Optional

import numpy as np

from .base import BaseRecognizer
from utils.config import RecognitionConfig
from utils.threading_utils import RecognitionResult

logger = logging.getLogger("voice_translator.recognition.parakeet")

SHERPA_AVAILABLE = importlib.util.find_spec("sherpa_onnx") is not None


class ParakeetRecognizer(BaseRecognizer):
    """Offline English Parakeet Unified EN INT8 recognizer."""

    FEATURE_DIM = 128

    def __init__(
        self,
        config: RecognitionConfig,
        model_path: str = "sherpa-onnx-nemo-parakeet-unified-en-0.6b-int8-non-streaming",
        num_threads: int = 2,
    ):
        super().__init__(config)
        self.model_path = self._resolve_model_path(model_path)
        self.num_threads = max(1, int(num_threads))
        self._recognizer = None
        self._model_name = "Parakeet Unified EN 0.6B INT8"

    @staticmethod
    def _resolve_model_path(model_path: str) -> Path:
        path = Path(model_path).expanduser()
        if path.is_absolute():
            return path
        return Path(__file__).resolve().parent.parent / path

    def load(self) -> bool:
        """Load the local sherpa-onnx recognizer."""
        if self._is_loaded:
            return True
        if not SHERPA_AVAILABLE:
            logger.error(
                "sherpa_onnx is unavailable; install sherpa-onnx and sherpa-onnx-bin"
            )
            return False

        files = {
            "tokens": self.model_path / "tokens.txt",
            "encoder": self.model_path / "encoder.int8.onnx",
            "decoder": self.model_path / "decoder.int8.onnx",
            "joiner": self.model_path / "joiner.int8.onnx",
        }
        missing = [name for name, path in files.items() if not path.is_file()]
        if missing:
            logger.error(
                "Parakeet model is incomplete at %s; missing: %s",
                self.model_path,
                ", ".join(missing),
            )
            return False

        try:
            import sherpa_onnx

            self._recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=str(files["encoder"]),
                decoder=str(files["decoder"]),
                joiner=str(files["joiner"]),
                tokens=str(files["tokens"]),
                num_threads=self.num_threads,
                sample_rate=self.config.sample_rate,
                feature_dim=self.FEATURE_DIM,
                decoding_method="greedy_search",
                provider="cpu",
                model_type="nemo_transducer",
            )
            self._is_loaded = True
            logger.info(
                "Parakeet model loaded from %s using %d threads",
                self.model_path,
                self.num_threads,
            )
            return True
        except Exception as exc:
            logger.error("Unable to load Parakeet: %s", exc)
            self._recognizer = None
            self._is_loaded = False
            return False

    def unload(self) -> None:
        self._recognizer = None
        self._is_loaded = False

    def recognize(self, audio_data: bytes) -> Optional[RecognitionResult]:
        """Recognize PCM16 mono audio at the configured sample rate."""
        if not self._is_loaded or self._recognizer is None:
            logger.error("Parakeet is not loaded")
            return None
        if not audio_data:
            return None

        try:
            samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            samples /= 32768.0
            stream = self._recognizer.create_stream()
            stream.accept_waveform(self.config.sample_rate, samples)
            self._recognizer.decode_stream(stream)
            text = str(stream.result.text or "").strip()
            if not text:
                return None
            return RecognitionResult(
                text=text,
                is_final=True,
                confidence=0.0,
                engine="parakeet",
            )
        except Exception as exc:
            logger.error("Parakeet recognition failed: %s", exc)
            return None

    def recognize_stream(self, audio_chunk: bytes) -> Generator[RecognitionResult, None, None]:
        """Treat a supplied chunk as a complete utterance.

        The current Parakeet model is non-streaming, so the main application
        should use push-to-talk and call :meth:`recognize` after recording.
        """
        result = self.recognize(audio_chunk)
        if result is not None:
            yield result
