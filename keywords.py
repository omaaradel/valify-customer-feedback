"""
Keyword sets per client, gated by the Valify services each client uses.

Play Store and App Store scrapers search by app ID — they don't use these keywords.
These keywords are for Reddit, Facebook, and web scrapers added in Phase 3.

In Phase 3, this module will also track per-keyword hit counts and rotate dead keywords
(zero hits across 3 consecutive runs) using state stored in the Admin tab.
"""
from typing import Dict, List

from config import ClientConfig


# ── Product keyword banks ────────────────────────────────────────────────────

_NID_EN: List[str] = [
    "national ID not working",
    "ID scan failed",
    "ID not recognized",
    "ID rejected",
    "cannot read ID",
    "identity verification failed",
    "KYC failed",
    "document scan error",
]

_NID_AR: List[str] = [
    "البطاقة مش شغالة",
    "التحقق مش شغال",
    "الهوية مش بتتقبل",
    "مسح الهوية فشل",
    "البطاقة مش بتتقرأ",
    "التحقق فشل",
    "رفض الهوية",
    "خطأ في البطاقة",
]

_LIVENESS_EN: List[str] = [
    "selfie video not working",
    "liveness check failed",
    "smile not detected",
    "blink not detected",
    "face not detected",
    "move head not working",
]

_LIVENESS_AR: List[str] = [
    "فيديو السيلفي مش شغال",
    "فحص الوجه فشل",
    "مش بيتعرف على الابتسامة",
    "مش بيتعرف على الرمشة",
    "الوجه مش متعرف عليه",
]

_FACEMATCH_EN: List[str] = [
    "selfie rejected",
    "face doesn't match",
    "photo not accepted",
    "face recognition failed",
]

_FACEMATCH_AR: List[str] = [
    "السيلفي اترفض",
    "الوجه مش بيتطابق",
    "الصورة مش بتتقبل",
    "التعرف على الوجه فشل",
]


# ── Per-client brand prefix keywords ────────────────────────────────────────

_BRAND: Dict[str, Dict[str, List[str]]] = {
    "Amazon": {
        "en": [
            "amazon egypt verification",
            "amazon identity egypt",
            "amazon seller verify egypt",
            "amazon national ID egypt",
            "amazon account verification egypt",
            "amazon.eg signup",
            "amazon egypt ID rejected",
            "amazon egypt can't verify",
        ],
        "ar": [
            "أمازون مصر التحقق",
            "أمازون البطاقة الوطنية",
            "أمازون الهوية مش بتتقبل",
            "أمازون مصر تسجيل",
            "أمازون مصر مش شغال",
            "أمازون مصر هوية",
            "أمازون مصر تحقق خطأ",
            "amazon.eg تحقق",
        ],
    },
    "Thndr": {
        "en": [
            # onboarding friction
            "thndr account not opening", "thndr signup problem", "thndr registration failed",
            "thndr KYC issue", "thndr KYC failed", "thndr verification failed",
            "thndr identity failed", "thndr ID not working", "thndr ID rejected",
            "thndr selfie rejected", "thndr face not recognized", "thndr selfie failed",
            "thndr phone verification", "thndr number not verified", "thndr OTP not working",
            # positive onboarding signals
            "thndr account opened successfully", "thndr verification easy",
            "thndr KYC smooth", "thndr signup fast",
            # general KYC context
            "thndr invest account", "open trading account thndr",
        ],
        "ar": [
            # onboarding friction
            "ثاندر تسجيل مشكلة", "فتح حساب ثاندر صعب", "ثاندر ما بيفتحش حساب",
            "ثاندر الهوية مش بتتقبل", "ثاندر البطاقة مش بتتقرأ", "ثاندر رفض الهوية",
            "ثاندر السيلفي اترفض", "ثاندر التحقق مش شغال", "ثاندر خطأ في التسجيل",
            "ثاندر رقم الهاتف مش بيتأكد", "ثاندر الكود مش بييجي", "ثاندر OTP مشكلة",
            # positive onboarding signals
            "ثاندر تسجيل سهل", "فتح حساب ثاندر بسرعة", "ثاندر التحقق مش لقيت مشكلة",
        ],
    },
    "Klivvr": {
        "en": [
            # onboarding friction
            "klivvr account not opening", "klivvr signup problem", "klivvr registration failed",
            "klivvr wallet not activated", "klivvr verification failed",
            "klivvr national ID not working", "klivvr ID rejected", "klivvr ID not recognized",
            "klivvr passport not working", "klivvr passport rejected", "klivvr identity failed",
            "klivvr KYC failed", "klivvr document upload failed",
            # positive onboarding signals
            "klivvr account opened", "klivvr verification easy", "klivvr signup fast",
            "klivvr wallet activated", "klivvr KYC smooth",
            # general context
            "open klivvr wallet", "klivvr digital wallet signup",
        ],
        "ar": [
            # onboarding friction
            "كليفر تسجيل مشكلة", "فتح محفظة كليفر صعب", "كليفر الحساب ما بيفتحش",
            "كليفر الهوية مش بتتقبل", "كليفر البطاقة مش شغالة", "كليفر رفض البطاقة",
            "كليفر الجواز مش بيتقبل", "كليفر رفض الجواز",
            "كليفر محفظة مشكلة", "كليفر التحقق مش شغال",
            # positive onboarding signals
            "كليفر تسجيل سهل", "فتح محفظة كليفر بسرعة", "كليفر التحقق تمام",
        ],
    },
    # Rabbit Mobility (e-scooter and e-bike rental). NOT Rabbit Mart (grocery delivery).
    "Rabbit": {
        "en": [
            # onboarding friction
            "rabbit mobility verification", "rabbit scooter signup problem",
            "rabbit identity failed", "rabbit selfie rejected",
            "rabbit liveness not working", "rabbit ID not recognized",
            "rabbit face detection failed", "rabbit rider KYC",
            "rabbit e-scooter verification", "rabbit bike rental signup",
            "rabbit account not opening", "rabbit registration failed",
            "rabbit license verification", "rabbit ID upload failed",
            # rider context
            "rabbit first ride signup", "sign up to rent rabbit",
            "rabbit scooter registration", "rabbit rider onboarding",
            "rabbit first rental problem",
            # positive signals
            "rabbit signup easy", "rabbit verification smooth",
        ],
        "ar": [
            "رابت تسجيل مشكلة", "رابت الهوية مش بتتقبل",
            "رابت السيلفي مش شغال", "رابت سكوتر تحقق",
            "تسجيل سواق رابت", "رابت أول ركوب مشكلة",
            "رابت رخصة القيادة مش بتتقبل",
            "رابت التحقق مش شغال", "رابت فتح حساب صعب",
        ],
    },
    "ADIB": {
        "en": [
            # onboarding friction
            "ADIB account not opening", "ADIB account opening problem", "ADIB registration failed",
            "ADIB digital onboarding issue", "ADIB KYC failed", "ADIB verification failed",
            "ADIB identity not accepted", "ADIB ID rejected", "ADIB ID not working",
            "ADIB selfie rejected", "ADIB selfie failed", "ADIB liveness not working",
            "ADIB liveness check failed", "ADIB face not recognized", "ADIB face match failed",
            "ADIB sanctions screening", "ADIB application rejected",
            # positive onboarding signals
            "ADIB account opened online", "ADIB verification easy", "ADIB digital banking smooth",
            "ADIB onboarding fast", "ADIB KYC smooth",
            # general context
            "open ADIB account online", "ADIB Egypt mobile banking signup",
        ],
        "ar": [
            # onboarding friction
            "أديب فتح حساب مشكلة", "أديب الحساب ما بيفتحش", "أديب تسجيل خطأ",
            "أديب التحقق مش شغال", "ADIB الهوية مش بتتقبل", "أديب رفض الهوية",
            "أديب البطاقة مش بتتقرأ", "أديب السيلفي اترفض", "أديب الوجه مش بيتعرف عليه",
            "أديب فيديو الحياة مش شغال", "أديب الكاميرا مش شغالة",
            "أديب الطلب اترفض", "ADIB مصر فتح حساب",
            # positive onboarding signals
            "أديب فتح حساب اونلاين سهل", "أديب التسجيل كان سريع", "أديب التحقق تمام",
        ],
    },
    "Midbank": {
        "en": [
            "midbank verification", "midbank account opening", "midbank national ID",
            "midbank identity failed", "mogo egypt verification", "mogo ID not working",
        ],
        "ar": [
            "ميدبنك فتح حساب مشكلة", "ميدبنك الهوية مش بتتقبل", "ميدبنك التحقق خطأ",
            "موجو مصر التحقق", "موجو هوية مشكلة",
        ],
    },
    # Raya Elite: B2E consumer finance for employees of corporate partners.
    # KYC is step 3 of onboarding (NID scan, liveness, facematch).
    "Raya": {
        "en": [
            # onboarding friction
            "raya elite account not opening", "raya elite registration failed",
            "raya elite verification failed", "raya elite identity failed",
            "raya elite ID not working", "raya elite ID rejected",
            "raya elite selfie rejected", "raya elite liveness not working",
            "raya elite face not recognized", "raya elite KYC failed",
            "raya elite document upload failed",
            # positive onboarding signals
            "raya elite account opened", "raya elite verification easy",
            "raya elite KYC smooth",
            # general context
            "raya elite signup", "raya elite employee finance",
        ],
        "ar": [
            # onboarding friction
            "رايا إليت تسجيل مشكلة", "رايا إليت الهوية مش بتتقبل",
            "رايا إليت التحقق مش شغال", "رايا إليت السيلفي اترفض",
            "رايا إليت الوجه مش بيتعرف عليه", "رايا إليت فتح حساب صعب",
            "رايا إليت رفض الهوية", "رايا إليت خطأ في التسجيل",
            # positive onboarding signals
            "رايا إليت تسجيل سهل", "رايا إليت التحقق تمام",
            # general context
            "رايا إليت تقسيط", "رايا إليت موظف",
        ],
    },
    "Khazna": {
        "en": [
            "khazna verification", "khazna signup problem", "khazna national ID",
            "khazna identity failed", "khazna account not opening",
        ],
        "ar": [
            "خزنة فتح حساب مشكلة", "خزنة الهوية مش بتتقبل", "خزنة التحقق خطأ",
            "فتح حساب خزنة صعب",
        ],
    },
}


def get_keywords(client: ClientConfig) -> Dict[str, List[str]]:
    """Return active EN + AR keyword lists for a client, gated by services used."""
    brand = _BRAND.get(client.display_name, {"en": [], "ar": []})
    en_kws = list(brand["en"]) + list(_NID_EN)
    ar_kws = list(brand["ar"]) + list(_NID_AR)

    if client.uses_liveness:
        en_kws.extend(_LIVENESS_EN)
        ar_kws.extend(_LIVENESS_AR)

    if client.uses_facematch:
        en_kws.extend(_FACEMATCH_EN)
        ar_kws.extend(_FACEMATCH_AR)

    return {"en": en_kws, "ar": ar_kws}
