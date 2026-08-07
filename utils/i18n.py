"""
Internationalization (i18n) Manager for Logiq Bot
Handles translation loading, language selection, string formatting, and config state persistence.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "en": "English",
    "ar": "العربية"
}

DEFAULT_LANGUAGE = "en"


class I18nManager:
    """Manages internationalization translations and language state"""

    def __init__(self, locales_dir: Optional[str] = None, default_lang: str = DEFAULT_LANGUAGE):
        if locales_dir is None:
            base_dir = Path(__file__).resolve().parent.parent
            if (base_dir / "internationalization").exists():
                locales_dir = base_dir / "internationalization"
            elif (base_dir / "i18n").exists():
                locales_dir = base_dir / "i18n"
            else:
                locales_dir = base_dir / "internationalization"

        self.locales_dir = Path(locales_dir)
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.current_language = default_lang if default_lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        self.load_translations()



    def load_translations(self):
        """Load all YAML translation files from the locales directory"""
        self.translations.clear()

        if not self.locales_dir.exists():
            logger.warning(f"Locales directory not found: {self.locales_dir}")
            return

        for lang_code in SUPPORTED_LANGUAGES:
            file_path = self.locales_dir / f"{lang_code}.yaml"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                        self.translations[lang_code] = data
                        logger.info(f"Loaded i18n translation: {lang_code} from {file_path}")
                except Exception as e:
                    logger.error(f"Failed to load translation file {file_path}: {e}")
                    self.translations[lang_code] = {}
            else:
                logger.warning(f"Translation file missing: {file_path}")
                self.translations[lang_code] = {}

    def get(self, key_path: str, lang: Optional[str] = None, **kwargs) -> str:
        """
        Get translated string for key path.
        Example: get('admin.reload_success', cog='moderation')
        """
        target_lang = lang if (lang and lang in SUPPORTED_LANGUAGES) else self.current_language
        
        # Try target language, fallback to English, fallback to key_path itself
        translation = self._resolve_key(target_lang, key_path)
        if translation is None and target_lang != DEFAULT_LANGUAGE:
            translation = self._resolve_key(DEFAULT_LANGUAGE, key_path)
        
        if translation is None:
            return key_path

        if isinstance(translation, str) and kwargs:
            try:
                return translation.format(**kwargs)
            except Exception as e:
                logger.warning(f"Formatting error for i18n key '{key_path}': {e}")
                return translation

        return str(translation)

    def _resolve_key(self, lang: str, key_path: str) -> Optional[Any]:
        """Traverse nested dict for key_path e.g. 'admin.reload_success'"""
        data = self.translations.get(lang, {})
        keys = key_path.split('.')
        
        curr = data
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return None
        return curr

    def set_language(self, lang_code: str, config_path: str = "config.yaml") -> bool:
        """
        Set active language and persist to config.yaml.
        """
        if lang_code not in SUPPORTED_LANGUAGES:
            return False

        self.current_language = lang_code
        self._save_to_config(lang_code, config_path)
        logger.info(f"Language state changed to: {lang_code}")
        return True

    def _save_to_config(self, lang_code: str, config_path: str):
        """Update config.yaml with new language setting"""
        path = Path(config_path)
        if not path.exists():
            # Try finding relative to project root
            path = Path(__file__).parent.parent / config_path

        if not path.exists():
            logger.warning(f"Config file not found at {path}, language state changed in memory only.")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            if "bot" not in config:
                config["bot"] = {}
            config["bot"]["language"] = lang_code

            if "i18n" not in config:
                config["i18n"] = {}
            config["i18n"]["language"] = lang_code

            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

            logger.info(f"Persisted language '{lang_code}' to {path}")
        except Exception as e:
            logger.error(f"Error persisting language setting to {config_path}: {e}")

    def get_language_name(self, lang_code: Optional[str] = None) -> str:
        """Get display name of language code"""
        code = lang_code or self.current_language
        return SUPPORTED_LANGUAGES.get(code, code)


# Global instance
i18n = I18nManager()


def t(key_path: str, lang: Optional[str] = None, **kwargs) -> str:
    """Shorthand global helper function for i18n lookup"""
    return i18n.get(key_path, lang=lang, **kwargs)
