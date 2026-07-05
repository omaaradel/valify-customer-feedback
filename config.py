"""
Client registry. Add new clients here as they are onboarded in later phases.

valify_services lists the internal service names from the BigQuery transaction data.
These gate which keyword categories are active in keywords.py.

App IDs verified against live store listings on 2026-05-24 (see docs/scrapers.md).
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class ClientConfig:
    display_name: str           # Human-readable; used in Sheet rows and logs
    internal_key: str           # Valify BigQuery key
    use_case: str               # One-line flow description for enrichment context
    valify_services: List[str]  # Internal service names from transaction data
    first_tx: datetime          # Lower bound for historical sweep
    playstore_id: Optional[str]
    appstore_id: Optional[str]
    run_cadence: str            # "daily" or "alternate_days"

    @property
    def uses_liveness(self) -> bool:
        return "liveness_detection" in self.valify_services

    @property
    def uses_facematch(self) -> bool:
        return "facial_recognition" in self.valify_services


CLIENTS: Dict[str, ClientConfig] = {
    "amazon": ClientConfig(
        display_name="Amazon",
        internal_key="Amazon_live_bundle",
        use_case="Return an item or seller verification.",
        valify_services=["ocr"],
        first_tx=datetime(2026, 3, 24, tzinfo=timezone.utc),
        playstore_id="com.amazon.mShop.android.shopping",
        appstore_id="297606951",
        run_cadence="daily",
    ),
    # Play Store verified 2026-05-25:
    #   com.axismarkets.thndr  "Thndr: Invest your money"  Axis Markets B.V.  1,000,000+ installs
    "thndr": ClientConfig(
        display_name="Thndr",
        internal_key="thndr",
        use_case="Customer onboarding. Opening a trading account.",
        valify_services=["ocr", "facial_recognition", "ntra_validation", "cso_validation"],
        first_tx=datetime(2026, 1, 1, tzinfo=timezone.utc),
        playstore_id="com.axismarkets.thndr",
        appstore_id="1494883259",
        run_cadence="daily",
    ),
    # Play Store verified 2026-05-25:
    #   com.klivvr.consumer  "Klivvr"  Klivvr  1,000,000+ installs
    "klivvr": ClientConfig(
        display_name="Klivvr",
        internal_key="Klivvr",
        use_case="Customer onboarding. Opening a digital wallet.",
        valify_services=["ocr", "passport_ocr", "egy_nid_transliteration"],
        first_tx=datetime(2026, 1, 1, tzinfo=timezone.utc),
        playstore_id="com.klivvr.consumer",
        appstore_id="1586109111",
        run_cadence="daily",
    ),
    # Play Store verified 2026-05-26:
    #   com.Rabbit.rabbitApp  "Rabbit Mobility"  Rabbit Mobility B.V.  500,000+ installs
    "rabbit": ClientConfig(
        display_name="Rabbit",
        internal_key="Rabbit_live_bundle",
        use_case="Rider onboarding. First scooter or e-bike rental.",
        valify_services=["liveness_detection", "ocr", "facial_recognition"],
        first_tx=datetime(2026, 1, 1, tzinfo=timezone.utc),
        playstore_id="com.Rabbit.rabbitApp",
        appstore_id="1468767626",
        run_cadence="alternate_days",
    ),
    # Play Store verified 2026-05-25:
    #   com.ADIBEgyptPhone  "ADIB Egypt Mobile Banking"  Abu Dhabi Islamic Bank - Egypt  100,000+ installs
    #   Confirmed Egypt app (developer "Abu Dhabi Islamic Bank - Egypt", 100k installs).
    #   UAE app is com.adib.mobile ("Abu Dhabi Islamic Bank", 1M+ installs) -- NOT this one.
    "adib": ClientConfig(
        display_name="ADIB",
        internal_key="ADIB",
        use_case="Customer onboarding. Opening a bank account.",
        valify_services=["ocr", "liveness_detection", "facial_recognition", "sanction_shield"],
        first_tx=datetime(2026, 1, 1, tzinfo=timezone.utc),
        playstore_id="com.ADIBEgyptPhone",
        appstore_id="1263042975",
        run_cadence="alternate_days",
    ),
    # Play Store verified 2026-05-26:
    #   com.midbankcf.midtakseet  "Mogo"  Mogo-eg  500,000+ installs
    "midbank": ClientConfig(
        display_name="Midbank",
        internal_key="Midbank",
        use_case="Customer onboarding. Opening a bank account.",
        valify_services=["ocr", "cropper"],
        first_tx=datetime(2026, 1, 1, tzinfo=timezone.utc),
        playstore_id="com.midbankcf.midtakseet",
        appstore_id="1639315081",
        run_cadence="alternate_days",
    ),
    # Play Store verified 2026-05-26:
    #   com.rayaelite.B2E  "Raya Elite"  RAYA ELECTRONICS S.A.E  10,000+ installs
    #   B2E consumer finance for employees of corporate partners. KYC is onboarding step 3.
    #   com.rayawealth.rayawealth is an unrelated Indian wealth management firm. Do not use.
    # App Store ID confirmed 2026-06-14: apps.apple.com/eg/app/raya-elite/id6738885879
    "raya": ClientConfig(
        display_name="Raya",
        internal_key="Raya",
        use_case="Customer onboarding. Consumer financing for employees of corporate partners. Three-step flow ending in identity verification.",
        valify_services=["liveness_detection", "facial_recognition", "ocr"],
        first_tx=datetime(2026, 1, 1, tzinfo=timezone.utc),
        playstore_id="com.rayaelite.B2E",
        appstore_id="6738885879",
        run_cadence="alternate_days",
    ),
    # Play Store verified 2026-05-26:
    #   com.project.imperialcreation.khaznaproject  "Khazna"  Khazna Tech LLC  1,000,000+ installs
    "khazna": ClientConfig(
        display_name="Khazna",
        internal_key="Khazna",
        use_case="Customer onboarding. Digital financial app.",
        valify_services=["ocr"],
        first_tx=datetime(2026, 1, 1, tzinfo=timezone.utc),
        playstore_id="com.project.imperialcreation.khaznaproject",
        appstore_id="1614641229",
        run_cadence="alternate_days",
    ),
}
