"""
Language detection only. Anthropic API enrichment removed.
Classification is done manually via Claude Code — see docs/enrich_prompt.md.
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
