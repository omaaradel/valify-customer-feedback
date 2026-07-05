# Enrichment — Classification via Claude

## What this is
Reads unenriched rows in the Sheet's Feedback Log, classifies each by 
sentiment, type, product area, and severity, writes the result back.
Run manually via Claude Code (Teams plan, $0). Not via API.

## How to run
Open a fresh Claude Code session in the project folder. Paste the 
content of `enrich_prompt.md` as the first message. It handles:
1. `python scripts/export_pending.py` → `pending.json`
2. Reads `pending.json`, classifies each item in-session
3. Writes `enriched.json`
4. `python scripts/import_enriched.py` → Sheet
5. Reports counts: total enriched, off-topic, critical, high

## Output fields
Each row gets six fields written back:
`sentiment`, `feedback_type`, `product_area`, `severity`, 
`agreement_signal`, `claude_summary`.

Field taxonomy and examples are in `/docs/enrichment_taxonomy.md` — 
load that file when classifying.

## Per-client use case (CRITICAL — Claude reads this for context)
Each client has a different flow. Feedback meaning depends on which flow.

| Client | Use case | What "verification" means |
|---|---|---|
| Amazon | **Return an item / seller registration** | ID capture during the return or seller-signup flow |
| Thndr | **Customer onboarding** — opening a trading account | NID + selfie at signup |
| Klivvr | **Customer onboarding** — opening a digital wallet | NID + passport at signup |
| Rabbit Mobility | **Rider onboarding** — first scooter/e-bike rental | NID + selfie before first ride |
| ADIB | **Customer onboarding** — opening a bank account | NID + selfie + liveness at signup |
| Midbank | **Customer onboarding** — opening a bank account | NID at signup |
| Raya | **Customer onboarding** — financial services account | NID + selfie + liveness at signup |
| Khazna | **Customer onboarding** — digital financial app | NID at signup |

Full per-client signal hints, edge cases, and example phrases are in 
`/docs/enrichment_hints.md` — load only when relevant.

## Valify scope rule

`valify_scope` answers: did this user interact with the identity verification step?

**What Valify owns at the action level:**
- ID capture: user was asked to photograph or scan their national ID or passport.
- Selfie capture: user was asked to photograph their face.
- Liveness detection: user was asked to blink, smile, move, or hold still in front of
  the camera during onboarding.
- Face match: the system compared the selfie to the ID photo.
- Mobile verification: an SMS code was sent to verify the user's phone number during
  onboarding (not during login).
- Policy objection: the user objects to being required to provide their ID or face
  data at all, framing it as a privacy or data concern. This is still valify_scope
  true because it directly describes the capture step.

**What Valify does NOT own:**
- Account approval delays after the verification step completed.
- Manual review queues managed by the client.
- Credit, fraud, or AML decisions made by the client's risk engine.
- "Retry after X days" messages.
- Customer support interactions.
- Login OTP or session management.
- Funds, transfers, or any post-onboarding product feature.

Classification is based on the ACTION described, not on whether Valify is named.
Users never mention Valify by name. See `docs/enrichment_hints.md` for detection
signals in Egyptian Arabic dialect, Modern Standard Arabic, and English.

## Sentiment rule

Sentiment is classified after valify_scope. It applies to any review regardless of
valify_scope value. Positive means the user had a good experience with what they are
describing. Negative means they had a bad or frustrating experience. Neutral means
they are describing something without a clear tone. When a review contains both
positive and negative elements, classify by the dominant tone. If neither tone
clearly outweighs the other, use neutral.

## How keywords are used (contextual, not lexical)
The keyword sets in `keywords.py` are **NOT** filters. They are 
**signal hints** passed to Claude during classification so it knows 
what kind of language to recognize. A review that says 
*"خلوني اصور البطاقة عشان ارجع منتج"* contains zero literal keyword 
matches but is highly relevant — Claude should classify it as 
`nid_verification` for Amazon's return flow. Keywords are starting 
points, not boundaries.

## Sentiment must be neutral on direction
Capture positive, negative, neutral, and suggestion feedback equally. 
Do not bias toward complaints. A user saying "التحقق كان سهل وسريع" 
is signal too — it tells product what's working.

## Token modularity
This file stays under 500 lines. When Claude Code needs details, it 
loads one of:
- `/docs/enrichment_taxonomy.md` — full field definitions + examples
- `/docs/enrichment_hints.md` — per-client signal hints and edge cases
- `/docs/enrichment_examples.md` — input/output examples for tricky cases

Load only the file relevant to the current task.

## Error handling
- Malformed classification → retry once with a stricter constraint
- Persistent failure → write `enrichment_failed` to fields, severity 
  `none`. Pick up on next run.
- Items tagged `off_topic` stay in the Sheet but are excluded from the 
  daily digest.
