"""
ProviderChain — tries providers in order at the per-batch level.

When a provider's circuit is OPEN or raises a quota/availability error, the chain
falls through to the next provider immediately. If all providers fail for a batch,
that batch is skipped: its rows stay blank in the sheet (not parse_error).

Checkpoint:
  Written to scripts/enrichment_checkpoint.json after every batch so a mid-run
  crash can be diagnosed. The checkpoint stores row-level results and which
  provider handled each row. Auto-resume from checkpoint is not yet implemented —
  add in Phase 9.5 if crash recovery becomes a recurring need.
"""
import json
import os
import time
from datetime import datetime

from enrichment.circuit_breaker import CircuitBreaker
from enrichment.providers.base import (
    BaseProvider,
    ProviderParseError,
    ProviderQuotaError,
    ProviderUnavailableError,
)

_BATCH_SIZE = 10
_BATCH_DELAY = 6.0  # seconds between batches — raised from 4.0 to stay clear of the 15 RPM free-tier ceiling

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CHECKPOINT_PATH = os.path.join(_PROJECT_ROOT, "scripts", "enrichment_checkpoint.json")


class ProviderChain:
    def __init__(self, providers: list):
        self._providers = providers
        self._breakers = {p.name: CircuitBreaker(p.name) for p in providers}
        self._run_id = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        self._checkpoint = {
            "run_id": self._run_id,
            "results": [],
            "skipped_row_ids": [],
            "provider_used": {},
        }

    def _try_batch(self, batch: list, method: str, system_instruction: str):
        """Attempt one batch against each provider in order.

        Returns (results, provider_name) on success, (None, None) if all fail.
        """
        for provider in self._providers:
            cb = self._breakers[provider.name]
            if cb.is_open:
                print(f"[chain] {provider.name} circuit OPEN — skipping")
                continue
            try:
                fn = getattr(provider, method)
                results = fn(batch, system_instruction)
                cb.record_success()
                return results, provider.name
            except ProviderQuotaError as exc:
                print(f"[chain] {provider.name} quota: {exc}")
                cb.record_quota_failure()
            except ProviderUnavailableError as exc:
                print(f"[chain] {provider.name} unavailable: {exc}")
                cb.record_transient_failure()
            except ProviderParseError as exc:
                # Parse errors don't indicate quota/availability problems.
                # Try next provider without touching the circuit breaker.
                print(f"[chain] {provider.name} parse error, trying next provider: {exc}")
            except Exception as exc:
                print(f"[chain] {provider.name} unexpected error: {exc}")
                cb.record_transient_failure()
        return None, None

    def _save_checkpoint(self) -> None:
        try:
            with open(_CHECKPOINT_PATH, "w", encoding="utf-8") as fh:
                json.dump(self._checkpoint, fh, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"[chain] checkpoint write failed: {exc}")

    def _run_batches(self, rows: list, method: str, system_instruction: str) -> list:
        all_results = []
        skipped_rows = 0
        batch_count = (len(rows) + _BATCH_SIZE - 1) // _BATCH_SIZE

        for i in range(0, len(rows), _BATCH_SIZE):
            if i > 0:
                time.sleep(_BATCH_DELAY)

            batch = rows[i : i + _BATCH_SIZE]
            batch_ids = [r["row_id"] for r in batch]
            batch_num = i // _BATCH_SIZE + 1

            results, provider_name = self._try_batch(batch, method, system_instruction)

            if results is None:
                print(
                    f"[chain] Batch {batch_num}/{batch_count}: "
                    f"all providers failed — skipping {len(batch)} rows {batch_ids}"
                )
                self._checkpoint["skipped_row_ids"].extend(batch_ids)
                skipped_rows += len(batch)
            else:
                for r in results:
                    self._checkpoint["provider_used"][r["row_id"]] = provider_name
                self._checkpoint["results"].extend(results)
                all_results.extend(results)
                print(
                    f"[chain] Batch {batch_num}/{batch_count}: "
                    f"{len(results)} rows via {provider_name}"
                )

            self._save_checkpoint()

        if skipped_rows:
            print(
                f"[chain] Run complete. {skipped_rows} rows skipped "
                f"(all providers exhausted — rows left blank in sheet)."
            )
        return all_results

    def classify_batch(self, rows: list, system_instruction: str) -> list:
        return self._run_batches(rows, "classify_one_batch", system_instruction)

    def enrich_full_batch(self, rows: list, system_instruction: str) -> list:
        return self._run_batches(rows, "enrich_one_batch", system_instruction)

    def provider_summary(self) -> dict:
        counts = {}
        for provider_name in self._checkpoint["provider_used"].values():
            counts[provider_name] = counts.get(provider_name, 0) + 1
        skipped = len(self._checkpoint["skipped_row_ids"])
        if skipped:
            counts["skipped"] = skipped
        return counts
