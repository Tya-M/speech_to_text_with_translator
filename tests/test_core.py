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
        assert config.engine in ["vosk", "gigaam"]
        assert config.gigaam_model in ["v3_e2e_ctc", "v3_e2e_rnnt"]
        assert 100 <= config.sensitivity <= 2000
    
    def test_config_validation(self):
        from utils.config import AppConfig
        config = AppConfig(sensitivity=5000, vad_threshold=50)
        assert config.sensitivity == 2000
        assert config.vad_threshold == 200

    def test_config_normalizes_invalid_gigaam_fields(self):
        from utils.config import AppConfig
        config = AppConfig(engine="unknown", gigaam_model="bogus", gigaam_device="gpu")
        assert config.engine == "gigaam"
        assert config.gigaam_model == "v3_e2e_rnnt"
        assert config.gigaam_device == "cpu"


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
        from recognition.filters import HallucinationFilter
        filt = HallucinationFilter()
        assert filt.is_hallucination("Редактор субтитров")
        assert filt.is_hallucination("да да да да да да")
        assert not filt.is_hallucination("Привет, как дела?")


class TestGigaAMRecognizer:
    """Тесты wrapper-логики GigaAM без загрузки реальной модели."""

    def test_recognize_transcribes_and_filters(self):
        import numpy as np

        from recognition.gigaam_engine import GigaAMRecognizer
        from utils.config import RecognitionConfig

        class FakeModel:
            def __init__(self):
                self.calls = []

            def transcribe(self, path):
                self.calls.append(path)
                return "Привет мир"

        recognizer = GigaAMRecognizer(RecognitionConfig(), model_name="v3_e2e_rnnt")
        recognizer._is_loaded = True
        recognizer._model = FakeModel()

        audio = np.array([1000, -1000, 1500, -1500], dtype=np.int16).tobytes()
        result = recognizer.recognize(audio)

        assert result is not None
        assert result.text == "Привет мир"
        assert result.engine == "gigaam"
        assert result.is_final is True

    def test_recognize_drops_hallucinations(self):
        import numpy as np

        from recognition.gigaam_engine import GigaAMRecognizer
        from utils.config import RecognitionConfig

        class FakeModel:
            def transcribe(self, path):
                return "Редактор субтитров"

        recognizer = GigaAMRecognizer(RecognitionConfig())
        recognizer._is_loaded = True
        recognizer._model = FakeModel()

        audio = np.array([1000, -1000], dtype=np.int16).tobytes()
        assert recognizer.recognize(audio) is None

    def test_extract_text_handles_object_with_text_attr(self):
        from recognition.gigaam_engine import GigaAMRecognizer

        class Result:
            text = "однажды в студию"

        assert GigaAMRecognizer._extract_text(Result()) == "однажды в студию"
        assert GigaAMRecognizer._extract_text("текст") == "текст"
        assert GigaAMRecognizer._extract_text(None) == ""


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
