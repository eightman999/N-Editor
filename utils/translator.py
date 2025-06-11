import os
import json

class Translator:
    def __init__(self, language='en'):
        self.language = language
        self.translations = {}
        self._load(language)

    @property
    def translations_dir(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'translations')

    def _load(self, language):
        path = os.path.join(self.translations_dir, f'{language}.json')
        if not os.path.exists(path):
            path = os.path.join(self.translations_dir, 'en.json')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.language = language
        except Exception:
            self.translations = {}
            self.language = language

    def set_language(self, language):
        self._load(language)

    def translate(self, key):
        return self.translations.get(key, key)

    def get_language_name(self, language):
        path = os.path.join(self.translations_dir, f'{language}.json')
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('language_name', language)
            except Exception:
                pass
        return language

    def get_available_languages(self):
        languages = {}
        if os.path.isdir(self.translations_dir):
            for filename in os.listdir(self.translations_dir):
                if filename.endswith('.json'):
                    code = os.path.splitext(filename)[0]
                    languages[code] = self.get_language_name(code)
        return languages

translator = Translator()
