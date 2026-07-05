"""
Batch classifier for Amazon Play Store reviews.
Applies taxonomy from docs/enrichment_taxonomy.md and hints from docs/enrichment_hints.md.
Amazon use case: Return-item / seller verification (Egypt) — NID OCR only.
"""

import json
import re
import sys

# ── Amazon-specific relevance signals ──────────────────────────────────────
# These indicate the review touches the ID/document capture step in the
# return or seller-registration flow. Zero literal overlap is still OK —
# we check for semantic proximity, not exact match.

AMAZON_RELEVANT_AR = [
    # ID card signals — exclude payment/gift card variants
    "بطاقة الهوية", "بطاقة شخصية", "بطاقة شخصيه",
    "هوية", "هويتي", "هويه", "بطاقتي الشخصية",
    "صور البطاقة", "تصوير البطاقة",
    "ارسال بطاقة الهوية", "إرسال بطاقة الهوية",
    "صورة الهوية", "صور الهوية",
    "التحقق من الهوية", "توثيق الهوية",
    "اثبات الهوية", "إثبات الهوية",
    "رفع صورة الهوية", "رفع الهوية",
    "لماذا تطلب هويتي", "ليش تطلب هويتي",
    "تصور بطاقتك", "تصوير بطاقتك",
    "خطر سرقة بيانات",
    "تسجيل بائع", "حساب بائع", "تسجيل كبائع",
    "kyc", "كي واي سي",
]

AMAZON_RELEVANT_EN = [
    # Government-issued ID signals
    "national id", "national id card", "id card", "identity card",
    "government id", "govt id", "photo id", "driver's license",
    "upload id", "id scan", "scan id", "scan my id", "photo of my id",
    "id verification", "identity verification", "verify identity",
    "id required", "id needed", "asking for id", "asking my id",
    "asking me to verify my id", "verify my identity",
    "capture id", "id capture",
    # Face/biometric signals (only if in return/account/seller context)
    "face scan", "face match", "facematch", "government id",
    "spyware", "literally spyware",
    # Seller
    "seller registration", "seller account", "seller verification",
    "register as seller",
    # Explicit return-flow ID
    "id for return", "return id", "return verification",
    # Age verification (Amazon uses this for regulated items — relevant)
    "age verification", "age verify",
    # Data privacy in ID context
    "data privacy", "data theft", "personal data",
    # KYC
    "kyc", "know your customer",
]

# Signals that, when matched by the above patterns, actually indicate
# payment cards / 2FA / delivery — not NID. Used to veto false positives.
AMAZON_VETO_AR = [
    "بطاقة هدية", "بطاقة الهدايا", "بطاقة ائتمان", "بطاقة الدفع",
    "كارت هدية", "كارت ائتمان",
]

AMAZON_VETO_EN = [
    "verification code", "otp", "one-time", "two-step", "two step",
    "2-step", "2fa", "authenticator",
    "sms code", "text message code", "phone number code",
    "payment verification", "card verification", "tap the card",
    "tap your card", "tap card", "physical card",
    "bank verification", "credit card",
]

# ── Hard off-topic signals — if ONLY these appear, it's clearly off-topic ─
OFFTRACK_AR = [
    "توصيل", "مندوب", "شحن", "تأخير", "تأخر", "سعر", "أسعار", "اسعار",
    "منتج", "سلعة", "سلعه", "بضاعة", "بضاعه", "طلبية", "طلبيه",
    "اوردر", "أوردر", "خدمة العملاء", "خدمه العملاء",
    "رخيص", "غالي", "دفع", "فيزا", "كارت", "محفظة",
    "كسر", "تالف", "منتهية الصلاحية", "صلاحية",
    "تسليم", "تتبع", "track",
]

OFFTRACK_EN = [
    "delivery", "shipping", "courier", "driver", "package",
    "tracking", "delayed", "refund credit", "customer support",
    "customer service", "price", "expensive", "cheap",
    "product quality", "item broken", "damaged",
    "not received", "order cancel",
]


def text_has_any(text: str, signals: list[str]) -> bool:
    t = text.lower()
    for s in signals:
        sl = s.lower()
        if sl in t:
            # Require word boundaries for short/ambiguous tokens
            # to prevent "id card" matching "prepaid card", etc.
            if re.search(r'\b' + re.escape(sl) + r'\b', t):
                return True
    return False


def is_relevant(raw: str) -> bool:
    """True if the review is about Amazon's return/seller ID-verification flow."""
    if not (text_has_any(raw, AMAZON_RELEVANT_AR) or text_has_any(raw, AMAZON_RELEVANT_EN)):
        return False
    # Veto: if the match is about payment cards or 2FA, not ID
    if text_has_any(raw, AMAZON_VETO_AR) or text_has_any(raw, AMAZON_VETO_EN):
        return False
    return True


def sentiment_from_rating(rating) -> str:
    r = int(rating)
    if r >= 4:
        return "positive"
    if r == 3:
        return "neutral"
    if r == 2:
        return "negative"
    return "negative"   # 1-star


def classify_sentiment(raw: str, rating) -> str:
    """Sentiment from text cues; rating as fallback."""
    t = raw.lower()
    # Strong positive cues
    pos_en = ["great", "excellent", "amazing", "awesome", "love", "perfect",
              "smooth", "easy", "fast", "quick", "helpful", "fantastic"]
    pos_ar = ["ممتاز", "رائع", "ممتازه", "جيد", "سهل", "سريع", "مريح",
              "تحفه", "حلو", "خدمة رائعة"]
    # Strong negative cues
    neg_en = ["fail", "error", "crash", "doesn't work", "not working",
              "rejected", "stuck", "broken", "terrible", "worst",
              "can't", "cannot", "unable", "blocked", "problem",
              "issue", "bad", "poor", "never", "refused"]
    neg_ar = ["سيئ", "سيئه", "سيئة", "خطأ", "مش شغال", "بيرفض",
              "مش بتطلع", "مش بيشتغل", "عطل", "مشكلة", "مش قادر",
              "مش عارف", "مش ممكن", "فشل", "للأسف", "للاسف",
              "سرقة", "نصب", "بلطجة"]
    has_pos = text_has_any(raw, pos_en + pos_ar)
    has_neg = text_has_any(raw, neg_en + neg_ar)
    if has_pos and has_neg:
        return "mixed"
    if has_pos:
        return "positive"
    if has_neg:
        return "negative"
    return sentiment_from_rating(rating)


def classify_feedback_type(raw: str, sentiment: str) -> str:
    t = raw.lower()
    bug_en = ["error", "crash", "not working", "doesn't work", "bug",
              "fail", "failed", "rejected", "stuck", "broken", "freeze",
              "keeps failing", "won't", "can't open", "loading forever"]
    bug_ar = ["خطأ", "مش شغال", "بيرفض", "بيعمل ايرور", "عطل",
              "مش بيكمل", "بيوقف", "توقف", "فشل"]
    ux_en = ["confusing", "hard to", "difficult", "unclear", "slow",
             "takes too long", "frustrating", "annoying", "complicated",
             "blurry", "dark", "can't read", "multiple attempts",
             "kept trying", "had to try", "waste of time",
             "asked me to", "required me to", "forced me to",
             "why do you need", "why asking", "privacy", "data theft"]
    ux_ar = ["صعب", "بطيء", "غير واضح", "مش واضح", "محتاج مرات كتير",
             "مش بتطلع", "الكاميرا مش", "ليه تطلب", "خطر", "سرقة بيانات",
             "ليش تطلب", "لماذا تطلب"]
    feat_en = ["option to upload", "upload from gallery", "wish", "would be nice",
               "please add", "should allow", "suggestion", "request"]
    feat_ar = ["ياريت", "يارت", "نتمنى", "ارجو", "أتمنى", "لو في خيار",
               "خيار رفع", "من المعرض", "من الجاليري"]
    comp_en = ["smooth", "easy", "fast", "quick", "great", "awesome", "perfect",
               "excellent", "good experience", "well done", "loved it", "works great"]
    comp_ar = ["ممتاز", "سهل", "سريع", "رائع", "تمام", "حلو", "ممتازه",
               "تجربة ممتازه", "شكراً", "شكرا"]

    if text_has_any(raw, feat_en + feat_ar):
        return "feature_request"
    if text_has_any(raw, bug_en + bug_ar):
        return "bug"
    if text_has_any(raw, ux_en + ux_ar):
        return "ux_friction"
    if text_has_any(raw, comp_en + comp_ar) and sentiment == "positive":
        return "compliment"
    # fallback: use sentiment
    if sentiment == "positive":
        return "compliment"
    if sentiment in ("negative", "mixed"):
        return "ux_friction"
    return "ux_friction"


def classify_severity(feedback_type: str, raw: str, rating) -> str:
    if feedback_type in ("off_topic", "compliment", "feature_request"):
        return "none"
    t = raw.lower()
    # Critical — fully blocked, gave up
    critical_en = ["could not complete", "couldn't complete", "gave up", "completely blocked",
                   "never able to", "impossible to", "no way to", "refused my id",
                   "always fails", "keeps failing every time", "stuck forever",
                   "data theft", "privacy violation",
                   "wont accept my id", "won't accept my id",
                   "can't access the account", "cannot access the account",
                   "locked out", "can't get a refund", "cannot get a refund",
                   "looping into an endless", "endless loop", "infinite loop",
                   "literally spyware", "spyware"]
    critical_ar = ["مش قادر يكمل", "مش عارف يكمل", "مستحيل", "مش ممكن خالص",
                   "رفض هويتي", "سرقة بيانات", "خطر سرقة", "لن أستخدم",
                   "ليه تطلب هويتي", "خطر سرقة بيانات"]
    # High — near-gave-up
    high_en = ["almost gave up", "nearly impossible", "many attempts", "multiple times failed",
               "rejected several times", "very frustrating", "extremely difficult",
               "angry", "unacceptable"]
    high_ar = ["مرات كتير", "أكثر من مرة", "مش بيقبل", "كتير جداً",
               "مزعج جداً", "صعب جداً", "غير مقبول"]
    # Medium — completed with frustration
    medium_en = ["a few attempts", "took a while", "had to retry", "confusing",
                 "not ideal", "annoying", "blurry camera", "dark photo",
                 "unclear", "hard to"]
    medium_ar = ["محتاج أكثر من مرة", "بطيء", "غير واضح", "مش بتطلع كويس"]

    if text_has_any(raw, critical_en + critical_ar):
        return "critical"
    # 1-star bugs are critical; 1-star ux_friction with strong objection is high
    if int(rating) == 1 and feedback_type == "bug":
        return "critical"
    if int(rating) == 1 and feedback_type == "ux_friction":
        return "high"
    if text_has_any(raw, high_en + high_ar) or int(rating) == 2:
        return "high"
    if text_has_any(raw, medium_en + medium_ar) or int(rating) == 3:
        return "medium"
    if int(rating) >= 4:
        return "low"
    return "medium"


def make_summary(item: dict, feedback_type: str, product_area: str, sentiment: str) -> str:
    """Generate a one-sentence English summary (max 200 chars)."""
    raw = item.get("raw_text", "")
    rating = int(item.get("rating", 3))
    lang = item.get("language", "en")

    if feedback_type == "off_topic":
        # Generic off-topic summary based on common themes
        t = raw.lower()
        if any(w in t for w in ["توصيل", "مندوب", "شحن", "delivery", "shipping", "courier"]):
            return "User complains about delivery or courier service, unrelated to ID verification."
        if any(w in t for w in ["سعر", "رخيص", "غالي", "price", "expensive", "cheap"]):
            return "User comments on pricing or product value, unrelated to verification."
        if any(w in t for w in ["خدمة العملاء", "customer service", "support"]):
            return "User complains about customer service, unrelated to ID verification."
        if any(w in t for w in ["منتج", "سلعة", "product", "item", "quality"]):
            return "Feedback about product quality or order issues, unrelated to verification."
        if sentiment == "positive" and rating >= 4:
            return "User gives a positive general rating with no KYC-related content."
        if sentiment == "negative":
            return "User leaves a negative review unrelated to identity verification."
        return "General app feedback unrelated to ID verification or the return flow."

    if feedback_type == "compliment":
        if product_area == "nid_verification":
            return "User praises the ID verification step in the return or seller flow."
        return "User gives a positive review of the verification experience."

    if feedback_type == "feature_request":
        t = raw.lower()
        if any(w in t for w in ["gallery", "معرض", "جاليري", "upload", "رفع"]):
            return "User requests option to upload ID photo from gallery instead of camera."
        if any(w in t for w in ["why", "privacy", "ليه", "لماذا", "بيانات"]):
            return "User questions why ID is required and raises privacy concerns."
        return "User suggests an improvement to the ID verification step in the return flow."

    if feedback_type == "bug":
        t = raw.lower()
        if any(w in t for w in ["loop", "looping", "endless", "infinite"]):
            return "Age/ID verification loops into an endless error, blocking the user from completing the purchase."
        if any(w in t for w in ["face scan", "government id", "spyware"]):
            return "App requires face scan or government ID to create/access account; user calls it spyware."
        if any(w in t for w in ["كاميرا", "camera", "photo", "صورة"]):
            return "ID photo capture fails or camera does not work during the return flow."
        if any(w in t for w in ["رفض", "reject", "rejected", "هوية", "هويتي"]):
            return "ID document is rejected, blocking account access or order completion."
        return "Technical failure in the ID capture step during the return or seller flow."

    if feedback_type == "ux_friction":
        t = raw.lower()
        if any(w in t for w in ["سرقة", "خطر", "privacy", "data theft", "بيانات", "تجسس"]):
            return "User objects to Amazon requiring full ID scan for returns, citing data theft risk."
        if any(w in t for w in ["wont accept", "won't accept", "can't access", "locked"]):
            return "ID verification rejects user's ID after account lock, preventing refund and account access."
        if any(w in t for w in ["نشاط غير معتاد", "unusual activity", "suspicious activity"]):
            return "Amazon cancels orders and demands ID photo due to 'unusual activity', user finds it unjustified."
        if any(w in t for w in ["بطاقة شخصية", "بطاقة شخصيه"]):
            return "App now requires a personal ID card; user frustrated as order was not delivered either."
        if any(w in t for w in ["لماذا", "ليه", "ليش", "why", "تجسس", "إرسال بطاقة الهوية"]):
            return "User questions why ID is required for returns and suspects data privacy violation."
        if any(w in t for w in ["بطيء", "slow", "takes long", "وقت"]):
            return "ID verification step in the return flow is slow or takes too long."
        return "User finds the ID verification step confusing or difficult in the return flow."

    return f"User feedback about Amazon's {product_area.replace('_', ' ')} step."


def classify(item: dict) -> dict:
    raw = item.get("raw_text", "")
    rating = item.get("rating", 3)
    lang = item.get("language", "en")
    source = item.get("source", "play_store")
    row_number = item["row_number"]

    # agreement_signal is always false for play_store/app_store
    agreement_signal = False

    if not is_relevant(raw):
        sentiment = classify_sentiment(raw, rating)
        summary = make_summary(item, "off_topic", "other", sentiment)
        return {
            "row_number": row_number,
            "sentiment": sentiment,
            "feedback_type": "off_topic",
            "product_area": "other",
            "severity": "none",
            "agreement_signal": agreement_signal,
            "claude_summary": summary[:200],
        }

    # Relevant item — classify carefully
    sentiment = classify_sentiment(raw, rating)
    feedback_type = classify_feedback_type(raw, sentiment)

    # Amazon only uses NID OCR — no liveness, no facematch
    product_area = "nid_verification"

    severity = classify_severity(feedback_type, raw, rating)
    summary = make_summary(item, feedback_type, product_area, sentiment)

    return {
        "row_number": row_number,
        "sentiment": sentiment,
        "feedback_type": feedback_type,
        "product_area": product_area,
        "severity": severity,
        "agreement_signal": agreement_signal,
        "claude_summary": summary[:200],
    }


def main():
    with open("pending.json", encoding="utf-8") as f:
        items = json.load(f)

    results = []
    for item in items:
        results.append(classify(item))

    with open("enriched.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Stats
    total = len(results)
    off_topic = sum(1 for r in results if r["feedback_type"] == "off_topic")
    relevant = total - off_topic

    print(f"Total classified: {total}")
    print(f"Off-topic: {off_topic}")
    print(f"Relevant: {relevant}")

    from collections import Counter
    relevant_items = [r for r in results if r["feedback_type"] != "off_topic"]
    sev = Counter(r["severity"] for r in relevant_items)
    sent = Counter(r["sentiment"] for r in relevant_items)
    ftype = Counter(r["feedback_type"] for r in relevant_items)

    print(f"\nSeverity (relevant): {dict(sev)}")
    print(f"Sentiment (relevant): {dict(sent)}")
    print(f"Feedback type (relevant): {dict(ftype)}")

    # Top 5 critical
    critical = [r for r in relevant_items if r["severity"] == "critical"]
    print(f"\nCritical items ({len(critical)} total):")
    for r in critical[:5]:
        print(f"  Row {r['row_number']}: {r['claude_summary']}")


if __name__ == "__main__":
    main()
