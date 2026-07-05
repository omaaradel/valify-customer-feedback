# Enrichment Examples — Edge Cases

## Example 1 — Implicit relevance (no keyword match)
**Input:** *"خلوني اصور البطاقة عشان ارجع منتج، شكلها مش طالعة كويس"* (Amazon)
**Output:**
```json
{
  "language": "ar",
  "sentiment": "negative",
  "feedback_type": "ux_friction",
  "product_area": "nid_verification",
  "severity": "medium",
  "agreement_signal": false,
  "claude_summary": "User struggles to capture a clear ID photo during the Amazon return flow."
}
```

## Example 2 — Positive signal
**Input:** *"The ID verification was super smooth, took 30 seconds"* (Thndr)
**Output:**
```json
{
  "language": "en",
  "sentiment": "positive",
  "feedback_type": "compliment",
  "product_area": "nid_verification",
  "severity": "none",
  "agreement_signal": false,
  "claude_summary": "User praises the fast and smooth ID verification at Thndr signup."
}
```

## Example 3 — Suggestion (feature request)
**Input:** *"ياريت تخلوا في اختيار رفع صورة البطاقة من الجاليري مش بس بالكاميرا"* (Klivvr)
**Output:**
```json
{
  "language": "ar",
  "sentiment": "neutral",
  "feedback_type": "feature_request",
  "product_area": "nid_verification",
  "severity": "none",
  "agreement_signal": false,
  "claude_summary": "User requests an option to upload ID from gallery instead of capturing via camera."
}
```

## Example 4 — Off-topic for the use case
**Input:** *"التطبيق بطيء جداً والتوصيل اتأخر يومين"* (Amazon)
**Output:**
```json
{
  "language": "ar",
  "sentiment": "negative",
  "feedback_type": "off_topic",
  "product_area": "other",
  "severity": "none",
  "agreement_signal": false,
  "claude_summary": "Complaint about app speed and delivery delay, unrelated to verification."
}
```

## Example 5 — Liveness (Rabbit Mobility)
**Input:** *"I tried to register to rent a scooter but the smile detection kept failing"* (Rabbit Mobility)
**Output:**
```json
{
  "language": "en",
  "sentiment": "negative",
  "feedback_type": "bug",
  "product_area": "liveness_detection",
  "severity": "critical",
  "agreement_signal": false,
  "claude_summary": "User cannot complete rider onboarding because the liveness smile-detection step fails."
}
```

## Example 6 — Mixed sentiment
**Input:** *"الـ KYC سريع بس الكاميرا بترفض الصور كتير"* (Thndr)
**Output:**
```json
{
  "language": "ar",
  "sentiment": "mixed",
  "feedback_type": "ux_friction",
  "product_area": "nid_verification",
  "severity": "medium",
  "agreement_signal": false,
  "claude_summary": "User finds Thndr's KYC fast overall but the camera step rejects ID photos repeatedly."
}
```
