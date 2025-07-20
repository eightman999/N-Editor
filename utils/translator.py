import json
import os
from typing import Dict

try:
    from googletrans import Translator as _GoogleTranslator
except Exception:  # googletrans may not be installed or fail
    _GoogleTranslator = None

class Translator:
    def __init__(self, language: str = 'ja', lang_dir: str | None = None) -> None:
        self.language = language
        self.lang_dir = (
            lang_dir
            or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'lang')
        )
        self.strings: Dict[str, str] = {}
        self.auto_translations: Dict[str, str] = {}
        self.google = _GoogleTranslator() if _GoogleTranslator else None
        self.load_language(language)

    def apply_to_widget(self, widget) -> None:
        """Recursively apply translation to widget texts."""
        from PyQt5.QtWidgets import QWidget
        if not isinstance(widget, QWidget):
            return

        def _translate_child(w):
            if hasattr(w, 'text') and callable(getattr(w, 'text')) and hasattr(w, 'setText'):
                original = w.text()
                if original:
                    w.setText(self.gettext(original))

            # Special handling for QTabWidget
            from PyQt5.QtWidgets import QTabWidget
            if isinstance(w, QTabWidget):
                for i in range(w.count()):
                    text = w.tabText(i)
                    if text:
                        w.setTabText(i, self.gettext(text))

        for child in widget.findChildren(QWidget):
            _translate_child(child)

    def load_language(self, language: str) -> None:
        """Load translation file for the specified language"""
        lang_file = os.path.join(self.lang_dir, f'{language}.json')
        auto_file = os.path.join(self.lang_dir, f'{language}_auto.json')
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.strings = json.load(f)
        except Exception:
            self.strings = {}
        try:
            with open(auto_file, 'r', encoding='utf-8') as f:
                self.auto_translations = json.load(f)
        except Exception:
            self.auto_translations = {}
        self.language = language

    def _save_auto_translations(self) -> None:
        if not self.auto_translations:
            return
        auto_file = os.path.join(self.lang_dir, f'{self.language}_auto.json')
        try:
            with open(auto_file, 'w', encoding='utf-8') as f:
                json.dump(self.auto_translations, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def gettext(self, key: str) -> str:
        """Retrieve the translated string for the given key"""
        if key in self.strings:
            return self.strings[key]
        if key in self.auto_translations:
            return self.auto_translations[key]
        if self.language != 'ja' and self.google is not None:
            try:
                result = self.google.translate(key, src='ja', dest=self.language).text
                self.auto_translations[key] = result
                self._save_auto_translations()
                return result
            except Exception:
                pass
        return key
