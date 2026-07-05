"""
Web scraper: DuckDuckGo keyword search + Trustpilot public page scraping.

DDG: free, no auth, max 10 results per query. Runs 3-4 queries per client
in Arabic and English. Reddit URLs surface here naturally (per 2026-06-14
decision to drop direct Reddit scraping). Tier B: DDG may rate-limit.

Trustpilot: public business pages only, requests + BeautifulSoup, no auth.
Only Amazon has a confirmed Trustpilot page (amazon.eg) as of 2026-06-14.
Tier B: Trustpilot layout changes break the parser without warning.

post_date for DDG results is blank when DDG metadata carries no date.
This interacts with housekeeping age-based pruning. Known limitation;
see 2026-06-14 decisions log entry.
"""
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

from enrichment import detect_language

log = logging.getLogger(__name__)

# Trustpilot is disabled in Phase 7. AWS WAF blocks plain Python requests at the
# TLS-fingerprint level. cloudscraper or curl_cffi may bypass it in a future phase.
# Only Amazon has a Trustpilot page (~85 reviews), so ROI vs Play Store signal is low.
# The web_trustpilot source value is preserved in code so re-enabling requires no restructuring.
_TRUSTPILOT_ENABLED = False
log.debug("Trustpilot scraping disabled in Phase 7 (WAF-blocked); see backlog in HANDOFF.md")

# DDG is disabled in Phase 9. DuckDuckGo returns search-result snippets, not user
# reviews. All 73 web_ddg rows written in Phase 7 were classified as off_topic or
# false by Gemini; they have been moved to the Quarantine tab. Re-enabling requires
# only flipping _DDG_ENABLED = True; no structural changes are needed.
_DDG_ENABLED = False
log.debug("DDG scraping disabled in Phase 9 (search snippets, not reviews); see backlog in HANDOFF.md")

_SLEEP_BETWEEN_QUERIES = 1.5   # seconds between DDG calls to avoid rate limits
_SLEEP_BETWEEN_CLIENTS = 2.0
_DDG_MAX_RESULTS = 10
_TRUSTPILOT_PAGES = 2          # fetch page 1 and page 2 only
_REQUEST_TIMEOUT = 20
_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

# Per-client DDG query strings. Queries are contextual hints, not exact-match filters.
# Each client has 3-4 English and 3-4 Arabic queries.
# Arabic uses Egyptian dialect phrasings that non-technical users would actually write.
_CLIENT_QUERIES: Dict[str, Dict[str, List[str]]] = {
    "amazon": {
        "en": [
            '"Amazon Egypt" identity verification',
            '"Amazon Egypt" seller verification return',
            "Amazon Egypt rejected my ID",
            "Amazon Egypt asking for ID card",
        ],
        "ar": [
            "أمازون مصر التحقق من الهوية",
            "أمازون مصر تحقق البائع",
            "أمازون مصر رفض هويتي",
            "أمازون مصر يطلب بطاقة الهوية",
        ],
    },
    "thndr": {
        "en": [
            "Thndr Egypt account verification problem",
            "Thndr identity verification face scan",
            "Thndr rejected",
            "Thndr account not approved",
        ],
        "ar": [
            "ثاندر تحقق الهوية مشكلة",
            "ثاندر فتح حساب استثمار",
            "ثاندر رفض التسجيل",
            "ثاندر حساب لم يتم الموافقة عليه",
        ],
    },
    "klivvr": {
        "en": [
            "Klivvr Egypt verification problem",
            "Klivvr wallet NID identity",
            "Klivvr cannot register",
            "Klivvr rejected onboarding",
        ],
        "ar": [
            "كليفر تحقق هوية مشكلة",
            "كليفر محفظة تسجيل",
            "كليفر لا يمكن التسجيل",
            "كليفر رفض التسجيل",
        ],
    },
    "rabbit": {
        "en": [
            '"Rabbit Mobility" Egypt verification problem',
            "Rabbit scooter onboarding face identity",
            "Rabbit Mobility cannot sign up",
            "Rabbit scooter app reject",
        ],
        "ar": [
            "رابيت موبيليتي تحقق هوية",
            "رابيت سكوتر تسجيل مشكلة",
            "رابيت موبيليتي لا يمكن التسجيل",
            "تطبيق رابيت رفض التسجيل",
        ],
    },
    "adib": {
        "en": [
            '"ADIB Egypt" account opening verification problem',
            '"ADIB Egypt" identity verification face scan',
            "ADIB Egypt registration problem",
            "ADIB Egypt app crash",
        ],
        "ar": [
            "أديب مصر فتح حساب مشكلة",
            "بنك أبو ظبي الإسلامي مصر تحقق هوية",
            "أديب مصر مشكلة في التسجيل",
            "تطبيق أديب مصر توقف",
        ],
    },
    "midbank": {
        "en": [
            "Mogo Egypt verification problem",
            "Mogo Midbank Egypt identity verification",
            "Mogo cannot register Egypt",
        ],
        "ar": [
            "موجو مصر تحقق هوية مشكلة",
            "تطبيق موجو مصر تسجيل",
            "موجو لا يمكن التسجيل مصر",
        ],
    },
    "raya": {
        "en": [
            '"Raya Elite" app verification problem',
            '"Raya Elite" identity verification Egypt',
            "Raya Elite rejected",
            "Raya Elite app cannot register",
        ],
        "ar": [
            "راية إليت تحقق هوية مشكلة",
            "تطبيق راية إليت تسجيل",
            "راية إليت رفض التسجيل",
            "تطبيق راية إليت لا يمكن التسجيل",
        ],
    },
    "khazna": {
        "en": [
            "Khazna Egypt verification problem",
            "Khazna app identity verification",
            "Khazna rejected",
            "Khazna cannot register",
        ],
        "ar": [
            "خزنة تحقق هوية مشكلة",
            "تطبيق خزنة تسجيل مصر",
            "خزنة رفض التسجيل",
            "خزنة لا يمكن التسجيل",
        ],
    },
}

# Trustpilot slugs. None means the client has no Trustpilot page.
_TRUSTPILOT_SLUGS: Dict[str, Optional[str]] = {
    "amazon": "amazon.eg",
    "thndr": None,
    "klivvr": None,
    "rabbit": None,
    "adib": None,
    "midbank": None,
    "raya": None,
    "khazna": None,
}


def fetch(
    client_key: str,
    display_name: str,
    since: datetime,
) -> List[Dict[str, Any]]:
    """Fetch DDG and Trustpilot results for a client. Returns normalized rows."""
    results: List[Dict] = []

    queries = _CLIENT_QUERIES.get(client_key, {})
    if not _DDG_ENABLED:
        log.info("[%s] DDG scraping disabled in Phase 9 -- skipping", display_name)
    elif not queries:
        log.warning("[%s] No DDG queries defined -- skipping web source", display_name)
    else:
        ddg_rows = _fetch_ddg(queries, display_name)
        results.extend(ddg_rows)

    slug = _TRUSTPILOT_SLUGS.get(client_key)
    if slug and _TRUSTPILOT_ENABLED:
        tp_rows = _fetch_trustpilot(slug, display_name, since)
        results.extend(tp_rows)
    elif slug and not _TRUSTPILOT_ENABLED:
        log.info("[%s] Trustpilot slug '%s' present but disabled in Phase 7 -- skipping", display_name, slug)

    log.info("[%s] Web total: %d rows", display_name, len(results))
    return results


def _fetch_ddg(queries: Dict[str, List[str]], display_name: str) -> List[Dict[str, Any]]:
    rows: List[Dict] = []
    seen_urls: set = set()
    all_queries = queries.get("en", []) + queries.get("ar", [])

    for i, query in enumerate(all_queries):
        if i > 0:
            time.sleep(_SLEEP_BETWEEN_QUERIES)
        try:
            ddgs = DDGS()
            raw = ddgs.text(query, max_results=_DDG_MAX_RESULTS)
            if not raw:
                log.debug("[%s] DDG query returned no results: %s", display_name, query[:60])
                continue
            for item in raw:
                url = item.get("href", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                row = _normalise_ddg(item, display_name)
                if row:
                    rows.append(row)
        except Exception as exc:
            log.error("[%s] DDG query error (%s): %s", display_name, query[:40], exc)

    log.info("[%s] DDG: %d unique results across %d queries", display_name, len(rows), len(all_queries))
    return rows


def _fetch_trustpilot(slug: str, display_name: str, since: datetime) -> List[Dict[str, Any]]:
    rows: List[Dict] = []
    base_url = f"https://www.trustpilot.com/review/{slug}"

    for page in range(1, _TRUSTPILOT_PAGES + 1):
        url = base_url if page == 1 else f"{base_url}?page={page}"
        try:
            resp = requests.get(url, headers=_REQUEST_HEADERS, timeout=_REQUEST_TIMEOUT)
            if resp.status_code != 200:
                log.error(
                    "[%s] Trustpilot page %d returned HTTP %d -- skipping",
                    display_name, page, resp.status_code,
                )
                break
            page_rows = _parse_trustpilot_page(resp.text, display_name, slug, since)
            rows.extend(page_rows)
            log.info("[%s] Trustpilot page %d: %d reviews", display_name, page, len(page_rows))
            if page_rows and page < _TRUSTPILOT_PAGES:
                time.sleep(1.5)
        except Exception as exc:
            log.error("[%s] Trustpilot fetch error (page %d): %s", display_name, page, exc)
            break

    return rows


def _parse_trustpilot_page(
    html: str, display_name: str, slug: str, since: datetime
) -> List[Dict[str, Any]]:
    rows: List[Dict] = []
    soup = BeautifulSoup(html, "html.parser")

    # Trustpilot wraps each review in a <article> with data-service-review-card-paper
    # Fallback: any <article> with a <time> element (layout changes break this).
    cards = soup.find_all("article", attrs={"data-service-review-card-paper": True})
    if not cards:
        # Broader fallback: article elements containing a time element
        cards = [a for a in soup.find_all("article") if a.find("time")]
    if not cards:
        log.warning(
            "[%s] Trustpilot: no review cards found at /review/%s -- layout may have changed",
            display_name, slug,
        )
        return rows

    for card in cards:
        row = _normalise_trustpilot_card(card, display_name, slug, since)
        if row:
            rows.append(row)

    return rows


def _normalise_trustpilot_card(
    card: Any, client_name: str, slug: str, since: datetime
) -> Optional[Dict[str, Any]]:
    # Date
    time_el = card.find("time")
    post_date = None
    if time_el and time_el.get("datetime"):
        try:
            dt = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            post_date = dt.astimezone(timezone.utc)
        except ValueError:
            pass

    if post_date and post_date < since:
        return None

    # Review text: look for a <p> with the review body
    body_el = (
        card.find("p", attrs={"data-service-review-text-typography": True})
        or card.find("p", class_=lambda c: c and "review" in c.lower())
        or card.find("p")
    )
    body = body_el.get_text(strip=True) if body_el else ""
    if not body:
        return None

    # Rating: <div data-service-review-rating> or <img alt="N stars">
    rating = None
    rating_el = card.find(attrs={"data-service-review-rating": True})
    if rating_el:
        try:
            rating = int(rating_el["data-service-review-rating"])
        except (ValueError, TypeError):
            pass
    if rating is None:
        img = card.find("img", alt=lambda a: a and "stars" in a.lower())
        if img:
            try:
                rating = int(img["alt"].split()[0])
            except (ValueError, TypeError, IndexError):
                pass

    # Author
    author_el = (
        card.find(attrs={"data-consumer-name-typography": True})
        or card.find(class_=lambda c: c and "consumer" in c.lower())
    )
    author = author_el.get_text(strip=True) if author_el else ""

    # URL: Trustpilot review permalinks use /reviews/{id} on the business page
    link_el = card.find("a", href=lambda h: h and "/reviews/" in h)
    if link_el:
        href = link_el["href"]
        post_url = href if href.startswith("http") else f"https://www.trustpilot.com{href}"
    else:
        post_url = f"https://www.trustpilot.com/review/{slug}"

    return {
        "client_name": client_name,
        "post_url": post_url,
        "source": "web_trustpilot",
        "post_date": post_date.isoformat() if post_date else "",
        "author": author,
        "raw_text": body,
        "rating": rating,
        "engagement": "",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "language": detect_language(body),
        "sentiment": "",
        "feedback_type": "",
        "product_area": "",
        "severity": "",
        "agreement_signal": "",
        "claude_summary": "",
    }


def _normalise_ddg(item: Dict[str, Any], client_name: str) -> Optional[Dict[str, Any]]:
    title = (item.get("title") or "").strip()
    snippet = (item.get("body") or "").strip()
    url = (item.get("href") or "").strip()

    if not url or not snippet:
        return None

    raw_text = f"{title}: {snippet}" if title else snippet
    domain = urlparse(url).netloc or url

    return {
        "client_name": client_name,
        "post_url": url,
        "source": "web_ddg",
        "post_date": "",   # DDG metadata rarely carries a reliable date
        "author": domain,
        "raw_text": raw_text,
        "rating": None,
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
