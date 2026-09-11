"""Regression tests for translator worker reuse after unload."""

import unittest

from translation.translator import Translator


class TestTranslationLifecycle(unittest.TestCase):
    def test_translator_can_submit_after_unload_and_reload(self):
        class FakeTranslation:
            def __init__(self, value):
                self.value = value

            def translate(self, text):
                return self.value

        translator = Translator()
        translator._is_loaded = True
        translator._translation_fn = FakeTranslation("готово")

        translator.unload()
        translator._is_loaded = True
        translator._translation_fn = FakeTranslation("снова готово")
        result = translator.translate_async("текст").result(timeout=1.0)

        self.assertEqual(result, "снова готово")
        translator.unload()


if __name__ == "__main__":
    unittest.main()
