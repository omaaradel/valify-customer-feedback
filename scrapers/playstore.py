"""
Google Play Store scraper using google-play-scraper.

Fetches reviews in Arabic then English for a given app ID, paginates
until the review date falls before `since`, or until max_per_lang is reached.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google_play_scraper import Sort, reviews
from google_play_scraper.exceptions import NotFoundError

from enrichment import detect_language

log = logging.getLogger(__name__)

_BATCH_SIZE = 200          # Reviews per API call
_SLEEP_BETWEEN_PAGES = 1.5  # Seconds between pagination calls
_SLEEP_BETWEEN_LANGS = 2.0  # Seconds between ar/en calls


def fetch(
    app_id: str,
    display_name: str,
    since: datetime,
    max_per_lang: int = 1000,
) -> List[Dict[str, Any]]:
    """Fetch Play Store reviews since `since`. Returns a list of normalized dicts."""
    if not app_id:
        log.warning("[%s] No Play Store app ID configured — skipping", display_name)
        return []

    results: List[Dict] = []
    for i, lang in enumerate(("ar", "en")):
        if i > 0:
            time.sleep(_SLEEP_BETWEEN_LANGS)
        lang_results = _fetch_lang(app_id, display_name, lang, since, max_per_lang)
        results.extend(lang_results)
        log.info("[%s] Play Store lang=%s: %d reviews", display_name, lang, len(lang_results))

    log.info("[%s] Play Store total: %d reviews since %s", display_name, len(results), since.date())
    return results


def _fetch_lang(
    app_id: str,
    display_name: str,
    lang: str,
    since: datetime,
    max_per_lang: int,
) -> List[Dict[str, Any]]:
    collected: List[Dict] = []
    continuation_token = None

    while len(collected) < max_per_lang:
        try:
            batch, continuation_token = reviews(
                app_id,
                lang=lang,
                country="eg",
                sort=Sort.NEWEST,
                count=_BATCH_SIZE,
                continuation_token=continuation_token,
            )
        except NotFoundError:
            log.error("[%s] Play Store app ID '%s' not found — check config.py", display_name, app_id)
            break
        except Exception as exc:
            log.warning("[%s] Play Store lang=%s error: %s", display_name, lang, exc)
            break

        if not batch:
            break

        cutoff_reached = False
        for r in batch:
            review_dt = _ensure_utc(r["at"])
            if review_dt < since:
                cutoff_reached = True
                break
            text = (r.get("content") or "").strip()
            if not text:
                continue  # skip rating-only reviews
            collected.append(_normalise(r, display_name, app_id))

        if cutoff_reached or continuation_token is None:
            break

        time.sleep(_SLEEP_BETWEEN_PAGES)

    return collected


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalise(r: Dict[str, Any], client_name: str, app_id: str) -> Dict[str, Any]:
    review_id = r.get("reviewId", "")
    text = (r.get("content") or "").strip()
    return {
        "client_name": client_name,
        "post_url": (
            f"https://play.google.com/store/apps/details"
            f"?id={app_id}&reviewId={review_id}"
        ),
        "source": "play_store",
        "post_date": _ensure_utc(r["at"]).isoformat(),
        "author": r.get("userName", ""),
        "raw_text": text,
        "rating": r.get("score"),
        "engagement": f"likes:{r.get('thumbsUpCount', 0)}, comments:0",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "language": detect_language(text),
        "sentiment": "",
        "feedback_type": "",
        "product_area": "",
        "severity": "",
        "agreement_signal": "",
        "claude_summary": "",
    }
