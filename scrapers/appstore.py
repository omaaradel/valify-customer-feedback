"""
Apple App Store scraper using the public iTunes RSS JSON feed.

app-store-scraper 0.3.5 was installed but its internal endpoint (amp-api.apps.apple.com)
returns empty for the Egypt storefront. The iTunes RSS endpoint
(itunes.apple.com/{country}/rss/customerreviews/...) is confirmed working and is the
same public data, free, no auth required.

Fetches up to 10 pages x 50 reviews = 500 max per app per run. No language filter:
Apple serves whatever language reviewers wrote in. Date filtering is client-side.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

from enrichment import detect_language

log = logging.getLogger(__name__)

_BASE_URL = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortBy=mostRecent/json"
_MAX_PAGES = 10          # Apple RSS caps at 10 pages of 50 each = 500 max
_SLEEP_BETWEEN_PAGES = 2.0
_SLEEP_BETWEEN_CLIENTS = 12.0   # wired into the client loop in main.py via sleep_before param
_RETRY_WAIT_ON_EMPTY = 30.0     # wait before one retry when page 1 returns an empty entry array
_SESSION_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    ),
}


def fetch(
    app_id: str,
    display_name: str,
    since: datetime,
    country: str = "eg",
    sleep_before: bool = False,
) -> Tuple[List[Dict[str, Any]], bool]:
    """Fetch App Store reviews since `since`.

    Returns (rows, suspected_block). suspected_block=True means Apple returned
    an empty feed on page 1 even after a 30-second retry, suggesting CDN throttling.
    The caller must treat a suspected-block zero differently from a genuine empty result.

    sleep_before: if True, sleeps _SLEEP_BETWEEN_CLIENTS seconds before the first
    request. Set by the caller (main.py) when this is not the first App Store client
    in a multi-client run. This is what wires _SLEEP_BETWEEN_CLIENTS into the loop.
    """
    if not app_id:
        log.warning("[%s] No App Store ID configured -- skipping", display_name)
        return [], False

    if sleep_before:
        log.info(
            "[%s] App Store: sleeping %.0fs before client (inter-client pacing)",
            display_name, _SLEEP_BETWEEN_CLIENTS,
        )
        time.sleep(_SLEEP_BETWEEN_CLIENTS)

    session = requests.Session()
    session.headers.update(_SESSION_HEADERS)

    rows, suspected_block = _attempt_fetch(app_id, display_name, since, country, session)

    if suspected_block:
        log.error(
            "[%s] App Store suspected block: page 1 empty entry array. "
            "Waiting %.0fs before retry.",
            display_name, _RETRY_WAIT_ON_EMPTY,
        )
        time.sleep(_RETRY_WAIT_ON_EMPTY)
        retry_rows, still_blocked = _attempt_fetch(app_id, display_name, since, country, session)
        if still_blocked:
            log.error(
                "[%s] App Store suspected block confirmed after retry. Returning 0 rows.",
                display_name,
            )
            return [], True
        rows = retry_rows
        log.info(
            "[%s] App Store retry recovered %d rows after suspected block.",
            display_name, len(rows),
        )

    log.info("[%s] App Store total: %d reviews since %s", display_name, len(rows), since.date())
    return rows, False


def _attempt_fetch(
    app_id: str,
    display_name: str,
    since: datetime,
    country: str,
    session: requests.Session,
) -> Tuple[List[Dict[str, Any]], bool]:
    """One full pagination attempt for a single client.
    Returns (rows, suspected_block). suspected_block=True only when page 1 returns
    HTTP 200 with an empty entry array, which is Apple's CDN throttle response."""
    results: List[Dict] = []

    for page in range(1, _MAX_PAGES + 1):
        url = _BASE_URL.format(country=country, page=page, app_id=app_id)
        try:
            resp = session.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            log.warning("[%s] App Store page %d error: %s", display_name, page, exc)
            break

        entries = data.get("feed", {}).get("entry", [])
        if not entries:
            if page == 1:
                body_len = len(resp.content)
                log.error(
                    "[%s] App Store SUSPECTED BLOCK: page 1 returned empty entry array "
                    "(body=%d bytes)",
                    display_name, body_len,
                )
                return results, True
            # page 2+ empty means end of reviews; normal exit
            break

        cutoff_reached = False
        page_count = 0
        for entry in entries:
            # The first entry in the feed is sometimes app metadata, not a review.
            # Real review entries have im:rating; skip entries without it.
            rating_node = entry.get("im:rating")
            if not rating_node:
                continue

            review_dt = _parse_date(entry.get("updated", {}).get("label", ""))
            if review_dt and review_dt < since:
                cutoff_reached = True
                break

            row = _normalise(entry, display_name, app_id)
            if row:
                results.append(row)
                page_count += 1

        log.info(
            "[%s] App Store page %d: %d reviews (total so far: %d)",
            display_name, page, page_count, len(results),
        )

        if cutoff_reached:
            log.info("[%s] App Store: reached date cutoff at page %d", display_name, page)
            break

        if page < _MAX_PAGES:
            time.sleep(_SLEEP_BETWEEN_PAGES)

    return results, False


def _parse_date(label: str) -> Optional[datetime]:
    if not label:
        return None
    try:
        # Apple uses ISO 8601 with timezone offset, e.g. 2024-01-15T10:30:00-07:00
        dt = datetime.fromisoformat(label)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _normalise(entry: Dict[str, Any], client_name: str, app_id: str) -> Optional[Dict[str, Any]]:
    title = entry.get("title", {}).get("label", "").strip()
    body = entry.get("content", {}).get("label", "").strip()
    if not body:
        return None

    raw_text = f"{title}: {body}" if title else body

    rating_label = entry.get("im:rating", {}).get("label", "")
    try:
        rating = int(rating_label)
    except (ValueError, TypeError):
        rating = None

    review_id = entry.get("id", {}).get("label", "")
    post_url = f"https://apps.apple.com/eg/app/id{app_id}?review={review_id}" if review_id else f"https://apps.apple.com/eg/app/id{app_id}"

    author = entry.get("author", {}).get("name", {}).get("label", "")
    date_label = entry.get("updated", {}).get("label", "")
    post_date = _parse_date(date_label)

    return {
        "client_name": client_name,
        "post_url": post_url,
        "source": "appstore",
        "post_date": post_date.isoformat() if post_date else "",
        "author": author,
        "raw_text": raw_text,
        "rating": rating,
        "engagement": "",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "language": detect_language(raw_text),
        "sentiment": "",
        "feedback_type": "",
        "product_area": "",
        "severity": "",
        "agreement_signal": "",
        "claude_summary": "",
    }
