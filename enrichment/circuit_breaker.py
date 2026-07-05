"""
Lightweight per-provider circuit breaker.

States:
  CLOSED    — healthy; requests pass through normally.
  OPEN      — failed; requests are skipped without hitting the API.
  HALF_OPEN — after cooldown, one test request is allowed through to check recovery.

Two failure modes with different recovery behaviour:
  quota     — daily limit exhausted (429); stays OPEN for the remainder of the run.
  transient — 503 or network error; 5-minute cooldown before moving to HALF_OPEN.
"""
import time


class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    TRANSIENT_COOLDOWN = 300.0   # 5 minutes for 503 / network errors
    QUOTA_COOLDOWN = float("inf")  # daily quota: never auto-recover within a run

    def __init__(self, name: str, failure_threshold: int = 2):
        self.name = name
        self._threshold = failure_threshold
        self._state = self.CLOSED
        self._consecutive_failures = 0
        self._opened_at = 0.0
        self._cooldown = self.TRANSIENT_COOLDOWN

    @property
    def state(self) -> str:
        if self._state == self.OPEN and self._cooldown < float("inf"):
            elapsed = time.time() - self._opened_at
            if elapsed >= self._cooldown:
                self._state = self.HALF_OPEN
        return self._state

    @property
    def is_open(self) -> bool:
        return self.state == self.OPEN

    def record_success(self) -> None:
        self._state = self.CLOSED
        self._consecutive_failures = 0

    def record_quota_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._threshold:
            self._state = self.OPEN
            self._opened_at = time.time()
            self._cooldown = self.QUOTA_COOLDOWN
            print(
                f"[circuit_breaker] {self.name}: OPEN "
                f"(quota exhausted — will not recover within this run)"
            )

    def record_transient_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._threshold:
            self._state = self.OPEN
            self._opened_at = time.time()
            self._cooldown = self.TRANSIENT_COOLDOWN
            print(
                f"[circuit_breaker] {self.name}: OPEN "
                f"(transient — cooldown {self.TRANSIENT_COOLDOWN:.0f}s)"
            )
