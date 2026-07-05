# Enrichment Taxonomy — Field Definitions

## `language`
| Value | Meaning |
|---|---|
| `ar` | Primarily Arabic (Egyptian dialect or formal) |
| `en` | Primarily English |
| `ar-en` | Mixed (Arabizi, code-switching, Franco-Arabic) |

## `sentiment`
Capture direction even when the topic is off-topic.
| Value | Meaning |
|---|---|
| `positive` | User had a good experience with what they are describing |
| `negative` | User had a bad or frustrating experience |
| `neutral` | Describing something factually without a clear positive or negative tone |

Note: `mixed` was removed in Phase 8. Reviews that contain both tones should be
classified by the dominant tone, or `neutral` if neither tone clearly outweighs the other.

## `feedback_type`
| Value | Meaning |
|---|---|
| `bug` | Technical failure: crash, error, broken step |
| `ux_friction` | Usability issue: confusing, slow, unclear, frustrating |
| `feature_request` | User wants something the app doesn't do, including suggestions |
| `compliment` | Praise for the verification/onboarding flow |
| `off_topic` | Not about KYC, identity verification, or the onboarding flow |

## `product_area`
Only classify to a specific Valify product if the client actually uses it.
| Value | Signals |
|---|---|
| `nid_verification` | ID card scan, photo of ID, OCR, "البطاقة", document upload |
| `liveness_detection` | Selfie video, blink/smile/move-head instructions, camera prompts |
| `facematch` | Selfie photo, "face not matching", photo vs ID card |
| `onboarding_general` | Signup, account opening, generic verification, not product-specific |
| `other` | None of the above |

## `severity`
| Value | Meaning |
|---|---|
| `critical` | User could not complete the flow and gave up or was fully blocked |
| `high` | User completed with significant difficulty, nearly gave up |
| `medium` | User completed but was frustrated or needed multiple attempts |
| `low` | Minor inconvenience, did not block completion |
| `none` | Not a friction issue (compliment, suggestion, off-topic, neutral) |

## `valify_scope`
Whether the review describes the identity verification step that Valify powers.
Classification is based on the ACTION described, not on whether Valify is named.
| Value | Meaning |
|---|---|
| `true` | Review describes ID capture, selfie capture, liveness detection, face match, or phone number verification during onboarding. |
| `false` | Review has nothing to do with the verification step. About post-onboarding status, customer support, funds, login, or any product feature after onboarding completed. |
| `unsure` | Review mentions onboarding going wrong but does not describe the specific step clearly enough to attribute to the verification step. |

## `agreement_signal`
`true` if visible comments/replies confirm the issue (same here, me too, 
نفس المشكلة, أنا كمان). `false` if no confirmation or no comments available.

## `claude_summary`
One sentence in English. Max 200 chars.
- Friction: *"User's national ID was rejected three times during return flow."*
- Praise: *"User praises the fast ID verification at signup."*
- Suggestion: *"User asks for an option to upload ID from gallery instead of camera."*
- Off-topic: *"Complaint about delivery time, unrelated to verification."*
