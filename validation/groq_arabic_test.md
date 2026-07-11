# Groq Arabic quality test

Sample size: 20 Arabic rows (23 on-topic Arabic rows available, 0 off-topic rows used to fill the sample).

Groq unreachable: Groq returned 0 results across all batches (HTTP 403 Forbidden on every batch, confirmed consistently across 4 separate attempts this session). Likely geo-blocked from this environment, consistent with the Groq geo-blocking note in docs/HANDOFF.md.

Result: deferred to the first GitHub Actions run. Groq's free tier is geo-blocked from Egyptian IPs, so this local run recorded Gemini results only. Groq is not yet confirmed or rejected as a production fallback; re-run this script from GitHub Actions (workflow_dispatch) to get a real comparison before relying on Groq in production.

Note: Gemini also did not return a result for 20/20 rows this run (see console output for per-batch errors; typically transient 503 high-demand responses or, after enough retries, a daily free-tier quota limit). This is separate from the Groq geo-block above and usually resolves on its own or after the daily quota resets.

| row_id | preview | gemini_valify_scope | groq_valify_scope | gemini_sentiment | groq_sentiment | match |
|---|---|---|---|---|---|---|
| 54 | تأخير في المواعيد ولو منتج هيرجع بيأخروك قوي لحد ماتزهق انك اشتريت منهم ويقولولو |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 659 | التطبيق له عشر ايام مايفتح ويلغي الطلبيات اللي اطلبهم وماحد تواصل معي لفتح التطب |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 687 | بقا اسوء بكتير وبقا بيطلب بطاقة شخصيه وليا فلوس على الحساب وفلوس أوردر موصلش من  |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 1812 | إدارة سيئة مفيش أي زوق يعني إيه أشتري طلبات تتلغي ويطلبوا مني صورة الهوية؟ لا وا |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 2882 | تطبيق جميل في الإستثمار و فتح الحساب سهل لكن لازم لما اجي اشتري السهم يكون السعر |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 2901 | اريد ارسال عقد فتح حسابي باسمي و ايضا اريد رقم واتس اب لارسال العقد بعد ان اوقعه |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 2914 | عملت إيداع بعد كده كتب قيد الانتظار وراح قالي حسابك تم رفضه ومش عارف اخد فلوسي و |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 2930 | فريق دعم بعد اذنكم في مشكله تاخير مراجعة عقدي مش عارف اسحب ولا اعمل إيداع بسبب ك |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 2945 | قمت بفتح حساب من اكتر من 9ايام ولم تاتي الموافقة والتواصل مع الدعم ولكن لا يوجد  |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 2978 | اسوء تجربه رفض بدون داعى فى حين اكتر من ابلكيشن قبلنى ابلكيشن مش صادق |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 2982 | اسوء ناس ينزلوا الليمت ويصدعوك رسائل وقرف وتكلم خدمة العملاء يقولك تمام اتوجة يا |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 2989 | سيئ جدا برفضك بدون اي سبب |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 2991 | زباله بمجرد ما ياخد كل بياناتك بيرفض خلال ثواني |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 2993 | بجد زي الزفت واشتغلالت وخلاص يجي موقفه وتروح يقولك مش مؤهل زفت زفتتين كمان ولا ح |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 3006 | فاشل فاشل كل شويه شبكه النت ضعيفه يلا نصور تاني بعدين النت ضعيف ويكرر ناس بتعذب  |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 3021 | تطبيق ممتاز بس للاسف جالى رفض |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 3066 | التطبيق بيحاول يدخل ع الصور بإستمرار بدون إذن |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 3127 | قدمت عليه و إجراءاته سهلة لكن الرصيد قليل 20 ألف بس مع العلم معايا رخصة موديل عا |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 3193 | تطبيق زباله من قبل اسجل اي حاجة لقيتو كتبلي لا يمكن تسجيل طلبك سجل بعد 90 يوم اي |  | n/a (deferred) |  | n/a (deferred) | n/a |
| 3235 | بيض اوى مش عاوز يكمل تسجيل البيانات |  | n/a (deferred) |  | n/a (deferred) | n/a |
