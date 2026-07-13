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
