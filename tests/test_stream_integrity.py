from __future__ import annotations

import asyncio
import csv
import io
import json
from datetime import datetime, timezone

import pytest

from src.data import collect_live_session
from src.data.stream_integrity import (
    StreamHealth,
    exponential_backoff,
)


def test_sequence_integrity():
    health = StreamHealth("book")

    assert health.observe_sequence(10) == "accepted"
    assert health.observe_sequence(12) == "accepted"
    assert health.observe_sequence(12) == "duplicate"
    assert health.observe_sequence(11) == "out_of_order"

    assert health.accepted_messages == 2
    assert health.duplicate_ids == 1
    assert health.out_of_order_ids == 1
    assert health.last_sequence_id == 12


def test_backoff_is_bounded():
    assert exponential_backoff(0) == pytest.approx(0.5)
    assert exponential_backoff(1) == pytest.approx(1.0)
    assert exponential_backoff(4) == pytest.approx(8.0)
    assert exponential_backoff(20) == pytest.approx(8.0)


def test_timeout_streak_resets():
    health = StreamHealth("book")

    health.record_timeout()
    health.record_timeout()

    health.record_raw(
        datetime.now(timezone.utc)
    )

    health.record_timeout()

    assert health.receive_timeouts == 3
    assert health.max_consecutive_timeouts == 2


def test_book_duplicate_is_not_written():
    output = io.StringIO()
    writer = csv.writer(output)
    health = StreamHealth("book")

    now = datetime.now(timezone.utc)

    def message(update_id):
        return json.dumps({
            "u": update_id,
            "s": "BTCUSDT",
            "b": "100",
            "B": "10",
            "a": "101",
            "A": "8",
        })

    health.record_raw(now)

    assert collect_live_session._process_book(
        message(1),
        writer,
        health,
        now,
    )

    health.record_raw(now)

    assert not collect_live_session._process_book(
        message(1),
        writer,
        health,
        now,
    )

    rows = list(
        csv.reader(
            io.StringIO(output.getvalue())
        )
    )

    assert len(rows) == 1
    assert health.duplicate_ids == 1


class FakeSocket:
    def __init__(self, messages):
        self.messages = list(messages)

    async def recv(self):
        if self.messages:
            return self.messages.pop(0)

        await asyncio.sleep(3600)


class FakeContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value

    async def __aexit__(self, *args):
        return False


class FakeConnector:
    def __init__(self, values):
        self.values = list(values)

    def __call__(self, uri):
        del uri
        return FakeContext(
            self.values.pop(0)
        )


def test_runner_retries_connection_failure():
    async def scenario():
        stop_event = asyncio.Event()
        health = StreamHealth("test")

        connector = FakeConnector([
            OSError("temporary"),
            FakeSocket(["ok"]),
        ])

        def handler(message, received_at):
            del message, received_at
            health.observe_sequence(1)
            stop_event.set()

        await collect_live_session._run_stream(
            name="Test",
            uri="wss://example.invalid",
            stop_event=stop_event,
            health=health,
            on_message=handler,
            stale_seconds=1.0,
            poll_seconds=0.01,
            connect_factory=connector,
            backoff_base=0.0,
            backoff_max=0.0,
        )

        return health

    health = asyncio.run(scenario())

    assert health.connection_errors == 1
    assert health.retry_attempts == 1
    assert health.connections == 1
    assert health.accepted_messages == 1
