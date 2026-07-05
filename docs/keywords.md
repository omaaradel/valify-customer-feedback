# Keywords — Per-Client Strategy

## Design Principles

1. **Services-gated keywords.** Keywords tied to a Valify product (Liveness Detection,
   Facematch) are only active for clients that actually use that product. A client without
   `liveness_detection` will never search for liveness-friction terms.

2. **Layered vocabulary:** Brand keyword + product friction term. Both parts must appear in
   the same post (via AND logic), or the brand keyword alone can surface high-signal posts
   for enrichment to filter.

3. **Egyptian dialect Arabic (عامية مصرية)** is the primary Arabic register for Play Store
   and Facebook. Formal Arabic (فصحى) is used for web fallback searches.

4. **Auto-rotation.** If a keyword returns 0 hits across 3 consecutive runs it is marked
   `dead` in the Admin tab and replaced with the next variant from the rotation pool below.

5. **Starting broad.** Each client begins with ~8 EN + ~8 AR keywords. Over time, the
   rotation mechanism narrows them toward what actually has signal.

---

## Keyword Categories (applied across all clients)

### General KYC / Onboarding Friction
| English | Arabic (Egyptian dialect) | Arabic (Formal) |
|---------|--------------------------|-----------------|
| verification failed | التحقق مش شغال | فشل التحقق |
| identity not accepted | الهوية مش بتتقبل | الهوية غير مقبولة |
| ID rejected | الـ ID اترفض | رُفض الهوية |
| can't complete signup | مش قادر أكمل التسجيل | تعذر إكمال التسجيل |
| account not opening | الحساب مش بيفتح | لا يمكن فتح الحساب |
| stuck on verification | واقف على التحقق | توقف عند التحقق |
| verification error | خطأ في التحقق | خطأ التحقق |
| KYC | كيواي سي | التحقق من الهوية |

### NID Verification (OCR) — used by ALL 8 clients
| English | Arabic (Egyptian dialect) | Arabic (Formal) |
|---------|--------------------------|-----------------|
| national ID not working | البطاقة مش شغالة | البطاقة الوطنية لا تعمل |
| ID photo blurry | صورة الـ ID ضبابية | صورة الهوية غير واضحة |
| ID scan failed | مسح الـ ID فشل | فشل مسح الهوية |
| can't read ID | مش بيقرأ البطاقة | لا يستطيع قراءة البطاقة |
| ID not recognized | مش بيتعرف على البطاقة | الهوية غير معروفة |
| upload ID | رفع الهوية | تحميل الهوية |

### Liveness Detection — only for Rabbit, ADIB, Raya
| English | Arabic (Egyptian dialect) | Arabic (Formal) |
|---------|--------------------------|-----------------|
| selfie video not working | فيديو السيلفي مش شغال | فيديو السيلفي لا يعمل |
| liveness check failed | فحص الوجه فشل | فشل فحص الحيوية |
| smile not detected | مش بيتعرف على الابتسامة | لم يتعرف على الابتسامة |
| blink not detected | مش بيتعرف على الرمشة | عدم اكتشاف الرمش |
| move head | حرك رأسك | تحريك الرأس |
| follow the instructions | اتبع التعليمات | اتبع التعليمات |
| face not detected | الوجه مش متعرف عليه | الوجه غير مكتشف |

### Facematch — only for Thndr, Rabbit, ADIB, Raya
| English | Arabic (Egyptian dialect) | Arabic (Formal) |
|---------|--------------------------|-----------------|
| selfie rejected | السيلفي اترفض | السيلفي مرفوض |
| face doesn't match | الوجه مش بيتطابق | الوجه لا يتطابق |
| photo not accepted | الصورة مش بتتقبل | الصورة غير مقبولة |
| face recognition failed | التعرف على الوجه فشل | فشل التعرف على الوجه |
| selfie | سيلفي | صورة شخصية |

---

## Per-Client Keyword Sets

### 1. Amazon (`Amazon_live_bundle`)
**Active Valify products:** NID OCR only
**First transaction:** 2026-03-24

**Starting EN keywords (8):**
```
"amazon egypt" verification
"amazon egypt" identity
"amazon seller" verify egypt
amazon "national ID" egypt
amazon "account verification" egypt
"amazon.eg" signup
amazon egypt "ID rejected"
amazon egypt "can't verify"
```

**Starting AR keywords (8):**
```
أمازون مصر التحقق
أمازون "البطاقة الوطنية"
أمازون "الهوية مش بتتقبل"
"أمازون.كوم" مصر تسجيل
أمازون مصر "مش شغال"
أمازون مصر هوية
أمازون مصر تحقق خطأ
"amazon.eg" تحقق
```

**Rotation pool (swapped in when a keyword dies):**
```
EN: "amazon egypt" KYC, amazon egypt "document", "amazon.eg" verify,
    amazon egypt "photo", amazon seller egypt verification
AR: أمازون إيجيبت هوية، أمازون الكاشير هوية، أمازون البائع تحقق
```

---

### 2. Thndr (`thndr`)
**Active Valify products:** NID OCR + Facematch + NTRA/CSO Phone Validation
**First transaction:** 2026-01-01

**Starting EN keywords (8):**
```
thndr verification
thndr "identity" failed
thndr "account" open problem
thndr "selfie" rejected
thndr "ID" not working
thndr "KYC" issue
thndr "face" not recognized
thndr signup problem
```

**Starting AR keywords (8):**
```
ثاندر تسجيل مشكلة
ثاندر "الهوية" مش بتتقبل
ثاندر "السيلفي" اترفض
فتح حساب ثاندر صعب
ثاندر "التحقق" مش شغال
ثاندر "البطاقة" مش بتتقرأ
ثاندر خطأ تسجيل
"thndr" مشكلة هوية
```

**Rotation pool:**
```
EN: thndr "photo" rejected, thndr onboarding stuck, thndr "face match",
    thndr investment account problem
AR: ثاندر فيس ريكوجنيشن، ثاندر وجه مش بيتطابق، ثاندر حساب استثمار مشكلة
```

---

### 3. Klivvr (`Klivvr`)
**Active Valify products:** NID OCR + Passport OCR + NID Transliteration
**First transaction:** 2026-01-01

**Starting EN keywords (8):**
```
klivvr verification
klivvr "national ID"
klivvr wallet signup problem
klivvr "passport" not working
klivvr identity failed
klivvr "account" not opening
klivvr "ID scan" failed
klivvr KYC
```

**Starting AR keywords (8):**
```
كليفر تسجيل مشكلة
كليفر "الهوية" مش بتتقبل
كليفر محفظة مشكلة
كليفر "البطاقة" مش شغالة
فتح حساب كليفر صعب
كليفر التحقق خطأ
"klivvr" هوية
كليفر جواز سفر مشكلة
```

**Rotation pool:**
```
EN: klivvr "document" scan, klivvr onboarding, klivvr "ID" rejected,
    klivvr wallet opening stuck
AR: كليفر سكان هوية، كليفر بطاقة هوية، كليفر حساب مشكلة
```

---

### 4. Rabbit (`Rabbit_live_bundle`)
**App:** Rabbit Mobility (e-scooter / e-bike rental) — NOT Rabbit Mart (grocery delivery).
**Flow:** Rider onboarding — verifying identity before allowing scooter or e-bike rental.
**Active Valify products:** NID OCR + Liveness Detection + Facematch
**First transaction:** 2026-01-01
**Keyword weighting:** Customer base skews English-fluent (urban, tech-savvy riders).
Run 10 EN keywords and 5 AR keywords (inverse of most other clients).

**Starting EN keywords (10):**
```
rabbit mobility verification
rabbit scooter signup problem
rabbit "identity" failed
rabbit "selfie" rejected
rabbit "liveness" not working
rabbit "ID" not recognized
rabbit "face" detection failed
rabbit rider KYC
rabbit e-scooter verification
rabbit bike rental signup
```

**Starting AR keywords (5):**
```
رابت تسجيل مشكلة
رابت "الهوية" مش بتتقبل
رابت "السيلفي" مش شغال
رابت سكوتر تحقق
تسجيل سواق رابت
```

**Rotation pool:**
```
EN: rabbit egypt verify, rabbit "blink", rabbit "move head", rabbit "smile" detected,
    rabbit onboarding stuck, rabbit scooter egypt problem, rabbit app rider identity,
    "rabbit mobility" egypt signup
AR: رابت تأجير سكوتر مشكلة، رابت وجه مش بيتطابق، رابت ابتسم مش شغال،
    تأجير سكوتر هوية، رابت دراجة كهربائية
```

---

### 5. ADIB (`ADIB`)
**Active Valify products:** NID OCR + Liveness Detection + Facematch + Sanctions Check
**First transaction:** 2026-01-01

**Starting EN keywords (8):**
```
ADIB "account opening" problem
ADIB verification failed
ADIB "digital onboarding" issue
ADIB "selfie" rejected
ADIB "liveness" not working
ADIB "identity" not accepted
ADIB "ID scan" failed
ADIB KYC
```

**Starting AR keywords (8):**
```
أديب "فتح حساب" مشكلة
أديب "التحقق" مش شغال
ADIB "الهوية" مش بتتقبل
أديب "السيلفي" اترفض
أديب "الوجه" مش بيتعرف عليه
أديب رقمي تسجيل خطأ
"ADIB مصر" هوية مشكلة
أديب فيديو سيلفي مشكلة
```

**Rotation pool:**
```
EN: ADIB egypt "face match", ADIB "document", ADIB "blink", ADIB sanctions,
    "abu dhabi islamic bank" egypt verification
AR: أديب مصر تسجيل، ADIB بطاقة هوية، بنك أبوظبي الإسلامي التحقق
```

---

### 6. Midbank (`Midbank`)
**Active Valify products:** NID OCR only
**First transaction:** 2026-01-01

**Starting EN keywords (8):**
```
midbank verification
midbank "account opening"
midbank "national ID"
midbank identity failed
midbank "ID scan"
midbank signup
midbank KYC
midbank onboarding
```

**Starting AR keywords (8):**
```
ميدبنك "فتح حساب" مشكلة
ميدبنك "الهوية" مش بتتقبل
ميدبنك التحقق خطأ
ميدبنك "البطاقة" مش بتتقرأ
فتح حساب ميدبنك صعب
ميدبنك تسجيل مشكلة
"midbank" هوية مصر
ميدبنك هوية خطأ
```

**Rotation pool:**
```
EN: midbank "document", midbank "ID rejected", midbank egypt bank account
AR: ميدبنك بطاقة مشكلة، ميدبنك تسجيل عبر الانترنت، ميد بنك هوية
```

---

### 7. Raya (`Raya`)
**Active Valify products:** NID OCR + Liveness Detection + Facematch
**First transaction:** 2026-01-01

**Starting EN keywords (8):**
```
raya "account opening"
raya financial verification
raya "identity" failed
raya "selfie" rejected
raya "liveness" detection
raya KYC problem
raya "ID" not working
raya onboarding stuck
```

**Starting AR keywords (8):**
```
رايا "فتح حساب" مشكلة
رايا "التحقق" مش شغال
رايا "الهوية" مش بتتقبل
رايا "السيلفي" اترفض
رايا "الوجه" مش بيتعرف عليه
رايا تسجيل خطأ
"raya" تحقق مصر
رايا فيديو سيلفي مشكلة
```

**Rotation pool:**
```
EN: "raya finance" verification, raya egypt digital, raya "face match",
    raya "blink", raya document scan
AR: رايا بنك مشكلة، رايا ماليه تسجيل، رايا وجه مش بيتطابق
```

---

### 8. Khazna (`Khazna`)
**Active Valify products:** NID OCR only
**First transaction:** 2026-01-01

**Starting EN keywords (8):**
```
khazna verification
khazna signup problem
khazna "national ID"
khazna "identity" failed
khazna "ID scan"
khazna account not opening
khazna KYC
khazna onboarding
```

**Starting AR keywords (8):**
```
خزنة "فتح حساب" مشكلة
خزنة "الهوية" مش بتتقبل
خزنة التحقق خطأ
خزنة "البطاقة" مش بتتقرأ
فتح حساب خزنة صعب
خزنة تسجيل مشكلة
"khazna" هوية مصر
خزنة هوية خطأ
```

**Rotation pool:**
```
EN: khazna "digital wallet" verify, khazna "ID rejected", khazna egypt app
AR: خزنة بطاقة مشكلة، خزنة تطبيق مشكلة، خزنه هوية
```

---

## Auto-Rotation Logic

### Tracking
In `keywords.py`, every keyword carries a hit counter persisted in memory
(and backed to the Admin tab's `active_keywords_en`/`active_keywords_ar` columns as JSON).

```python
# Example structure in memory / Admin tab
{
  "thndr": {
    "en": {
      "thndr verification": {"hits": 12, "consecutive_zeros": 0},
      "thndr signup problem": {"hits": 0, "consecutive_zeros": 3},  # → dead
      ...
    }
  }
}
```

### Rotation trigger
When `consecutive_zeros >= 3` AND the rotation pool has a replacement:
1. Move the dead keyword to the `dead_keywords` column in the Admin tab (comma-separated).
2. Pull the first unused keyword from the rotation pool.
3. Log the swap: `"Swapped 'thndr signup problem' → 'thndr onboarding stuck' on 2026-05-25"`.

### Zero-hits definition
A keyword returns zero hits when it produces no new (non-deduplicated) results
across ALL scrapers in a single run. App Store + Play Store + Reddit + Facebook + Twitter + Web
must all return nothing for that keyword for it to count as a zero run.

### Rotation never removes a keyword that has had hits in the last 14 days.
This prevents rotating out a keyword that's seasonal or tied to a specific incident.
