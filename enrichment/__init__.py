"""
Language detection utility. Imported by scrapers.
The full classifier lives in enrichment/gemini_classifier.py.
"""
import re


def detect_language(text: str) -> str:
    has_arabic = bool(re.search(r"[؀-ۿ]", text))
    has_latin = bool(re.search(r"[a-zA-Z]", text))
    if has_arabic and has_latin:
        return "ar-en"
    if has_arabic:
        return "ar"
    return "en"
