from __future__ import annotations

import pandas as pd
import pytest

from src.data.simulate_execution_development import (
    validate_completed_trades,
)


def _valid_trade(
    *,
    session_id: str = "TEST_SESSION",
    entry_offset_seconds: float = 1.1,
    exit_offset_seconds: float = 2.1,
) -> dict:
    """
    Construct one trade satisfying the frozen execution protocol:

    bucket start:   t
    decision:       t + 1.0 s
    target entry:   t + 1.1 s
    actual entry:   t + entry_offset_seconds
    target exit:    actual entry + 1.0 s
    actual exit:    t + exit_offset_seconds
    """
    t0 = pd.Timestamp(
        "2026-09-20T12:00:00Z"
    )

    actual_entry = (
        t0
        + pd.Timedelta(
            seconds=entry_offset_seconds
        )
    )

    target_exit = (
        actual_entry
        + pd.Timedelta(seconds=1)
    )

    actual_exit = (
        t0
        + pd.Timedelta(
            seconds=exit_offset_seconds
        )
    )

    return {
        "session_id": session_id,
        "status": "COMPLETED",

        "bucket_start_utc": t0,

        "decision_time_utc": (
            t0
            + pd.Timedelta(seconds=1)
        ),

        "target_entry_time_utc": (
            t0
            + pd.Timedelta(
                seconds=1,
                milliseconds=100,
            )
        ),

        "actual_entry_time_utc": actual_entry,

        "target_exit_time_utc": target_exit,

        "actual_exit_time_utc": actual_exit,

        "decision_to_entry_ms": (
            (
                actual_entry
                - (
                    t0
                    + pd.Timedelta(seconds=1)
                )
            ).total_seconds()
            * 1000
        ),

        "holding_time_actual_seconds": (
            actual_exit
            - actual_entry
        ).total_seconds(),
    }


def test_valid_completed_trade_passes_all_checks() -> None:
    trades = pd.DataFrame(
        [
            _valid_trade(),
        ]
    )

    checks, all_pass = validate_completed_trades(
        trades
    )

    assert all_pass is True
    assert all(checks.values())

    assert checks[
        "decision_equals_bucket_plus_1s"
    ] is True

    assert checks[
        "target_entry_not_before_decision"
    ] is True

    assert checks[
        "actual_entry_not_before_target"
    ] is True

    assert checks[
        "target_exit_not_before_entry"
    ] is True

    assert checks[
        "actual_exit_not_before_target"
    ] is True

    assert checks[
        "all_decision_to_entry_at_least_100ms"
    ] is True

    assert checks[
        "all_actual_holding_at_least_1s"
    ] is True

    assert checks[
        "no_overlapping_positions"
    ] is True


def test_validator_detects_entry_before_target() -> None:
    trade = _valid_trade()

    trade["actual_entry_time_utc"] = (
        pd.Timestamp(
            "2026-09-20T12:00:01.050Z"
        )
    )

    trade["decision_to_entry_ms"] = 50.0

    trade["target_exit_time_utc"] = (
        trade["actual_entry_time_utc"]
        + pd.Timedelta(seconds=1)
    )

    trade["actual_exit_time_utc"] = (
        trade["target_exit_time_utc"]
    )

    trade["holding_time_actual_seconds"] = 1.0

    trades = pd.DataFrame(
        [
            trade,
        ]
    )

    checks, all_pass = validate_completed_trades(
        trades
    )

    assert all_pass is False

    assert checks[
        "actual_entry_not_before_target"
    ] is False

    assert checks[
        "all_decision_to_entry_at_least_100ms"
    ] is False


def test_validator_detects_overlapping_positions() -> None:
    first = _valid_trade(
        entry_offset_seconds=1.1,
        exit_offset_seconds=2.5,
    )

    t0 = pd.Timestamp(
        "2026-09-20T12:00:00Z"
    )

    second_bucket = (
        t0
        + pd.Timedelta(seconds=1)
    )

    second = {
        "session_id": "TEST_SESSION",
        "status": "COMPLETED",

        "bucket_start_utc": second_bucket,

        "decision_time_utc": (
            second_bucket
            + pd.Timedelta(seconds=1)
        ),

        "target_entry_time_utc": (
            second_bucket
            + pd.Timedelta(
                seconds=1,
                milliseconds=100,
            )
        ),

        "actual_entry_time_utc": (
            second_bucket
            + pd.Timedelta(
                seconds=1,
                milliseconds=100,
            )
        ),

        "target_exit_time_utc": (
            second_bucket
            + pd.Timedelta(
                seconds=2,
                milliseconds=100,
            )
        ),

        "actual_exit_time_utc": (
            second_bucket
            + pd.Timedelta(
                seconds=2,
                milliseconds=100,
            )
        ),

        "decision_to_entry_ms": 100.0,
        "holding_time_actual_seconds": 1.0,
    }

    trades = pd.DataFrame(
        [
            first,
            second,
        ]
    )

    checks, all_pass = validate_completed_trades(
        trades
    )

    assert all_pass is False

    assert checks[
        "no_overlapping_positions"
    ] is False


def test_validator_raises_when_no_completed_trades() -> None:
    trades = pd.DataFrame(
        [
            {
                "status": "INCOMPLETE_NO_EXIT",
            }
        ]
    )

    with pytest.raises(
        RuntimeError,
        match="No completed development trades",
    ):
        validate_completed_trades(
            trades
        )
