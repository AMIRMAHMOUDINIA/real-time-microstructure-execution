from __future__ import annotations

from math import isclose
from pathlib import Path

import pandas as pd

import src.data.build_session_features as feature_builder
import src.data.simulate_execution_development as execution


SESSION_ID = "20260829_091754"
LABEL = "holdout_5"

SAMPLE_DIR = Path(__file__).resolve().parent

BOOK_FILE = (
    SAMPLE_DIR
    / f"btcusdt_book_{SESSION_ID}.csv.gz"
)

TRADE_FILE = (
    SAMPLE_DIR
    / f"btcusdt_trades_{SESSION_ID}.csv.gz"
)


EXPECTED_COMPLETED_TRADES = 78
EXPECTED_LONG_TRADES = 41
EXPECTED_SHORT_TRADES = 37

EXPECTED_MEAN_GROSS_RETURN_BPS = (
    0.045895152297883206
)

EXPECTED_BREAK_EVEN_COST_PER_SIDE_BPS = (
    0.022947576148941603
)


def prepare_execution_book(
    book: pd.DataFrame,
) -> pd.DataFrame:
    """
    Apply the same quote-validity and ordering rules used by
    simulate_execution_development.load_book().
    """
    book = book.copy()

    required_columns = [
        "received_at_utc",
        "bid_price",
        "ask_price",
    ]

    for column in required_columns:
        if column not in book.columns:
            raise KeyError(
                f"Missing required raw-book column: "
                f"{column}"
            )

    book["received_at_utc"] = pd.to_datetime(
        book["received_at_utc"],
        utc=True,
        format="mixed",
        errors="coerce",
    )

    for column in [
        "bid_price",
        "ask_price",
    ]:
        book[column] = pd.to_numeric(
            book[column],
            errors="coerce",
        )

    if "bid_quantity" in book.columns:
        book["bid_quantity"] = pd.to_numeric(
            book["bid_quantity"],
            errors="coerce",
        )

    if "ask_quantity" in book.columns:
        book["ask_quantity"] = pd.to_numeric(
            book["ask_quantity"],
            errors="coerce",
        )

    if "update_id" in book.columns:
        book["update_id"] = pd.to_numeric(
            book["update_id"],
            errors="coerce",
        )

    book = book.dropna(
        subset=[
            "received_at_utc",
            "bid_price",
            "ask_price",
        ]
    ).copy()

    book = book[
        (book["bid_price"] > 0)
        &
        (book["ask_price"] > 0)
        &
        (book["ask_price"] >= book["bid_price"])
    ].copy()

    book = book.sort_values(
        "received_at_utc",
        kind="mergesort",
    ).reset_index(
        drop=True
    )

    if len(book) == 0:
        raise RuntimeError(
            "No valid book quotes remain."
        )

    return book


def build_features() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Rebuild the frozen one-second feature dataset from the
    public compressed raw sample.
    """
    book, trades = feature_builder.load_raw_data(
        BOOK_FILE,
        TRADE_FILE,
    )

    book_features = (
        feature_builder.build_book_features(
            book
        )
    )

    trade_features = (
        feature_builder.build_trade_features(
            trades
        )
    )

    features = feature_builder.combine_features(
        book_features,
        trade_features,
    )

    features = feature_builder.add_future_targets(
        features
    )

    features = features.reset_index()

    execution_book = prepare_execution_book(
        book
    )

    return (
        features,
        execution_book,
    )


def run_frozen_simulator(
    features: pd.DataFrame,
    book: pd.DataFrame,
):
    """
    Reuse the repository's existing frozen simulator.

    Only its file-loading functions are temporarily replaced so
    that it consumes the reconstructed public sample in memory.
    No execution logic is duplicated here.
    """
    parameters = execution.load_parameters()

    original_load_features = (
        execution.load_features
    )

    original_load_book = (
        execution.load_book
    )

    try:
        execution.load_features = (
            lambda session_id: features.copy()
        )

        execution.load_book = (
            lambda session_id: book.copy()
        )

        trades, summary = (
            execution.simulate_session(
                session_id=SESSION_ID,
                label=LABEL,
                parameters=parameters,
            )
        )

    finally:
        execution.load_features = (
            original_load_features
        )

        execution.load_book = (
            original_load_book
        )

    return (
        trades,
        summary,
        parameters,
    )


def verify_reference_result(
    trades: pd.DataFrame,
    summary: dict,
) -> None:
    """
    Fail loudly if the reconstructed sample does not reproduce
    the frozen public reference result.
    """
    if (
        summary["completed_trades"]
        != EXPECTED_COMPLETED_TRADES
    ):
        raise AssertionError(
            "Completed-trade count mismatch: "
            f"{summary['completed_trades']} "
            f"!= {EXPECTED_COMPLETED_TRADES}"
        )

    if (
        summary["completed_long_trades"]
        != EXPECTED_LONG_TRADES
    ):
        raise AssertionError(
            "Long-trade count mismatch."
        )

    if (
        summary["completed_short_trades"]
        != EXPECTED_SHORT_TRADES
    ):
        raise AssertionError(
            "Short-trade count mismatch."
        )

    if not isclose(
        summary["mean_gross_return_bps"],
        EXPECTED_MEAN_GROSS_RETURN_BPS,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise AssertionError(
            "Mean gross return mismatch: "
            f"{summary['mean_gross_return_bps']}"
        )

    if not isclose(
        summary[
            "break_even_additional_cost_per_side_bps"
        ],
        EXPECTED_BREAK_EVEN_COST_PER_SIDE_BPS,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise AssertionError(
            "Break-even cost mismatch: "
            f"{summary['break_even_additional_cost_per_side_bps']}"
        )

    checks, all_pass = (
        execution.validate_completed_trades(
            trades
        )
    )

    if not all_pass:
        failed = [
            name
            for name, passed
            in checks.items()
            if not passed
        ]

        raise AssertionError(
            "Mechanical validation failed: "
            + ", ".join(failed)
        )


def main() -> None:
    print()
    print("=" * 72)
    print("PUBLIC HOLDOUT REPRODUCTION")
    print("=" * 72)

    print(
        f"Session:                  "
        f"{SESSION_ID}"
    )

    features, book = build_features()

    print(
        f"Feature observations:     "
        f"{len(features)}"
    )

    print(
        f"Valid raw book quotes:    "
        f"{len(book)}"
    )

    trades, summary, parameters = (
        run_frozen_simulator(
            features,
            book,
        )
    )

    verify_reference_result(
        trades,
        summary,
    )

    print()
    print("Frozen execution settings")
    print("-" * 72)

    print(
        f"Signal:                   "
        f"{execution.SIGNAL_COLUMN}"
    )

    print(
        f"Lower threshold:          "
        f"{parameters['lower_threshold']:.10f}"
    )

    print(
        f"Upper threshold:          "
        f"{parameters['upper_threshold']:.10f}"
    )

    print(
        f"Modeled latency:          "
        f"{parameters['reference_latency_ms']:.1f} ms"
    )

    print(
        f"Holding period:           "
        f"{parameters['holding_period_seconds']:.1f} s"
    )

    print()
    print("Reproduced holdout result")
    print("-" * 72)

    print(
        f"Qualifying signals:       "
        f"{summary['qualifying_signals']}"
    )

    print(
        f"Completed trades:         "
        f"{summary['completed_trades']}"
    )

    print(
        f"Long / short:             "
        f"{summary['completed_long_trades']} / "
        f"{summary['completed_short_trades']}"
    )

    print(
        f"Mean gross return:        "
        f"{summary['mean_gross_return_bps']:+.10f} "
        f"bps/trade"
    )

    print(
        f"Break-even extra cost:    "
        f"{summary['break_even_additional_cost_per_side_bps']:.10f} "
        f"bps/side"
    )

    print()
    print(
        "Mechanical validation:   PASS"
    )

    print(
        "Reference-result check:  PASS"
    )

    print()
    print(
        "This reproduces one 10-minute holdout session only; "
        "it does not establish production profitability or "
        "long-horizon robustness."
    )


if __name__ == "__main__":
    main()
