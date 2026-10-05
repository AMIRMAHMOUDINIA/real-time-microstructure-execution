from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class StreamHealth:
    stream: str
    connections: int = 0
    reconnects: int = 0
    retry_attempts: int = 0
    raw_messages: int = 0
    accepted_messages: int = 0
    receive_timeouts: int = 0
    stale_reconnects: int = 0
    connection_errors: int = 0
    duplicate_ids: int = 0
    out_of_order_ids: int = 0
    malformed_messages: int = 0
    max_consecutive_timeouts: int = 0
    last_sequence_id: int | None = None
    first_received_at_utc: str | None = None
    last_received_at_utc: str | None = None
    _timeout_streak: int = field(default=0, repr=False)

    def record_connection(self) -> None:
        self.connections += 1
        if self.connections > 1:
            self.reconnects += 1
        self._timeout_streak = 0

    def record_timeout(self) -> None:
        self.receive_timeouts += 1
        self._timeout_streak += 1
        self.max_consecutive_timeouts = max(
            self.max_consecutive_timeouts,
            self._timeout_streak,
        )

    def record_raw(self, received_at: datetime) -> None:
        stamp = (
            received_at.astimezone(timezone.utc)
            .isoformat()
        )
        self.raw_messages += 1
        self._timeout_streak = 0
        if self.first_received_at_utc is None:
            self.first_received_at_utc = stamp
        self.last_received_at_utc = stamp

    def observe_sequence(self, sequence_id: int) -> str:
        sequence_id = int(sequence_id)

        if self.last_sequence_id is not None:
            if sequence_id == self.last_sequence_id:
                self.duplicate_ids += 1
                return "duplicate"

            if sequence_id < self.last_sequence_id:
                self.out_of_order_ids += 1
                return "out_of_order"

        self.last_sequence_id = sequence_id
        self.accepted_messages += 1
        return "accepted"

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("_timeout_streak")
        return data


def exponential_backoff(
    attempt: int,
    base_seconds: float = 0.5,
    max_seconds: float = 8.0,
) -> float:
    if attempt < 0:
        raise ValueError("attempt must be non-negative")
    if base_seconds < 0 or max_seconds < 0:
        raise ValueError("backoff values must be non-negative")

    return min(
        base_seconds * (2 ** attempt),
        max_seconds,
    )
