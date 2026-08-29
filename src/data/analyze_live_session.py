from pathlib import Path
import argparse

import pandas as pd


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"


# =============================================================================
# SESSION DISCOVERY
# =============================================================================

def find_latest_complete_session():
    """
    Find the latest session for which both the book and trade CSV exist.
    """

    book_files = sorted(
        RAW_DIR.glob("btcusdt_book_*.csv")
    )

    if not book_files:
        raise FileNotFoundError(
            f"No book files found in:\n{RAW_DIR}"
        )

    candidates = []

    for book_file in book_files:
        session_id = (
            book_file.stem
            .replace("btcusdt_book_", "")
        )

        trade_file = (
            RAW_DIR
            / f"btcusdt_trades_{session_id}.csv"
        )

        if trade_file.exists():
            candidates.append(
                (
                    session_id,
                    book_file,
                    trade_file,
                )
            )

    if not candidates:
        raise FileNotFoundError(
            "No complete matching book/trade session found."
        )

    return candidates[-1]


def get_session_files(session_id=None):
    """
    Return the requested session or the latest complete session.
    """

    if session_id is None:
        return find_latest_complete_session()

    book_file = (
        RAW_DIR
        / f"btcusdt_book_{session_id}.csv"
    )

    trade_file = (
        RAW_DIR
        / f"btcusdt_trades_{session_id}.csv"
    )

    if not book_file.exists():
        raise FileNotFoundError(
            f"Book file not found:\n{book_file}"
        )

    if not trade_file.exists():
        raise FileNotFoundError(
            f"Trade file not found:\n{trade_file}"
        )

    return (
        session_id,
        book_file,
        trade_file,
    )


# =============================================================================
# DATA LOADING
# =============================================================================

def parse_datetime_column(
    df,
    column,
):
    """
    Parse ISO timestamps robustly.

    format='mixed' handles ISO strings that may differ only in fractional
    second precision. This avoids pandas leaving the entire column as strings.
    """

    if column not in df.columns:
        return

    df[column] = pd.to_datetime(
        df[column],
        utc=True,
        format="mixed",
        errors="coerce",
    )


def convert_numeric_columns(
    df,
    columns,
):
    """
    Explicit numeric conversion for analysis fields.
    """

    for column in columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )


def load_data(
    book_file,
    trade_file,
):
    """
    Load and sanitize raw session data.

    No signal definitions or analytical methodology are changed here.
    """

    book = pd.read_csv(
        book_file
    )

    trade = pd.read_csv(
        trade_file
    )

    # -------------------------------------------------------------------------
    # TIMESTAMPS
    # -------------------------------------------------------------------------

    parse_datetime_column(
        book,
        "received_at_utc",
    )

    parse_datetime_column(
        trade,
        "received_at_utc",
    )

    parse_datetime_column(
        trade,
        "event_time_utc",
    )

    parse_datetime_column(
        trade,
        "trade_time_utc",
    )

    # -------------------------------------------------------------------------
    # NUMERIC BOOK FIELDS
    # -------------------------------------------------------------------------

    convert_numeric_columns(
        book,
        [
            "update_id",
            "bid_price",
            "bid_quantity",
            "ask_price",
            "ask_quantity",
            "mid_price",
            "spread",
            "imbalance",
        ],
    )

    # -------------------------------------------------------------------------
    # NUMERIC TRADE FIELDS
    # -------------------------------------------------------------------------

    convert_numeric_columns(
        trade,
        [
            "trade_id",
            "price",
            "quantity",
            "quote_value",
        ],
    )

    return (
        book,
        trade,
    )


# =============================================================================
# HELPERS
# =============================================================================

def safe_duration_seconds(
    df,
    column="received_at_utc",
):
    """
    Duration between the first and last valid recorded timestamp.
    """

    if column not in df.columns:
        return float("nan")

    timestamps = (
        df[column]
        .dropna()
    )

    if len(timestamps) < 2:
        return float("nan")

    duration = (
        timestamps.iloc[-1]
        - timestamps.iloc[0]
    )

    return (
        duration.total_seconds()
    )


def safe_vwap(trade):
    """
    Quantity-weighted average trade price.
    """

    valid = trade.dropna(
        subset=[
            "quantity",
            "quote_value",
        ]
    )

    total_quantity = (
        valid["quantity"].sum()
    )

    if total_quantity <= 0:
        return float("nan")

    return (
        valid["quote_value"].sum()
        / total_quantity
    )


# =============================================================================
# ANALYSIS
# =============================================================================

def analyze_session(
    session_id,
    book_file,
    trade_file,
):

    book, trade = load_data(
        book_file,
        trade_file,
    )

    print()
    print("=" * 72)
    print("BTCUSDT LIVE SESSION ANALYSIS")
    print("=" * 72)

    print(
        f"Session ID:  {session_id}"
    )

    print(
        f"Book file:   "
        f"{book_file.relative_to(PROJECT_ROOT)}"
    )

    print(
        f"Trade file:  "
        f"{trade_file.relative_to(PROJECT_ROOT)}"
    )

    # =========================================================================
    # DATASET SIZE
    # =========================================================================

    print()
    print("=" * 72)
    print("DATASET SIZE")
    print("=" * 72)

    print(
        f"Book updates:               "
        f"{len(book)}"
    )

    print(
        f"Trades:                     "
        f"{len(trade)}"
    )

    # =========================================================================
    # TRADE DIRECTION
    # =========================================================================

    buy_trades = trade[
        trade["aggressor_side"] == "BUY"
    ]

    sell_trades = trade[
        trade["aggressor_side"] == "SELL"
    ]

    buy_count = len(
        buy_trades
    )

    sell_count = len(
        sell_trades
    )

    total_directional_trades = (
        buy_count
        + sell_count
    )

    if total_directional_trades > 0:

        trade_count_imbalance = (
            buy_count
            - sell_count
        ) / total_directional_trades

    else:

        trade_count_imbalance = float(
            "nan"
        )

    print()
    print("=" * 72)
    print("TRADE DIRECTION")
    print("=" * 72)

    print(
        f"BUY-aggressor trades:       "
        f"{buy_count}"
    )

    print(
        f"SELL-aggressor trades:      "
        f"{sell_count}"
    )

    print(
        f"Trade-count imbalance:      "
        f"{trade_count_imbalance:+.4f}"
    )

    # =========================================================================
    # TRADE VOLUME
    # =========================================================================

    buy_volume = (
        buy_trades[
            "quantity"
        ].sum()
    )

    sell_volume = (
        sell_trades[
            "quantity"
        ].sum()
    )

    total_volume = (
        buy_volume
        + sell_volume
    )

    if total_volume > 0:

        trade_flow_imbalance = (
            buy_volume
            - sell_volume
        ) / total_volume

    else:

        trade_flow_imbalance = float(
            "nan"
        )

    print()
    print("=" * 72)
    print("TRADE VOLUME")
    print("=" * 72)

    print(
        f"Buy volume:                 "
        f"{buy_volume:.6f} BTC"
    )

    print(
        f"Sell volume:                "
        f"{sell_volume:.6f} BTC"
    )

    print(
        f"Total traded volume:        "
        f"{total_volume:.6f} BTC"
    )

    print(
        f"Trade-flow imbalance:       "
        f"{trade_flow_imbalance:+.4f}"
    )

    # =========================================================================
    # TRADED NOTIONAL
    # =========================================================================

    buy_notional = (
        buy_trades[
            "quote_value"
        ].sum()
    )

    sell_notional = (
        sell_trades[
            "quote_value"
        ].sum()
    )

    total_notional = (
        buy_notional
        + sell_notional
    )

    if total_notional > 0:

        notional_flow_imbalance = (
            buy_notional
            - sell_notional
        ) / total_notional

    else:

        notional_flow_imbalance = float(
            "nan"
        )

    print()
    print("=" * 72)
    print("TRADED NOTIONAL")
    print("=" * 72)

    print(
        f"Buy notional:               "
        f"{buy_notional:,.2f} USDT"
    )

    print(
        f"Sell notional:              "
        f"{sell_notional:,.2f} USDT"
    )

    print(
        f"Total notional:             "
        f"{total_notional:,.2f} USDT"
    )

    print(
        f"Notional-flow imbalance:    "
        f"{notional_flow_imbalance:+.4f}"
    )

    # =========================================================================
    # TRADE PRICE STATISTICS
    # =========================================================================

    valid_prices = (
        trade[
            "price"
        ]
        .dropna()
    )

    if len(valid_prices) >= 1:

        first_trade_price = (
            valid_prices.iloc[0]
        )

        last_trade_price = (
            valid_prices.iloc[-1]
        )

        price_change = (
            last_trade_price
            - first_trade_price
        )

        price_change_bps = (
            (
                last_trade_price
                / first_trade_price
            )
            - 1.0
        ) * 10_000

    else:

        first_trade_price = float(
            "nan"
        )

        last_trade_price = float(
            "nan"
        )

        price_change = float(
            "nan"
        )

        price_change_bps = float(
            "nan"
        )

    vwap = safe_vwap(
        trade
    )

    print()
    print("=" * 72)
    print("TRADE PRICE STATISTICS")
    print("=" * 72)

    print(
        f"First trade price:          "
        f"{first_trade_price:.2f}"
    )

    print(
        f"Last trade price:           "
        f"{last_trade_price:.2f}"
    )

    print(
        f"Price change:               "
        f"{price_change:+.2f} USDT"
    )

    print(
        f"Price change:               "
        f"{price_change_bps:+.3f} bps"
    )

    print(
        f"VWAP:                       "
        f"{vwap:.3f}"
    )

    # =========================================================================
    # TRADE SIZE STATISTICS
    # =========================================================================

    trade_sizes = (
        trade[
            "quantity"
        ]
        .dropna()
    )

    print()
    print("=" * 72)
    print("TRADE SIZE STATISTICS")
    print("=" * 72)

    print(
        f"Mean trade size:            "
        f"{trade_sizes.mean():.6f} BTC"
    )

    print(
        f"Median trade size:          "
        f"{trade_sizes.median():.6f} BTC"
    )

    print(
        f"Largest trade:              "
        f"{trade_sizes.max():.6f} BTC"
    )

    # =========================================================================
    # TOP-OF-BOOK SPREAD
    # =========================================================================

    spread = (
        book[
            "spread"
        ]
        .dropna()
    )

    print()
    print("=" * 72)
    print("TOP-OF-BOOK SPREAD")
    print("=" * 72)

    print(
        f"Median spread:              "
        f"{spread.median():.4f} USDT"
    )

    print(
        f"Mean spread:                "
        f"{spread.mean():.4f} USDT"
    )

    print(
        f"95th percentile spread:     "
        f"{spread.quantile(0.95):.4f} USDT"
    )

    print(
        f"99th percentile spread:     "
        f"{spread.quantile(0.99):.4f} USDT"
    )

    print(
        f"Maximum spread:             "
        f"{spread.max():.4f} USDT"
    )

    # =========================================================================
    # TOP-OF-BOOK IMBALANCE
    # =========================================================================

    imbalance = (
        book[
            "imbalance"
        ]
        .dropna()
    )

    print()
    print("=" * 72)
    print("TOP-OF-BOOK IMBALANCE")
    print("=" * 72)

    print(
        f"Mean imbalance:             "
        f"{imbalance.mean():+.4f}"
    )

    print(
        f"Median imbalance:           "
        f"{imbalance.median():+.4f}"
    )

    print(
        f"Minimum imbalance:          "
        f"{imbalance.min():+.4f}"
    )

    print(
        f"Maximum imbalance:          "
        f"{imbalance.max():+.4f}"
    )

    # =========================================================================
    # SESSION TIMING
    # =========================================================================

    book_duration = (
        safe_duration_seconds(
            book
        )
    )

    trade_duration = (
        safe_duration_seconds(
            trade
        )
    )

    print()
    print("=" * 72)
    print("SESSION TIMING")
    print("=" * 72)

    print(
        f"Observed book duration:     "
        f"{book_duration:.3f} seconds"
    )

    print(
        f"Observed trade duration:    "
        f"{trade_duration:.3f} seconds"
    )

    # =========================================================================
    # SESSION SUMMARY
    # =========================================================================

    print()
    print("=" * 72)
    print("SESSION SUMMARY")
    print("=" * 72)

    print(
        f"Trade-flow imbalance:       "
        f"{trade_flow_imbalance:+.4f}"
    )

    print(
        f"Book imbalance (median):    "
        f"{imbalance.median():+.4f}"
    )

    print(
        f"Price move:                 "
        f"{price_change_bps:+.3f} bps"
    )

    print(
        f"VWAP:                       "
        f"{vwap:.3f}"
    )

    print(
        f"Total volume:               "
        f"{total_volume:.6f} BTC"
    )

    print(
        f"Total notional:             "
        f"{total_notional:,.2f} USDT"
    )

    print()
    print("=" * 72)
    print("ANALYSIS COMPLETE")
    print("=" * 72)


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--session-id",
        type=str,
        default=None,
        help=(
            "Specific session ID in YYYYMMDD_HHMMSS format. "
            "If omitted, analyze the latest complete session."
        ),
    )

    args = parser.parse_args()

    (
        session_id,
        book_file,
        trade_file,
    ) = get_session_files(
        args.session_id
    )

    analyze_session(
        session_id,
        book_file,
        trade_file,
    )


if __name__ == "__main__":
    main()