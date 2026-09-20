from __future__ import annotations

import pandas as pd
import pytest
from pandas.testing import assert_series_equal

from src.data.build_session_features import (
    add_future_targets,
    build_book_features,
    build_trade_features,
    combine_features,
)


def _book_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Create a minimal valid raw Level-1 book DataFrame."""
    return pd.DataFrame(rows)


def _trade_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Create a minimal valid raw trade DataFrame."""
    return pd.DataFrame(rows)


def test_book_features_do_not_use_future_second() -> None:
    """
    Changing raw book observations after the end of a one-second bucket
    must not change features already computed for that earlier bucket.
    """
    t0 = pd.Timestamp("2026-09-20T12:00:00Z")

    baseline = _book_dataframe(
        [
            {
                "received_at_utc": t0 + pd.Timedelta(milliseconds=100),
                "update_id": 1,
                "mid_price": 100.0,
                "spread": 0.10,
                "imbalance": 0.20,
                "bid_quantity": 12.0,
                "ask_quantity": 8.0,
            },
            {
                "received_at_utc": t0 + pd.Timedelta(milliseconds=800),
                "update_id": 2,
                "mid_price": 101.0,
                "spread": 0.20,
                "imbalance": 0.40,
                "bid_quantity": 14.0,
                "ask_quantity": 6.0,
            },
            {
                "received_at_utc": t0 + pd.Timedelta(seconds=1, milliseconds=100),
                "update_id": 3,
                "mid_price": 102.0,
                "spread": 0.30,
                "imbalance": 0.60,
                "bid_quantity": 16.0,
                "ask_quantity": 4.0,
            },
        ]
    )

    modified_future = baseline.copy()

    future_mask = (
        modified_future["received_at_utc"]
        >= t0 + pd.Timedelta(seconds=1)
    )

    modified_future.loc[future_mask, "mid_price"] = 10_000.0
    modified_future.loc[future_mask, "spread"] = 50.0
    modified_future.loc[future_mask, "imbalance"] = -0.99
    modified_future.loc[future_mask, "bid_quantity"] = 1.0
    modified_future.loc[future_mask, "ask_quantity"] = 1_000.0

    baseline_features = build_book_features(baseline)
    modified_features = build_book_features(modified_future)

    assert_series_equal(
        baseline_features.loc[t0],
        modified_features.loc[t0],
        check_names=False,
    )

    next_second = t0 + pd.Timedelta(seconds=1)

    assert not baseline_features.loc[next_second].equals(
        modified_features.loc[next_second]
    )


def test_trade_features_do_not_use_future_second() -> None:
    """
    Changing trades in a later second must not alter the trade features
    belonging to an earlier second.
    """
    t0 = pd.Timestamp("2026-09-20T12:00:00Z")

    baseline = _trade_dataframe(
        [
            {
                "received_at_utc": t0 + pd.Timedelta(milliseconds=150),
                "trade_id": 1,
                "price": 100.0,
                "quantity": 2.0,
                "quote_value": 200.0,
                "aggressor_side": "BUY",
            },
            {
                "received_at_utc": t0 + pd.Timedelta(milliseconds=700),
                "trade_id": 2,
                "price": 100.0,
                "quantity": 1.0,
                "quote_value": 100.0,
                "aggressor_side": "SELL",
            },
            {
                "received_at_utc": t0 + pd.Timedelta(seconds=1, milliseconds=200),
                "trade_id": 3,
                "price": 101.0,
                "quantity": 3.0,
                "quote_value": 303.0,
                "aggressor_side": "BUY",
            },
        ]
    )

    modified_future = baseline.copy()

    future_mask = (
        modified_future["received_at_utc"]
        >= t0 + pd.Timedelta(seconds=1)
    )

    modified_future.loc[future_mask, "quantity"] = 1_000.0
    modified_future.loc[future_mask, "quote_value"] = 100_000.0
    modified_future.loc[future_mask, "aggressor_side"] = "SELL"

    baseline_features = build_trade_features(baseline)
    modified_features = build_trade_features(modified_future)

    assert_series_equal(
        baseline_features.loc[t0],
        modified_features.loc[t0],
        check_names=False,
    )

    next_second = t0 + pd.Timedelta(seconds=1)

    assert not baseline_features.loc[next_second].equals(
        modified_features.loc[next_second]
    )


def test_missing_book_second_is_filled_from_past_not_future() -> None:
    """
    combine_features uses forward-fill for mid price.

    A missing second must therefore inherit the last observed past price,
    rather than leaking the next available future price backward.
    """
    t0 = pd.Timestamp("2026-09-20T12:00:00Z")

    book = _book_dataframe(
        [
            {
                "received_at_utc": t0 + pd.Timedelta(milliseconds=100),
                "update_id": 1,
                "mid_price": 100.0,
                "spread": 0.10,
                "imbalance": 0.25,
                "bid_quantity": 10.0,
                "ask_quantity": 8.0,
            },
            {
                "received_at_utc": t0 + pd.Timedelta(seconds=2, milliseconds=100),
                "update_id": 2,
                "mid_price": 200.0,
                "spread": 0.20,
                "imbalance": -0.25,
                "bid_quantity": 8.0,
                "ask_quantity": 10.0,
            },
        ]
    )

    trades = _trade_dataframe(
        [
            {
                "received_at_utc": t0 + pd.Timedelta(milliseconds=300),
                "trade_id": 1,
                "price": 100.0,
                "quantity": 1.0,
                "quote_value": 100.0,
                "aggressor_side": "BUY",
            }
        ]
    )

    book_features = build_book_features(book)
    trade_features = build_trade_features(trades)

    combined = combine_features(
        book_features,
        trade_features,
    )

    missing_second = t0 + pd.Timedelta(seconds=1)

    assert combined.loc[missing_second, "mid_price"] == pytest.approx(100.0)

    assert combined.loc[
        t0 + pd.Timedelta(seconds=2),
        "mid_price",
    ] == pytest.approx(200.0)


def test_future_return_target_matches_known_prices() -> None:
    """
    Verify the explicit definition of the one-second forward return target.
    """
    t0 = pd.Timestamp("2026-09-20T12:00:00Z")

    features = pd.DataFrame(
        {
            "mid_price": [
                100.0,
                101.0,
                99.0,
            ]
        },
        index=pd.date_range(
            start=t0,
            periods=3,
            freq="1s",
        ),
    )

    result = add_future_targets(features)

    assert result.loc[
        t0,
        "future_mid_1s",
    ] == pytest.approx(101.0)

    assert result.loc[
        t0,
        "future_return_1s_bps",
    ] == pytest.approx(100.0)

    second = t0 + pd.Timedelta(seconds=1)

    expected_second_return = (
        (99.0 / 101.0) - 1.0
    ) * 10_000

    assert result.loc[
        second,
        "future_return_1s_bps",
    ] == pytest.approx(expected_second_return)

    final_second = t0 + pd.Timedelta(seconds=2)

    assert pd.isna(
        result.loc[
            final_second,
            "future_mid_1s",
        ]
    )

    assert pd.isna(
        result.loc[
            final_second,
            "future_return_1s_bps",
        ]
    )
