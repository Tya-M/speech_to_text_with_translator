"""
Лёгкий фильтр галлюцинаций/филлеров для вывода ASR-движков.

Вынесен в отдельный модуль, чтобы не зависеть от конкретного движка распознавания.
"""

import re


class HallucinationFilter:
    """Lightweight filter for common ASR filler/hallucination outputs."""

    _KNOWN_PHRASES = {
        "редактор субтитров",
        "субтитры создавал",
        "субтитры сделал",
        "спасибо за просмотр",
        "продолжение следует",
    }
    _FILLER_WORDS = {"а", "ага", "да", "угу", "мм", "м", "эм", "ээ", "ну"}

    def is_hallucination(self, text: str) -> bool:
        normalized = self._normalize(text)
        if not normalized:
            return True

        if normalized in self._KNOWN_PHRASES:
            return True

        words = normalized.split()
        if len(words) >= 5 and len(set(words)) == 1:
            return True

        return bool(words) and all(word in self._FILLER_WORDS for word in words)

    def clean(self, text: str) -> str:
        text = text.strip()
        if self.is_hallucination(text):
            return ""
        return text

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.strip().lower().replace("ё", "е")
        text = re.sub(r"[^\w\s]+", " ", text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", text).strip()
