"""Internationalization support — loads translations from JSON files."""

import json
import logging
import os
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

_TRANSLATIONS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "translations")


class I18N:
    def __init__(self, locale: str = "en", custom_file: str | None = None):
        self._locale = locale
        self._data: dict[str, Any] = {}
        self._load(custom_file)

    def _load(self, custom_file: str | None = None) -> None:
        if custom_file:
            file_path = custom_file
        else:
            file_path = os.path.join(_TRANSLATIONS_DIR, f"{self._locale}.json")

        try:
            with open(file_path, encoding="utf-8") as f:
                self._data = json.load(f)
            logger.debug(f"Loaded translations: {file_path}")
        except FileNotFoundError:
            logger.warning(f"Translation file not found: {file_path}")
            self._data = {}
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding translation file: {e}")
            self._data = {}

    def get(self, key: str, **kwargs) -> str:
    
        parts = key.split(".")
        value = self._data

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return key

            if value is None:
                return key

        if isinstance(value, str):
            try:
                return value.format(**kwargs) if kwargs else value
            except (KeyError, IndexError):
                return value

        return str(value) if value else key

    def section(self, section_key: str) -> dict:
        parts = section_key.split(".")
        value = self._data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, {})
            else:
                return {}
        return value if isinstance(value, dict) else {}

    def reload(self) -> None:
        self._load()
        _get_i18n.cache_clear()


@lru_cache(maxsize=4)
def _get_i18n(locale: str = "en") -> I18N:
    return I18N(locale=locale)


def t(key: str, locale: str = "en", **kwargs) -> str:
    return _get_i18n(locale).get(key, **kwargs)


def get_section(section_key: str, locale: str = "en") -> dict:
    return _get_i18n(locale).section(section_key)
