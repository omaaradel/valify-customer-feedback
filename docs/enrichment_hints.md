# Per-Client Enrichment Hints

These are **signal hints**, not filters. Use to recognize relevant
feedback in natural language, even when no literal keyword matches.

## Amazon: Return an item or seller verification
**Relevant if the user mentions:**
- The ID capture step during a return flow (e.g., *"عشان ارجع منتج طلب يصور البطاقة"*)
- Identity verification when registering as a seller
- Camera/photo step in the returns or seller flow
- Document upload requested by Amazon

**NOT relevant if about:** delivery, products, prices, refunds, customer service, app crashes unrelated to ID step

## Thndr: Customer onboarding (trading account)
**Use case:** Customer onboarding. Opening a trading account.
**Valify products:** NID OCR, Facematch, Phone Validation (NTRA and CSO)

**Relevant if about:**
- Account opening flow: NID upload at signup, selfie or facematch step
- Phone number verification blocking account creation (NTRA or CSO)
- KYC step preventing access to trading features
- Registration rejected or stuck during onboarding

**NOT relevant if about:** trading activity, portfolio performance, stock prices,
dividend complaints, app speed or crashes unrelated to onboarding

## Klivvr: Customer onboarding (digital wallet)
**Use case:** Customer onboarding. Opening a digital wallet.
**Valify products:** NID OCR, Passport OCR, NID Transliteration

**Relevant if about:**
- Wallet account opening: NID or passport upload, identity step blocking wallet setup
- Document transliteration or name mismatch issues during onboarding
- Registration rejected or stuck before wallet is activated

**NOT relevant if about:** wallet transactions, top-up failures, send or receive money,
payment issues, app crashes unrelated to onboarding

## Rabbit Mobility: Rider onboarding (e-scooter or e-bike rental)
**Use case:** Rider onboarding. First scooter or e-bike rental.
**Valify products:** NID OCR, Liveness Detection, Facematch

**Relevant if about:**
- Rider signup before first ride: ID scan to unlock first scooter or bike
- Age verification from NID (confirming rider meets the minimum age requirement)
- Selfie or liveness step to confirm rider identity before riding
- License verification as part of rider onboarding
- Registration rejected or stuck before first ride is unlocked

**NOT relevant if about:** ride pricing, vehicle availability, charging,
parking, scooter hardware issues, app crashes unrelated to onboarding

## ADIB: Customer onboarding (bank account)
**Use case:** Customer onboarding. Opening a bank account.
**Valify products:** NID OCR, Liveness Detection, Facematch, Sanctions Screening

**Relevant if about:** digital onboarding from the app, NID upload step,
selfie or liveness check, sanctions screening rejection, application rejected during onboarding

**NOT relevant if about:** in-branch services, card issues, transfers,
existing account problems, internet banking after account is open

## Midbank: Customer onboarding (bank account via Mogo app)
**Use case:** Customer onboarding. Opening a bank account.
**Valify products:** NID OCR

**Relevant if about:**
- Account or BNPL credit line opening in the Mogo app
- NID scan or upload failing during onboarding
- Identity verification step blocking account activation

**NOT relevant if about:** loan repayment complaints, BNPL purchase issues after
account is open, installment schedules, existing account problems

## Raya: Customer onboarding (Raya Elite B2E consumer finance)
**Use case:** Customer onboarding. Consumer financing for employees of corporate
partners. Three-step flow ending in identity verification.
**Valify products:** NID OCR, Liveness Detection, Facematch

**Relevant if about:**
- Employee registering for a Raya Elite credit limit in the three-step flow
- Step 3 of onboarding: NID scan, liveness check, or facematch failing
- Identity verification blocking access to the installment credit line
- Account rejected or stuck during the onboarding flow

**NOT relevant if about:** installment purchase complaints after onboarding is
complete, product selection at Raya retail stores, Raya Shop, Raya Auto,
other Raya subsidiaries

## Khazna: Customer onboarding (digital financial app)
**Use case:** Customer onboarding. Digital financial app.
**Valify products:** NID OCR

**Relevant if about:**
- Account opening or registration in the Khazna earned-wage-access app
- NID scan or upload failing during signup
- Identity verification step blocking salary advance or wallet access

**NOT relevant if about:** salary advance amount or timing, wage withdrawal
failures after onboarding is complete, payment issues, existing account complaints

## Universal signal phrases (any client, any flow)
**Arabic (Egyptian dialect):** صور البطاقة، رفع الهوية، التقاط الصورة،
السيلفي، الوجه، التحقق، الكاميرا، فتح حساب، تسجيل، توثيق، اعمل أكونت،
ابعت صورة، الكاميرا مش شغالة، الصورة مش بتطلع

**Arabic (formal):** البطاقة الوطنية، التحقق من الهوية، فحص الوجه،
الصورة الشخصية

**English:** capture ID, upload ID, take a photo, selfie step, verify identity,
camera doesn't work, photo blurry, can't continue signup, KYC step

## Scope detection signals

The following are examples of how Egyptian users describe the identity verification
step. They do not mention Valify by name. Classification must be based on the action
described, not on the name mentioned. These examples cover Egyptian Arabic dialect,
Modern Standard Arabic, and English.

**Identity verification step detected (valify_scope = true):**

Egyptian Arabic dialect, ID capture:
- طلب منهم يصوروا البطاقة او جواز السفر
- البطاقة ما اتقبلتش
- الصورة مش واضحة
- ليه محتاجين بطاقتي
- ايه دخل جواز السفر ده
- مش هقبل يسكانوا هويتي

Egyptian Arabic dialect, selfie and liveness:
- طلب منهم يصوروا وشهم
- السيلفي ما اتقبلتش
- فضل يطلب مني اعيد صورة وشي
- قالهم ابص في الكاميرا
- ابتسم
- لا تتحرك وفضل يفشل
- الكاميرا مش شايلة وشي

Egyptian Arabic dialect, facematch and rejection:
- قالهم الوش مش متطابق مع البطاقة
- رفضوني على طول بعد ما صورت البطاقة
- بعد الكاميرا قالي مش مؤهل

Egyptian Arabic dialect, phone verification during onboarding:
- الكود ما جاش
- الرسالة ما وصلتش وانا بفتح الحساب

Modern Standard Arabic:
- طُلب من المستخدم تصوير بطاقة الهوية الوطنية ولم تُقبل الصورة

English:
- The app asked me to scan my ID and it kept failing
- I had to take a selfie 10 times and it never worked
- Camera opened, scanned my face, then error
- Why do they need my national ID just to return a product
- They forced me to upload my ID card to their system

**Not identity verification (valify_scope = false):**

English:
- My account is under review / waiting for approval
- I submitted everything and I am waiting
- They told me to try again after 30 days
- Customer service is not responding
- My account was rejected after I finished the steps
- I passed verification but my account is still blocked

Egyptian Arabic dialect:
- حسابي بيتراجع
- مستني موافقة
- قالي ارجع بعد 30 يوم

## Sentiment is independent of relevance
A positive review about the ID step is just as valuable as a complaint.
Examples:
- *"التحقق كان سريع جداً، مش كنت متوقع"* -> `positive`, `compliment`, `nid_verification`
- *"ياريت يكون في خيار اني ارفع صورة من المعرض"* -> `neutral`, `feature_request`, `nid_verification`
