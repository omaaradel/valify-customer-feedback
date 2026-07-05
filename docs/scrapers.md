# Scrapers — Platform-by-Platform Approach

## Decision Summary

| Platform | Library | Auth Required | Reliability | Why Chosen |
|----------|---------|---------------|-------------|------------|
| Google Play Store | `google-play-scraper` (pip) | None | High | Mature, free, returns rating + date + reply count |
| Apple App Store | `app-store-scraper` (pip) | None | High | RSS-based, free, stable |
| Reddit | `praw` (pip) | App credentials (free) | High | Official API, 60 req/min free tier |
| Facebook | `facebook-scraper` (pip) | None (public content) | Low | Best-effort only — expect frequent failures, accept gaps |
| Web fallback | `duckduckgo-search` (pip) | None | Medium | Catches app-review sites, blogs, forums |

**X/Twitter:** Out of scope for v1 — snscrape has been unreliable since early 2024, and twscrape requires account credentials we won't pay for.

---

## 1. Google Play Store — `google-play-scraper`

**Library:** `google-play-scraper==1.2.7`
**Install:** `pip install google-play-scraper`
**Auth:** None

### Approach
- Each client's Play Store app ID is stored in `config.py`.
- `reviews()` is called with `lang='ar'` first (Egyptian Arabic reviews), then `lang='en'`.
- `sort=Sort.NEWEST` ensures daily runs only paginate until we pass our cutoff date.
- Historical sweep: paginate with `count=200` per page until `at` (review date) < `first_tx`.
- Daily delta: paginate until `at` < `now - 48h`. The 48-hour overlap is intentional.

### Amazon app decision
Amazon Egypt users use the global Amazon Shopping app (`com.amazon.mShop.android.shopping`).
The "return an item" and seller-verification flows that Valify powers live inside this app.
The Seller Central app (`com.amazon.sellermobile.android`) is for inventory management and
is NOT where the Valify KYC/NID verification flow surfaces. Do not change this.

### Fields captured
| Source field | Maps to |
|-------------|---------|
| `content` | `raw_text` |
| `score` | `rating` |
| `at` | `post_date` |
| `userName` | `author` |
| constructed URL | `post_url` |
| `thumbsUpCount` | part of `engagement` |

### Verified app IDs (confirmed against live Play Store listings, 2026-05-24)

| Client | Play Store App ID | Store URL |
|--------|------------------|-----------|
| Amazon | `com.amazon.mShop.android.shopping` | https://play.google.com/store/apps/details?id=com.amazon.mShop.android.shopping |
| Thndr | `com.axismarkets.thndr` | https://play.google.com/store/apps/details?id=com.axismarkets.thndr |
| Klivvr | `com.klivvr.consumer` | https://play.google.com/store/apps/details?id=com.klivvr.consumer |
| Rabbit | `com.Rabbit.rabbitApp` | https://play.google.com/store/apps/details?id=com.Rabbit.rabbitApp |
| ADIB | `com.ADIBEgyptPhone` | https://play.google.com/store/apps/details?id=com.ADIBEgyptPhone |
| Midbank | `com.midbankcf.midtakseet` | https://play.google.com/store/apps/details?id=com.midbankcf.midtakseet |
| Raya | `com.rayawealth.rayawealth` | https://play.google.com/store/apps/details?id=com.rayawealth.rayawealth |
| Khazna | `com.project.imperialcreation.khaznaproject` | https://play.google.com/store/apps/details?id=com.project.imperialcreation.khaznaproject |

> **Rabbit note:** `Rabbit_live_bundle` is **Rabbit Mobility** (e-scooter/e-bike rental,
> developer Rabbit Mobility B.V.) — NOT Rabbit Mart (grocery delivery, `com.rabbit.mart`).
> These are unrelated companies that share a brand name. Rabbit Mobility operates in Egypt
> and verifies rider identities before allowing scooter/bike rentals.
>
> **Midbank note:** The Mogo app (`com.midbankcf.midtakseet`) is published by Mid Bank for
> Consumer Finance (Midbank's BNPL subsidiary). This is the app that uses Valify's OCR
> for NID scanning during onboarding. The parent bank's mobile banking app, if separate,
> does not appear to use Valify services per the transaction data.
>
> **Raya note:** Raya Wealth (`com.rayawealth.rayawealth`) is the Raya Group mutual-fund
> investment app that opens accounts requiring full KYC (NID + liveness + facematch).
> Other Raya apps (Shoraka, Elite) are separate products.

### Rate limits
No documented rate limit. Conservative: 1 request per 2 seconds between pagination calls.

---

## 2. Apple App Store — `app-store-scraper`

**Library:** `app-store-scraper==0.3.5`
**Install:** `pip install app-store-scraper`
**Auth:** None (uses iTunes RSS)

### Approach
- `AppStore(country='eg', app_name='...', app_id=...)` then `.review(how_many=200)`.
- Egyptian storefront (`country='eg'`) returns Arabic and English reviews.
- Same date-cutoff logic as Play Store.

### Verified App Store IDs (confirmed 2026-05-24)

| Client | App Store ID | Store URL |
|--------|-------------|-----------|
| Amazon | `297606951` | https://apps.apple.com/eg/app/amazon-shopping/id297606951 |
| Thndr | `1494883259` | https://apps.apple.com/us/app/thndr-invest-your-money/id1494883259 |
| Klivvr | `1586109111` | https://apps.apple.com/us/app/klivvr/id1586109111 |
| Rabbit | `1468767626` | https://apps.apple.com/us/app/rabbit-mobility/id1468767626 |
| ADIB | `1263042975` | https://apps.apple.com/us/app/adib-egypt-mobile-banking/id1263042975 |
| Midbank | `1639315081` | https://apps.apple.com/eg/app/mogo-eg/id1639315081 |
| Raya | `6737333850` | https://apps.apple.com/us/app/raya-wealth/id6737333850 |
| Khazna | `1614641229` | https://apps.apple.com/eg/app/khazna/id1614641229 |

---

## 3. Reddit — `praw`

**Library:** `praw==7.7.1`
**Install:** `pip install praw`
**Auth:** Read-only app credentials. Register at reddit.com/prefs/apps (free, 2 minutes).

### Approach
Search two ways per client:
1. `reddit.subreddit('all').search(keyword, sort='new', time_filter='day', limit=25)`
2. Targeted subreddits: `r/egypt`, `r/saudiarabia` (expats).

Historical sweep uses `time_filter='year'`.

### Fields captured
| PRAW field | Maps to |
|-----------|---------|
| `submission.url` | `post_url` |
| `submission.selftext` or `.title` | `raw_text` |
| `submission.created_utc` | `post_date` |
| `submission.author.name` | `author` |
| `submission.score` | part of `engagement` (upvotes) |
| `submission.num_comments` | part of `engagement` |
| top-5 comments | analyzed for `agreement_signal` by Claude |

### Rate limits
60 requests/minute on free tier. Throttle: 1 request/second.

---

## 4. Facebook — `facebook-scraper`

**Library:** `facebook-scraper==0.2.59`
**Install:** `pip install facebook-scraper`
**Auth:** None for public content.

**Status: Best-effort. Expect frequent failures. Do not invest engineering time keeping it
alive. Gaps are accepted.** Facebook aggressively blocks scrapers; any run may return 0
results or raise a blocked exception. The system handles this gracefully and continues.

### Approach
- Scrape public pages/groups (e.g., client brand pages, public Egyptian fintech communities).
- Use `get_posts(url, pages=3)` for daily runs; filter posts by active keywords.
- All exceptions are caught; the run continues without Facebook data.

### Fields captured
| field | Maps to |
|-------|---------|
| `post_url` | `post_url` |
| `post_text` | `raw_text` |
| `time` | `post_date` |
| `username` | `author` |
| `likes` + `comments` count | `engagement` |

---

## 5. Web Fallback — `duckduckgo-search`

**Library:** `duckduckgo-search==6.1.7`
**Install:** `pip install duckduckgo-search`
**Auth:** None

### Approach
One search per client per run using client name + top-3 keywords combined with OR.
Targets app-review aggregators, Egyptian tech blogs, forum threads.

### Fields captured
| DuckDuckGo field | Maps to |
|-----------------|---------|
| `href` | `post_url` |
| `body` | `raw_text` (snippet only) |
| `published` (if present) | `post_date` |

---

## Cron timezone note

Cron runs at 06:00 UTC. This is 08:00 Cairo in winter (UTC+2) and 09:00 Cairo during
DST (UTC+3). Do not attempt to track Cairo local time — accept the seasonal shift.

---

## Scraper Execution Order per Client

```
1. Play Store  (structured ratings, highest signal-to-noise)
2. App Store   (same)
3. Reddit      (long-form, agreement signal available)
4. Facebook    (best-effort, expect failures)
5. Web         (fallback, snippets only)
```

Scrapers run sequentially per client. Between clients, a 5-second sleep reduces the
chance of IP-based blocking.
