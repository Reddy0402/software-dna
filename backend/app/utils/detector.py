import os
from typing import Optional
from app.config import settings


class LanguageDetector:
    # Warm up sets from list configurations for O(1) lookups
    _ignored_filenames = {f.lower() for f in settings.IGNORED_FILENAMES}
    _ignored_extensions = {ext.lower() for ext in settings.IGNORED_EXTENSIONS}
    _language_map = {ext.lower(): lang for ext, lang in settings.LANGUAGE_MAP.items()}

    @classmethod
    def detect_language(cls, filename: str) -> Optional[str]:
        """
        Determines the programming language of a file based on its extension.
        Returns the language name if supported, otherwise returns None.
        Returns None if the file or extension is configured to be ignored.
        """
        if not filename:
            return None

        filename_lower = filename.strip().lower()

        # 1. Check if the exact filename is on the ignore list (e.g. package-lock.json)
        if filename_lower in cls._ignored_filenames:
            return None

        # 2. Extract the extension (e.g. '.py' -> 'py')
        _, ext_with_dot = os.path.splitext(filename_lower)
        ext = ext_with_dot.lstrip(".")

        if not ext:
            return None

        # 3. Check if the extension is on the ignore list (e.g. 'png', 'lock')
        if ext in cls._ignored_extensions:
            return None

        # 4. Map extension to programming language
        return cls._language_map.get(ext)
