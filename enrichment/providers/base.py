"""
Abstract base class and shared types for enrichment providers.

All providers implement the same two methods:
  classify_one_batch  — valify_scope + sentiment for up to 10 rows
  enrich_one_batch    — all 7 enrichment fields for up to 10 rows

On failure, providers raise one of the three exceptions below.
They never return parse_error values — that decision belongs to the caller.
"""
import json
from abc import ABC, abstractmethod


class ProviderQuotaError(Exception):
    """Daily quota exhausted (HTTP 429 or explicit quota message)."""
    pass


class ProviderUnavailableError(Exception):
    """Transient unavailability: 503, 500, or network failure."""
    pass


class ProviderParseError(Exception):
    """Provider returned a response that could not be parsed as valid JSON.
    Does not indicate quota or availability failure — try the next provider
    without updating the circuit breaker."""
    pass


class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def classify_one_batch(self, batch: list, system_instruction: str) -> list:
        """
        Classify valify_scope and sentiment for a batch of up to 10 rows.
        Each row must have: row_id, client, source, review_text.
        Returns list of {row_id, valify_scope, sentiment}.
        Raises ProviderQuotaError, ProviderUnavailableError, or ProviderParseError on failure.
        """
        ...

    @abstractmethod
    def enrich_one_batch(self, batch: list, system_instruction: str) -> list:
        """
        Full enrichment for a batch of up to 10 rows (all 7 enrichment fields).
        Returns list with row_id + all 7 fields.
        Raises ProviderQuotaError, ProviderUnavailableError, or ProviderParseError on failure.
        """
        ...


# ---------------------------------------------------------------------------
# Shared prompt builders — identical content for all providers.
# ---------------------------------------------------------------------------

def classify_prompt(batch: list) -> str:
    return (
        "Classify the following reviews. For each review, determine two fields:\n"
        "  valify_scope: true / false / unsure\n"
        "  sentiment: positive / negative / neutral\n\n"
        "Rules:\n"
        "- Base valify_scope on the ACTION described, not on whether Valify is named.\n"
        "- Users never mention Valify by name. Detect by what the user did or was asked to do.\n"
        "- Understand Egyptian Arabic dialect, Modern Standard Arabic, and English natively.\n"
        "  Do not translate. Classify in the language the review is written in.\n"
        "- Sentiment applies to any review regardless of valify_scope value.\n"
        "- Return ONLY a valid JSON array. No preamble. No explanation. No markdown fences.\n"
        "- Each element: {\"row_id\": \"...\", \"valify_scope\": \"...\", \"sentiment\": \"...\"}\n\n"
        "Reviews to classify:\n"
        + json.dumps(batch, ensure_ascii=False)
    )


def enrich_prompt(batch: list) -> str:
    return (
        "Classify the following reviews. For each review, return all 7 enrichment fields.\n\n"
        "Fields to return for each review:\n"
        "  sentiment: positive / negative / neutral\n"
        "  feedback_type: bug / ux_friction / feature_request / compliment / off_topic\n"
        "  product_area: nid_verification / liveness_detection / facematch / onboarding_general / other\n"
        "  severity: critical / high / medium / low / none\n"
        "  agreement_signal: true / false\n"
        "  claude_summary: one sentence in English, max 200 characters\n"
        "  valify_scope: true / false / unsure\n\n"
        "Rules:\n"
        "- Base valify_scope on the ACTION described, not on whether Valify is named.\n"
        "- Users never mention Valify by name. Detect by what the user did or was asked to do.\n"
        "- Understand Egyptian Arabic dialect, Modern Standard Arabic, and English natively.\n"
        "  Do not translate. Classify in the language the review is written in.\n"
        "- For off_topic rows: severity = none, product_area = other, valify_scope = false.\n"
        "- agreement_signal is true only if the review text itself contains phrases like\n"
        "  'same here', 'me too', 'نفس المشكلة', 'أنا كمان' or explicit third-party confirmation.\n"
        "- For web_ddg source rows: these are web search snippets, often vague. Use 'unsure' for\n"
        "  valify_scope when the snippet does not clearly describe the ID capture step.\n"
        "- Return ONLY a valid JSON array. No preamble. No explanation. No markdown fences.\n"
        "- Each element must have all 7 fields plus row_id.\n\n"
        "Reviews to classify:\n"
        + json.dumps(batch, ensure_ascii=False)
    )
