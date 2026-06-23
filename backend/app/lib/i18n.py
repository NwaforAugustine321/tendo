"""Internationalization support — loads translations from JSON files."""

import json
import logging
import os
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

_TRANSLATIONS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "translations")


class I18N:
    """Handles loading and retrieving translated strings.

    Usage:
        from app.lib.i18n import t

        message = t("transactions.created")
        prompt = t("onboarding.name_prompt")
        error = t("errors.not_found")
        field = t("transactions.fields.total")
    """

    def __init__(self, locale: str = "en", custom_file: str | None = None):
        self._locale = locale
        self._data: dict[str, Any] = {}
        self._load(custom_file)

    def _load(self, custom_file: str | None = None) -> None:
        """Load translations from JSON file."""
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
        """
        Retrieve a translation by dot-notation key.

        Args:
            key: Dot-separated path (e.g., "transactions.created", "errors.not_found")
            **kwargs: Format variables to interpolate (e.g., balance="500")

        Returns:
            The translated string, or the key itself if not found.
        """
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
        """Get an entire section as a dict."""
        parts = section_key.split(".")
        value = self._data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, {})
            else:
                return {}
        return value if isinstance(value, dict) else {}

    def reload(self) -> None:
        """Reload translations from file (useful for hot-reload in dev)."""
        self._load()
        _get_i18n.cache_clear()


@lru_cache(maxsize=4)
def _get_i18n(locale: str = "en") -> I18N:
    """Get a cached I18N instance."""
    return I18N(locale=locale)


def t(key: str, locale: str = "en", **kwargs) -> str:
    """Shortcut to get a translated string.

    Usage:
        from app.lib.i18n import t

        t("transactions.created")
        t("transactions.balance_note", balance="500")
    """
    return _get_i18n(locale).get(key, **kwargs)


def get_section(section_key: str, locale: str = "en") -> dict:
    """Get an entire translation section as a dict.

    Usage:
        fields = get_section("transactions.fields")
    """
    return _get_i18n(locale).section(section_key)
