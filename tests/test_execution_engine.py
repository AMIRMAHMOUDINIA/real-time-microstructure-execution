from __future__ import annotations

import pandas as pd
import pytest

import src.data.simulate_execution_development as execution


def test_classify_signal_respects_thresholds() -> None:
    lower = -0.80
    upper = 0.80

    assert execution.classify_signal(
        -0.81,
        lower,
        upper,
    ) == "SHORT"

    assert execution.classify_signal(
        -0.80,
        lower,
        upper,
    ) == "SHORT"

    assert execution.classify_signal(
        0.00,
        lower,
        upper,
    ) == "FLAT"

    assert execution.classify_signal(
        0.80,
        lower,
        upper,
    ) == "LONG"

    assert execution.classify_signal(
        0.81,
        lower,
        upper,
    ) == "LONG"

    assert execution.classify_signal(
        float("nan"),
        lower,
        upper,
    ) == "FLAT"


def test_first_quote_at_or_after_never_uses_earlier_quote() -> None:
    t0 = pd.Timestamp("2026-09-20T12:00:00Z")

    book = pd.DataFrame(
        {
            "received_at_utc": [
                t0 + pd.Timedelta(milliseconds=50),
                t0 + pd.Timedelta(milliseconds=100),
                t0 + pd.Timedelta(milliseconds=150),
            ],
            "bid_price": [
                99.0,
                100.0,
                101.0,
            ],
            "ask_price": [
                99.1,
                100.1,
                101.1,
            ],
        }
    )

    quote_times = pd.DatetimeIndex(
        book["received_at_utc"]
    )

    target = (
        t0
        + pd.Timedelta(milliseconds=120)
    )

    quote = execution.first_quote_at_or_after(
        book=book,
        quote_times=quote_times,
        target_time=target,
    )

    assert quote is not None

    assert quote["received_at_utc"] == (
        t0
        + pd.Timedelta(milliseconds=150)
    )

    assert quote["received_at_utc"] >= target

    assert quote["bid_price"] == pytest.approx(
        101.0
    )


def test_first_quote_at_or_after_accepts_exact_timestamp() -> None:
    t0 = pd.Timestamp("2026-09-20T12:00:00Z")

    book = pd.DataFrame(
        {
            "received_at_utc": [
                t0,
                t0 + pd.Timedelta(milliseconds=100),
            ],
            "bid_price": [
                100.0,
                101.0,
            ],
            "ask_price": [
                100.1,
                101.1,
            ],
        }
    )

    quote_times = pd.DatetimeIndex(
        book["received_at_utc"]
    )

    target = (
        t0
        + pd.Timedelta(milliseconds=100)
    )

    quote = execution.first_quote_at_or_after(
        book=book,
        quote_times=quote_times,
        target_time=target,
    )

    assert quote is not None
    assert quote["received_at_utc"] == target
    assert quote["bid_price"] == pytest.approx(
        101.0
    )


def test_gross_return_uses_aggressive_bid_ask_sides() -> None:
    long_return = execution.gross_return_bps(
        direction="LONG",
        entry_bid=99.90,
        entry_ask=100.00,
        exit_bid=101.00,
        exit_ask=101.10,
    )

    expected_long = (
        (101.00 / 100.00)
        - 1.0
    ) * 10_000

    assert long_return == pytest.approx(
        expected_long
    )

    short_return = execution.gross_return_bps(
        direction="SHORT",
        entry_bid=100.50,
        entry_ask=100.60,
        exit_bid=99.90,
        exit_ask=100.00,
    )

    expected_short = (
        (100.50 / 100.00)
        - 1.0
    ) * 10_000

    assert short_return == pytest.approx(
        expected_short
    )


def test_simulate_long_trade_applies_decision_time_latency_and_quote_sides(
    monkeypatch,
) -> None:
    """
    Bucket t summarizes [t, t+1).

    Decision must therefore occur at t+1s.

    With 100 ms modeled latency, the earliest permissible entry is
    t+1.100s. A quote at t+1.050s must not be used.

    The actual selected entry quote is t+1.150s.

    With a one-second holding period, the target exit is therefore
    t+2.150s. A quote at t+2.100s must not be used; the selected exit
    quote is t+2.200s.

    LONG execution must pay the entry ask and receive the exit bid.
    """
    t0 = pd.Timestamp(
        "2026-09-20T12:00:00Z"
    )

    features = pd.DataFrame(
        {
            "received_at_utc": [
                t0,
            ],
            execution.SIGNAL_COLUMN: [
                0.90,
            ],
        }
    )

    book = pd.DataFrame(
        {
            "received_at_utc": [
                t0 + pd.Timedelta(
                    seconds=1,
                    milliseconds=50,
                ),
                t0 + pd.Timedelta(
                    seconds=1,
                    milliseconds=150,
                ),
                t0 + pd.Timedelta(
                    seconds=2,
                    milliseconds=100,
                ),
                t0 + pd.Timedelta(
                    seconds=2,
                    milliseconds=200,
                ),
            ],
            "bid_price": [
                99.90,
                100.40,
                100.70,
                101.00,
            ],
            "ask_price": [
                100.00,
                100.50,
                100.80,
                101.10,
            ],
            "update_id": [
                1,
                2,
                3,
                4,
            ],
        }
    )

    monkeypatch.setattr(
        execution,
        "load_features",
        lambda session_id: features.copy(),
    )

    monkeypatch.setattr(
        execution,
        "load_book",
        lambda session_id: book.copy(),
    )

    parameters = {
        "lower_threshold": -0.80,
        "upper_threshold": 0.80,
        "reference_latency_ms": 100.0,
        "holding_period_seconds": 1.0,
    }

    trades, summary = execution.simulate_session(
        session_id="TEST_LONG",
        label="test",
        parameters=parameters,
    )

    assert len(trades) == 1

    trade = trades.iloc[0]

    expected_decision = (
        t0
        + pd.Timedelta(seconds=1)
    )

    expected_target_entry = (
        t0
        + pd.Timedelta(
            seconds=1,
            milliseconds=100,
        )
    )

    expected_actual_entry = (
        t0
        + pd.Timedelta(
            seconds=1,
            milliseconds=150,
        )
    )

    expected_target_exit = (
        t0
        + pd.Timedelta(
            seconds=2,
            milliseconds=150,
        )
    )

    expected_actual_exit = (
        t0
        + pd.Timedelta(
            seconds=2,
            milliseconds=200,
        )
    )

    assert trade["status"] == "COMPLETED"
    assert trade["direction"] == "LONG"

    assert trade["decision_time_utc"] == (
        expected_decision
    )

    assert trade["target_entry_time_utc"] == (
        expected_target_entry
    )

    assert trade["actual_entry_time_utc"] == (
        expected_actual_entry
    )

    assert trade["target_exit_time_utc"] == (
        expected_target_exit
    )

    assert trade["actual_exit_time_utc"] == (
        expected_actual_exit
    )

    assert trade["decision_to_entry_ms"] == (
        pytest.approx(150.0)
    )

    assert trade["entry_quote_wait_ms"] == (
        pytest.approx(50.0)
    )

    assert trade["exit_quote_wait_ms"] == (
        pytest.approx(50.0)
    )

    assert trade["entry_bid"] == pytest.approx(
        100.40
    )

    assert trade["entry_ask"] == pytest.approx(
        100.50
    )

    assert trade["exit_bid"] == pytest.approx(
        101.00
    )

    assert trade["exit_ask"] == pytest.approx(
        101.10
    )

    expected_return = (
        (101.00 / 100.50)
        - 1.0
    ) * 10_000

    assert trade["gross_return_bps"] == (
        pytest.approx(expected_return)
    )

    assert summary["completed_trades"] == 1

    assert summary[
        "mean_gross_return_bps"
    ] == pytest.approx(
        expected_return
    )

    assert summary[
        "break_even_additional_cost_per_side_bps"
    ] == pytest.approx(
        expected_return / 2.0
    )


def test_simulate_short_trade_uses_entry_bid_and_exit_ask(
    monkeypatch,
) -> None:
    """
    SHORT execution must sell at the entry bid and buy back at the exit ask.
    """
    t0 = pd.Timestamp(
        "2026-09-20T12:00:00Z"
    )

    features = pd.DataFrame(
        {
            "received_at_utc": [
                t0,
            ],
            execution.SIGNAL_COLUMN: [
                -0.90,
            ],
        }
    )

    book = pd.DataFrame(
        {
            "received_at_utc": [
                t0 + pd.Timedelta(seconds=1),
                t0 + pd.Timedelta(seconds=2),
            ],
            "bid_price": [
                100.50,
                99.90,
            ],
            "ask_price": [
                100.60,
                100.00,
            ],
            "update_id": [
                1,
                2,
            ],
        }
    )

    monkeypatch.setattr(
        execution,
        "load_features",
        lambda session_id: features.copy(),
    )

    monkeypatch.setattr(
        execution,
        "load_book",
        lambda session_id: book.copy(),
    )

    parameters = {
        "lower_threshold": -0.80,
        "upper_threshold": 0.80,
        "reference_latency_ms": 0.0,
        "holding_period_seconds": 1.0,
    }

    trades, summary = execution.simulate_session(
        session_id="TEST_SHORT",
        label="test",
        parameters=parameters,
    )

    assert len(trades) == 1

    trade = trades.iloc[0]

    assert trade["status"] == "COMPLETED"
    assert trade["direction"] == "SHORT"

    assert trade["entry_bid"] == pytest.approx(
        100.50
    )

    assert trade["entry_ask"] == pytest.approx(
        100.60
    )

    assert trade["exit_bid"] == pytest.approx(
        99.90
    )

    assert trade["exit_ask"] == pytest.approx(
        100.00
    )

    expected_return = (
        (100.50 / 100.00)
        - 1.0
    ) * 10_000

    assert trade["gross_return_bps"] == (
        pytest.approx(expected_return)
    )

    assert summary[
        "completed_short_trades"
    ] == 1

    assert summary[
        "short_mean_gross_return_bps"
    ] == pytest.approx(
        expected_return
    )
