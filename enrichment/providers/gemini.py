"""
Gemini Flash provider (primary enrichment provider).

Raises ProviderQuotaError on 429, ProviderUnavailableError on 503/500/network,
ProviderParseError on unparseable response. Never returns parse_error values.
"""
import json
import urllib.error
import urllib.request

from enrichment.providers.base import (
    BaseProvider,
    ProviderParseError,
    ProviderQuotaError,
    ProviderUnavailableError,
    classify_prompt,
    enrich_prompt,
)

_MODEL = "gemini-3.5-flash"
_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + _MODEL
    + ":generateContent"
)


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: str):
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "gemini"

    def _call_api(self, system_instruction: str, user_content: str) -> str:
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": {"temperature": 0.0},
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        url = _API_URL + "?key=" + self._api_key
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429:
                raise ProviderQuotaError(f"Gemini 429: {body[:400]}") from exc
            if exc.code in (500, 503):
                raise ProviderUnavailableError(f"Gemini {exc.code}: {body[:400]}") from exc
            raise
        except (urllib.error.URLError, OSError) as exc:
            raise ProviderUnavailableError(f"Gemini network error: {exc}") from exc

    @staticmethod
    def _parse(raw: str) -> list:
        try:
            outer = json.loads(raw)
            text = outer["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(ln for ln in lines if not ln.strip().startswith("```")).strip()
            return json.loads(text)
        except Exception as exc:
            raise ProviderParseError(f"Gemini parse error: {exc} | raw[:500]={raw[:500]}") from exc

    def classify_one_batch(self, batch: list, system_instruction: str) -> list:
        raw = self._call_api(system_instruction, classify_prompt(batch))
        return self._parse(raw)

    def enrich_one_batch(self, batch: list, system_instruction: str) -> list:
        raw = self._call_api(system_instruction, enrich_prompt(batch))
        return self._parse(raw)
