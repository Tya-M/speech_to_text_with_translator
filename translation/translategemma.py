"""Local TranslateGemma backend for Russian to English translation.

The backend is intentionally optional.  The application can keep using Argos
when Transformers is not installed or while the TranslateGemma model is not
available locally.
"""

import gc
import importlib.util
import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Optional

from .translator import TranslationCache

logger = logging.getLogger("voice_translator.translation.translategemma")

TRANSLATEGEMMA_AVAILABLE = bool(
    importlib.util.find_spec("torch")
    and importlib.util.find_spec("transformers")
)


class TranslateGemmaTranslator:
    """Offline TranslateGemma 4B translator running on the CPU."""

    SOURCE_LANG = "ru"
    TARGET_LANG = "en"
    DEFAULT_MODEL_ID = "google/translategemma-4b-it"

    def __init__(
        self,
        cache_size: int = 100,
        model_id: str = DEFAULT_MODEL_ID,
    ):
        self._cache = TranslationCache(maxsize=cache_size)
        self.model_id = str(model_id or self.DEFAULT_MODEL_ID).strip()
        self._processor = None
        self._model = None
        self._torch = None
        self._is_loaded = False
        self._lock = threading.Lock()
        self._executor = self._new_executor()

    @staticmethod
    def _new_executor() -> ThreadPoolExecutor:
        # One worker avoids competing with GigaAM on the four-core Intel CPU.
        return ThreadPoolExecutor(max_workers=1, thread_name_prefix="TranslateGemma")

    def load(self) -> bool:
        """Load the official model, downloading it on first use if necessary."""
        if not TRANSLATEGEMMA_AVAILABLE:
            logger.error(
                "TranslateGemma недоступен: установите transformers и torch"
            )
            return False

        with self._lock:
            if self._executor is None:
                self._executor = self._new_executor()
        if self._is_loaded:
            return True

        try:
            import torch
            from transformers import AutoProcessor, AutoModelForImageTextToText

            logger.info("Загрузка TranslateGemma из %s на CPU...", self.model_id)
            processor = AutoProcessor.from_pretrained(self.model_id)
            model = AutoModelForImageTextToText.from_pretrained(
                self.model_id,
                torch_dtype=torch.float32,
            )
            model.to("cpu")
            model.eval()

            with self._lock:
                self._torch = torch
                self._processor = processor
                self._model = model
                self._is_loaded = True
            logger.info("TranslateGemma загружен на CPU")
            return True
        except Exception as exc:
            logger.error("Ошибка загрузки TranslateGemma: %s", exc)
            self._processor = None
            self._model = None
            self._torch = None
            self._is_loaded = False
            return False

    def unload(self) -> None:
        """Release model memory and stop the translation worker."""
        with self._lock:
            self._is_loaded = False
            self._processor = None
            self._model = None
            self._torch = None
            executor = self._executor
            self._executor = None
        self._cache.clear()
        if executor:
            executor.shutdown(wait=False, cancel_futures=True)
        gc.collect()
        logger.info("TranslateGemma выгружен")

    def _translate_loaded(self, text: str) -> str:
        """Translate one phrase using TranslateGemma's official chat template."""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "source_lang_code": self.SOURCE_LANG,
                        "target_lang_code": self.TARGET_LANG,
                        "text": text,
                    }
                ],
            }
        ]

        processor = self._processor
        model = self._model
        torch = self._torch
        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        if hasattr(inputs, "to"):
            inputs = inputs.to("cpu")
        else:
            inputs = {
                key: value.to("cpu") if hasattr(value, "to") else value
                for key, value in inputs.items()
            }

        input_len = inputs["input_ids"].shape[-1]
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=256,
            )
        generated = output[0][input_len:]
        return processor.decode(generated, skip_special_tokens=True).strip()

    def translate(self, text: str) -> Optional[str]:
        """Translate text synchronously, using the shared LRU cache."""
        if not text or not text.strip():
            return None
        text = text.strip()

        cached = self._cache.get(text)
        if cached is not None:
            return cached
        if not self._is_loaded or self._model is None:
            logger.error("TranslateGemma не загружен")
            return None

        try:
            start_time = time.time()
            with self._lock:
                translated = self._translate_loaded(text)
            self._cache.put(text, translated)
            logger.debug(
                "TranslateGemma перевёл за %.3fs: %s → %s",
                time.time() - start_time,
                text[:30],
                translated[:30],
            )
            return translated
        except Exception as exc:
            logger.error("Ошибка перевода TranslateGemma: %s", exc)
            return None

    def translate_async(self, text: str) -> Future:
        """Translate text without blocking the GUI thread."""
        with self._lock:
            if self._executor is None:
                self._executor = self._new_executor()
            return self._executor.submit(self.translate, text)

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    @property
    def cache_stats(self) -> dict:
        return self._cache.stats

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unload()
