"""
Groq provider (fallback when Gemini quota exhausts).

Uses the Groq OpenAI-compatible REST API via urllib — no extra pip dependency.
Default model: llama-3.3-70b-versatile (best multilingual quality on free tier).

Raises ProviderQuotaError on 429, ProviderUnavailableError on 503/500/network,
ProviderParseError on unparseable response. Never returns parse_error values.

Arabic quality note: Egyptian dialect classification must be tested on a 20-row
Arabic sample during Phase 9 before this provider is trusted in production.
If quality fails, replace with Ollama (Qwen2.5 or Aya-23).
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

_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_DEFAULT_MODEL = "llama-3.3-70b-versatile"


class GroqProvider(BaseProvider):
    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL):
        self._api_key = api_key
        self._model = model

    @property
    def name(self) -> str:
        return "groq"

    def _call_api(self, system_instruction: str, user_content: str) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.0,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            _API_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429:
                raise ProviderQuotaError(f"Groq 429: {body[:400]}") from exc
            if exc.code in (500, 503):
                raise ProviderUnavailableError(f"Groq {exc.code}: {body[:400]}") from exc
            raise
        except (urllib.error.URLError, OSError) as exc:
            raise ProviderUnavailableError(f"Groq network error: {exc}") from exc

    @staticmethod
    def _parse(raw: str) -> list:
        try:
            outer = json.loads(raw)
            text = outer["choices"][0]["message"]["content"].strip()
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(ln for ln in lines if not ln.strip().startswith("```")).strip()
            return json.loads(text)
        except Exception as exc:
            raise ProviderParseError(f"Groq parse error: {exc} | raw[:500]={raw[:500]}") from exc

    def classify_one_batch(self, batch: list, system_instruction: str) -> list:
        raw = self._call_api(system_instruction, classify_prompt(batch))
        return self._parse(raw)

    def enrich_one_batch(self, batch: list, system_instruction: str) -> list:
        raw = self._call_api(system_instruction, enrich_prompt(batch))
        return self._parse(raw)
