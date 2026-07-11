#!/usr/bin/env python3
"""
One-time diagnostic: is the Groq 403 a malformed GROQ_API_KEY (whitespace) or
a genuine block of this environment.

Never prints the key itself, only its length and whitespace state. The Groq
error response body for a 403 is safe to print, it is an error message and
error type, not a secret.

Run from the repo root:
    python scripts/diagnose_groq.py
"""
import os
import sys
import urllib.error
import urllib.request

from dotenv import load_dotenv
load_dotenv()

_MODELS_URL = "https://api.groq.com/openai/v1/models"


def _try_call(key: str) -> None:
    req = urllib.request.Request(
        _MODELS_URL,
        headers={"Authorization": f"Bearer {key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"HTTP status: {resp.status}")
            print("Groq is reachable and the key is accepted.")
            return
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP status: {exc.code}")
        print("Response body:")
        print(body[:2000])
    except (urllib.error.URLError, OSError) as exc:
        print(f"Network error, not an HTTP status: {exc}")


def main() -> None:
    raw_key = os.environ.get("GROQ_API_KEY", "")

    print(f"GROQ_API_KEY length: {len(raw_key)}")
    print(f"GROQ_API_KEY has leading whitespace: {raw_key != raw_key.lstrip()}")
    print(f"GROQ_API_KEY has trailing whitespace: {raw_key != raw_key.rstrip()}")

    if not raw_key:
        print("GROQ_API_KEY is empty or unset. Cannot make a test call.")
        sys.exit(1)

    print()
    print("Calling https://api.groq.com/openai/v1/models with the key exactly as loaded (unstripped):")
    _try_call(raw_key)

    stripped_key = raw_key.strip()
    if stripped_key != raw_key:
        print()
        print("Key had whitespace. Retrying with the stripped key to test whether whitespace is the cause:")
        _try_call(stripped_key)


if __name__ == "__main__":
    main()
