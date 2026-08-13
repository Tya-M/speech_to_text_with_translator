"""
Тесты для Russian Voice Translator.
Запуск: python -m pytest tests/ -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfig:
    """Тесты конфигурации."""
    
    def test_config_defaults(self):
        from utils.config import AppConfig
        config = AppConfig()
        assert config.engine in ["vosk", "whisper"]
        assert 100 <= config.sensitivity <= 2000
    
    def test_config_validation(self):
        from utils.config import AppConfig
        config = AppConfig(sensitivity=5000, vad_threshold=50)
        assert config.sensitivity == 2000
        assert config.vad_threshold == 200


class TestTranslationCache:
    """Тесты LRU кэша."""
    
    def test_cache_lru_eviction(self):
        from translation.translator import TranslationCache
        cache = TranslationCache(maxsize=3)
        cache.put("a", "1")
        cache.put("b", "2")
        cache.put("c", "3")
        cache.get("a")
        cache.put("d", "4")
        assert cache.get("a") == "1"
        assert cache.get("b") is None


class TestHallucinationFilter:
    """Тесты фильтра галлюцинаций."""
    
    def test_filter_hallucinations(self):
        from recognition.whisper_engine import HallucinationFilter
        filt = HallucinationFilter()
        assert filt.is_hallucination("Редактор субтитров")
        assert filt.is_hallucination("да да да да да да")
        assert not filt.is_hallucination("Привет, как дела?")


class TestWhisperCppRecognizer:
    """Тесты wrapper-логики whisper.cpp без загрузки модели."""

    def test_recognize_uses_stable_russian_decode_params(self):
        import numpy as np

        from recognition.whispercpp_engine import WhisperCppRecognizer
        from utils.config import RecognitionConfig

        class Segment:
            text = "Привет мир"

        class FakeModel:
            def __init__(self):
                self.params = {}

            def transcribe(self, _audio, **params):
                self.params = params
                required = {
                    "language": "ru",
                    "translate": False,
                    "no_context": True,
                    "no_timestamps": True,
                    "single_segment": True,
                    "print_progress": False,
                    "suppress_nst": True,
                }
                if all(params.get(key) == value for key, value in required.items()):
                    return [Segment()]
                return []

        fake_model = FakeModel()
        recognizer = WhisperCppRecognizer(RecognitionConfig(), language="ru")
        recognizer._is_loaded = True
        recognizer._model = fake_model
        recognizer.gpu_active = True

        audio = np.array([1000, -1000], dtype=np.int16).tobytes()
        result = recognizer.recognize(audio)

        assert result is not None
        assert result.text == "Привет мир"
        assert result.engine == "whisper.cpp (Metal)"
        assert fake_model.params["translate"] is False

    def test_filters_english_live_fillers(self):
        from recognition.whispercpp_engine import WhisperCppRecognizer
        from utils.config import RecognitionConfig

        recognizer = WhisperCppRecognizer(RecognitionConfig(), language="ru")

        assert recognizer._clean_text("the") == ""
        assert recognizer._clean_text("ist") == ""
        assert recognizer._clean_text("multingatt") == ""
        assert recognizer._clean_text("funded") == ""
        assert recognizer._clean_text("thanks for watching") == ""
        assert recognizer._clean_text("Нихера не работает сюда.") == "Нихера не работает сюда."

    def test_filters_subtitle_and_garbled_hallucinations(self):
        from recognition.whispercpp_engine import WhisperCppRecognizer
        from utils.config import RecognitionConfig

        recognizer = WhisperCppRecognizer(RecognitionConfig(), language="ru")

        assert recognizer._clean_text("Смотрите на видео!") == ""
        assert recognizer._clean_text("СПОКОЙНАЯ МУЗЫКА") == ""
        assert recognizer._clean_text("Смешка.") == ""
        assert recognizer._clean_text("fl этотですdskem, that нель-c lives than- onère") == ""
        assert recognizer._clean_text("�-ice�ice predideаа е, yсьто mak") == ""
        assert recognizer._clean_text("Однажды в студию") == "Однажды в студию"

    def test_prefers_local_ggml_model_file(self):
        import tempfile
        from pathlib import Path

        from recognition.whispercpp_engine import WhisperCppRecognizer
        from utils.config import RecognitionConfig

        with tempfile.TemporaryDirectory() as tmp:
            model_file = Path(tmp) / "ggml-medium.bin"
            model_file.write_bytes(b"local model placeholder")
            recognizer = WhisperCppRecognizer(
                RecognitionConfig(),
                model_name="medium",
                model_dir=tmp,
                language="ru",
            )

            assert recognizer._model_path() == str(model_file)


class TestOfflineArgosSentencizer:
    """Тесты локального разбиения фраз для Argos."""

    def test_short_live_phrases_stay_offline(self):
        from translation.translator import OfflineSentenceSplitter

        splitter = OfflineSentenceSplitter()

        assert splitter.split_sentences("однажды в студёную зимнюю пору") == [
            "однажды в студёную зимнюю пору"
        ]
        assert splitter.split_sentences("Привет. Как дела?") == ["Привет.", "Как дела?"]


class TestThreadingUtils:
    """Тесты thread-safe утилит."""
    
    def test_queue(self):
        from utils.threading_utils import ThreadSafeQueue
        queue = ThreadSafeQueue()
        queue.put("item")
        assert queue.get() == "item"
    
    def test_counter(self):
        from utils.threading_utils import AtomicCounter
        counter = AtomicCounter()
        assert counter.increment() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
