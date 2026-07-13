"""
Модуль перевода с использованием Argos Translate.
Включает LRU кэширование для производительности.
"""

import logging
import threading
from collections import OrderedDict
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, Future
import time

logger = logging.getLogger("voice_translator.translation")

# Импортируем argostranslate с обработкой ошибки
try:
    import argostranslate.package
    import argostranslate.translate
    ARGOS_AVAILABLE = True
except ImportError:
    ARGOS_AVAILABLE = False
    logger.warning("Argos Translate не установлен. Используйте: pip install argostranslate")


class TranslationCache:
    """
    Thread-safe LRU кэш для переводов.
    """
    
    def __init__(self, maxsize: int = 100):
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._maxsize = maxsize
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[str]:
        """
        Получает значение из кэша.
        Перемещает элемент в конец (LRU).
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None
    
    def put(self, key: str, value: str) -> None:
        """
        Добавляет значение в кэш.
        Удаляет старейший элемент при переполнении.
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self._maxsize:
                    self._cache.popitem(last=False)
                self._cache[key] = value
    
    def clear(self) -> None:
        """Очищает кэш."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    @property
    def stats(self) -> dict:
        """Статистика кэша."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                "size": len(self._cache),
                "maxsize": self._maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate
            }


class Translator:
    """
    Офлайн переводчик Russian → English с использованием Argos Translate.
    """
    
    SOURCE_LANG = "ru"
    TARGET_LANG = "en"
    
    def __init__(self, cache_size: int = 100):
        self._cache = TranslationCache(maxsize=cache_size)
        self._translation_fn = None
        self._is_loaded = False
        self._lock = threading.Lock()
        # 1 worker для Intel i5 4-core — избегаем конкуренции с Vosk за CPU
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="Translator")
    
    def load(self) -> bool:
        """
        Загружает и инициализирует переводчик.
        Скачивает языковой пакет если нужно.
        """
        if not ARGOS_AVAILABLE:
            logger.error("Argos Translate недоступен")
            return False
        
        if self._is_loaded:
            return True
        
        try:
            logger.info("Инициализация Argos Translate...")
            
            # Обновляем индекс пакетов с таймаутом чтобы избежать зависания
            import socket
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(10.0)
            try:
                argostranslate.package.update_package_index()
            finally:
                socket.setdefaulttimeout(original_timeout)
            
            # Проверяем, установлен ли нужный пакет
            installed_languages = argostranslate.translate.get_installed_languages()
            
            source_lang = None
            target_lang = None
            
            for lang in installed_languages:
                if lang.code == self.SOURCE_LANG:
                    source_lang = lang
                elif lang.code == self.TARGET_LANG:
                    target_lang = lang
            
            # Если пакет не установлен, устанавливаем
            if source_lang is None or target_lang is None:
                logger.info("Установка языкового пакета ru→en...")
                
                available_packages = argostranslate.package.get_available_packages()
                package_to_install = None
                
                for pkg in available_packages:
                    if pkg.from_code == self.SOURCE_LANG and pkg.to_code == self.TARGET_LANG:
                        package_to_install = pkg
                        break
                
                if package_to_install is None:
                    logger.error("Языковой пакет ru→en не найден")
                    return False
                
                download_path = package_to_install.download()
                argostranslate.package.install_from_path(download_path)
                logger.info("Языковой пакет установлен")
                
                # Обновляем список языков
                installed_languages = argostranslate.translate.get_installed_languages()
                for lang in installed_languages:
                    if lang.code == self.SOURCE_LANG:
                        source_lang = lang
                    elif lang.code == self.TARGET_LANG:
                        target_lang = lang
            
            # Получаем функцию перевода
            if source_lang and target_lang:
                self._translation_fn = source_lang.get_translation(target_lang)
                
                if self._translation_fn is None:
                    logger.error("Не удалось создать функцию перевода")
                    return False
                
                self._is_loaded = True
                logger.info("Argos Translate инициализирован")
                return True
            
            logger.error("Не удалось найти языки после установки")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка инициализации Argos: {e}")
            return False
    
    def unload(self) -> None:
        """Выгружает переводчик."""
        self._translation_fn = None
        self._is_loaded = False
        self._cache.clear()
        self._executor.shutdown(wait=False)
        logger.info("Переводчик выгружен")
    
    def translate(self, text: str) -> Optional[str]:
        """
        Синхронный перевод текста.
        Использует кэш для повторных запросов.
        """
        if not text or not text.strip():
            return None
        
        text = text.strip()
        
        # Проверяем кэш
        cached = self._cache.get(text)
        if cached is not None:
            logger.debug(f"Cache hit: {text[:30]}...")
            return cached
        
        if not self._is_loaded or self._translation_fn is None:
            logger.error("Переводчик не загружен")
            return None
        
        try:
            start_time = time.time()
            
            with self._lock:
                translated = self._translation_fn.translate(text)
            
            translation_time = time.time() - start_time
            logger.debug(f"Перевод за {translation_time:.3f}с: {text[:30]} → {translated[:30]}")
            
            # Сохраняем в кэш
            self._cache.put(text, translated)
            
            return translated
            
        except Exception as e:
            logger.error(f"Ошибка перевода: {e}")
            return None
    
    def translate_async(self, text: str) -> Future:
        """
        Асинхронный перевод текста.
        Возвращает Future с результатом.
        """
        return self._executor.submit(self.translate, text)
    
    @property
    def is_loaded(self) -> bool:
        """Проверяет, загружен ли переводчик."""
        return self._is_loaded
    
    @property
    def cache_stats(self) -> dict:
        """Возвращает статистику кэша."""
        return self._cache.stats
    
    def __enter__(self):
        self.load()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unload()
