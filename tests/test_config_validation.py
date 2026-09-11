"""Regression tests for configuration values passed to native-facing code."""

import unittest

from translation.translator import TranslationCache
from utils.config import AppConfig


class TestConfigValidation(unittest.TestCase):
    def test_invalid_numeric_values_fall_back_before_runtime_use(self):
        config = AppConfig(
            sensitivity="bad",
            vad_threshold=None,
            device_index=-5,
            sample_rate=0,
            chunk_duration=float("nan"),
            window_width=0,
            window_height=-1,
            translation_cache_size=0,
        )

        self.assertEqual(config.sensitivity, 1000)
        self.assertEqual(config.vad_threshold, 500)
        self.assertEqual(config.device_index, 0)
        self.assertEqual(config.sample_rate, 8000)
        self.assertEqual(config.chunk_duration, 3.0)
        self.assertEqual(config.window_width, 500)
        self.assertEqual(config.window_height, 400)
        self.assertEqual(config.translation_cache_size, 1)

    def test_zero_translation_cache_is_safe(self):
        cache = TranslationCache(maxsize=0)

        cache.put("key", "value")

        self.assertEqual(cache.get("key"), "value")
        self.assertEqual(cache.stats["maxsize"], 1)

    def test_translation_backend_and_model_are_normalized(self):
        config = AppConfig(
            translation_engine="TRANSLATEGEMMA",
            translategemma_model_id="  local/model  ",
        )

        self.assertEqual(config.translation_engine, "translategemma")
        self.assertEqual(config.translategemma_model_id, "local/model")

        fallback = AppConfig(translation_engine="unknown")
        self.assertEqual(fallback.translation_engine, "argos")


if __name__ == "__main__":
    unittest.main()
