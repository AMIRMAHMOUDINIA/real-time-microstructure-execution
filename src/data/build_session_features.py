from pathlib import Path
import argparse

import numpy as np
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# SESSION DISCOVERY
# =============================================================================

def find_latest_complete_session():

    book_files = sorted(
        RAW_DIR.glob("btcusdt_book_*.csv")
    )

    if not book_files:
        raise FileNotFoundError(
            f"No book files found in {RAW_DIR}"
        )

    complete_sessions = []

    for book_file in book_files:

        session_id = (
            book_file.stem
            .replace(
                "btcusdt_book_",
                "",
            )
        )

        trade_file = (
            RAW_DIR
            / f"btcusdt_trades_{session_id}.csv"
        )

        if trade_file.exists():

            complete_sessions.append(
                (
                    session_id,
                    book_file,
                    trade_file,
                )
            )

    if not complete_sessions:
        raise FileNotFoundError(
            "No complete book/trade session found."
        )

    return complete_sessions[-1]


def get_session_files(session_id=None):

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
            f"Missing book file:\n{book_file}"
        )

    if not trade_file.exists():
        raise FileNotFoundError(
            f"Missing trade file:\n{trade_file}"
        )

    return (
        session_id,
        book_file,
        trade_file,
    )


# =============================================================================
# RAW DATA LOADING
# =============================================================================

def parse_datetime_column(
    df,
    column,
):

    if column not in df.columns:
        return

    df[column] = pd.to_datetime(
        df[column],
        format="mixed",
        utc=True,
        errors="coerce",
    )


def convert_numeric_columns(
    df,
    columns,
):

    for column in columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )


def load_raw_data(
    book_file,
    trade_file,
):

    book = pd.read_csv(
        book_file
    )

    trades = pd.read_csv(
        trade_file
    )

    # -------------------------------------------------------------------------
    # Robust timestamp parsing
    # -------------------------------------------------------------------------

    parse_datetime_column(
        book,
        "received_at_utc",
    )

    parse_datetime_column(
        trades,
        "received_at_utc",
    )

    parse_datetime_column(
        trades,
        "event_time_utc",
    )

    parse_datetime_column(
        trades,
        "trade_time_utc",
    )

    # -------------------------------------------------------------------------
    # Numeric book fields
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
    # Numeric trade fields
    # -------------------------------------------------------------------------

    convert_numeric_columns(
        trades,
        [
            "trade_id",
            "price",
            "quantity",
            "quote_value",
        ],
    )

    return (
        book,
        trades,
    )


# =============================================================================
# BOOK FEATURES
# =============================================================================

def build_book_features(book):

    book = book.copy()

    book = book.dropna(
        subset=[
            "received_at_utc"
        ]
    )

    book = book.sort_values(
        "received_at_utc"
    )

    book = book.set_index(
        "received_at_utc"
    )

    book_features = (
        book.resample("1s")
        .agg(
            mid_price=(
                "mid_price",
                "last",
            ),
            mean_spread=(
                "spread",
                "mean",
            ),
            median_spread=(
                "spread",
                "median",
            ),
            mean_book_imbalance=(
                "imbalance",
                "mean",
            ),
            median_book_imbalance=(
                "imbalance",
                "median",
            ),
            book_updates=(
                "update_id",
                "count",
            ),
            mean_bid_quantity=(
                "bid_quantity",
                "mean",
            ),
            mean_ask_quantity=(
                "ask_quantity",
                "mean",
            ),
        )
    )

    return book_features


# =============================================================================
# TRADE FEATURES
# =============================================================================

def build_trade_features(trades):

    trades = trades.copy()

    trades = trades.dropna(
        subset=[
            "received_at_utc"
        ]
    )

    trades = trades.sort_values(
        "received_at_utc"
    )

    is_buy = (
        trades["aggressor_side"]
        == "BUY"
    )

    is_sell = (
        trades["aggressor_side"]
        == "SELL"
    )

    trades[
        "buy_quantity_component"
    ] = np.where(
        is_buy,
        trades["quantity"],
        0.0,
    )

    trades[
        "sell_quantity_component"
    ] = np.where(
        is_sell,
        trades["quantity"],
        0.0,
    )

    trades[
        "buy_notional_component"
    ] = np.where(
        is_buy,
        trades["quote_value"],
        0.0,
    )

    trades[
        "sell_notional_component"
    ] = np.where(
        is_sell,
        trades["quote_value"],
        0.0,
    )

    trades = trades.set_index(
        "received_at_utc"
    )

    trade_features = (
        trades.resample("1s")
        .agg(
            trades=(
                "trade_id",
                "count",
            ),
            total_quantity=(
                "quantity",
                "sum",
            ),
            buy_quantity=(
                "buy_quantity_component",
                "sum",
            ),
            sell_quantity=(
                "sell_quantity_component",
                "sum",
            ),
            total_notional=(
                "quote_value",
                "sum",
            ),
            buy_notional=(
                "buy_notional_component",
                "sum",
            ),
            sell_notional=(
                "sell_notional_component",
                "sum",
            ),
            mean_trade_size=(
                "quantity",
                "mean",
            ),
        )
    )

    trade_features[
        "trade_flow_imbalance"
    ] = np.where(
        trade_features[
            "total_quantity"
        ] > 0,
        (
            trade_features[
                "buy_quantity"
            ]
            - trade_features[
                "sell_quantity"
            ]
        )
        /
        trade_features[
            "total_quantity"
        ],
        0.0,
    )

    trade_features[
        "notional_flow_imbalance"
    ] = np.where(
        trade_features[
            "total_notional"
        ] > 0,
        (
            trade_features[
                "buy_notional"
            ]
            - trade_features[
                "sell_notional"
            ]
        )
        /
        trade_features[
            "total_notional"
        ],
        0.0,
    )

    return trade_features


# =============================================================================
# COMBINE ONE-SECOND FEATURES
# =============================================================================

def combine_features(
    book_features,
    trade_features,
):

    features = (
        book_features.join(
            trade_features,
            how="outer",
        )
        .sort_index()
    )

    trade_columns = [
        "trades",
        "total_quantity",
        "buy_quantity",
        "sell_quantity",
        "total_notional",
        "buy_notional",
        "sell_notional",
        "mean_trade_size",
        "trade_flow_imbalance",
        "notional_flow_imbalance",
    ]

    for column in trade_columns:

        features[column] = (
            features[column]
            .fillna(0.0)
        )

    features[
        "trades"
    ] = (
        features[
            "trades"
        ]
        .astype(int)
    )

    features[
        "book_updates"
    ] = (
        features[
            "book_updates"
        ]
        .fillna(0)
        .astype(int)
    )

    features[
        "mid_price"
    ] = (
        features[
            "mid_price"
        ]
        .ffill()
    )

    return features


# =============================================================================
# FUTURE RETURN TARGETS
# =============================================================================

def add_future_targets(features):

    features = features.copy()

    features[
        "future_mid_1s"
    ] = (
        features[
            "mid_price"
        ]
        .shift(-1)
    )

    features[
        "future_mid_5s"
    ] = (
        features[
            "mid_price"
        ]
        .shift(-5)
    )

    features[
        "future_return_1s_bps"
    ] = (
        (
            features[
                "future_mid_1s"
            ]
            / features[
                "mid_price"
            ]
        )
        - 1.0
    ) * 10_000

    features[
        "future_return_5s_bps"
    ] = (
        (
            features[
                "future_mid_5s"
            ]
            / features[
                "mid_price"
            ]
        )
        - 1.0
    ) * 10_000

    return features


# =============================================================================
# SUMMARY
# =============================================================================

def print_summary(features):

    print()
    print("=" * 72)
    print("ONE-SECOND FEATURE DATASET")
    print("=" * 72)

    print(
        f"Observations:               "
        f"{len(features)}"
    )

    print(
        f"Total book updates:         "
        f"{int(features['book_updates'].sum())}"
    )

    print(
        f"Total trades:               "
        f"{int(features['trades'].sum())}"
    )

    print()
    print("=" * 72)
    print("FEATURE SUMMARY")
    print("=" * 72)

    summary_columns = [
        "median_book_imbalance",
        "trade_flow_imbalance",
        "mean_spread",
        "book_updates",
        "trades",
        "future_return_1s_bps",
        "future_return_5s_bps",
    ]

    print(
        features[
            summary_columns
        ].describe()
    )

    print()
    print("=" * 72)
    print("EXPLORATORY CORRELATIONS")
    print("=" * 72)

    book_1s = (
        features[
            "median_book_imbalance"
        ]
        .corr(
            features[
                "future_return_1s_bps"
            ]
        )
    )

    flow_1s = (
        features[
            "trade_flow_imbalance"
        ]
        .corr(
            features[
                "future_return_1s_bps"
            ]
        )
    )

    book_5s = (
        features[
            "median_book_imbalance"
        ]
        .corr(
            features[
                "future_return_5s_bps"
            ]
        )
    )

    flow_5s = (
        features[
            "trade_flow_imbalance"
        ]
        .corr(
            features[
                "future_return_5s_bps"
            ]
        )
    )

    print(
        f"Book imbalance vs +1s return:  "
        f"{book_1s:+.4f}"
    )

    print(
        f"Trade flow vs +1s return:      "
        f"{flow_1s:+.4f}"
    )

    print(
        f"Book imbalance vs +5s return:  "
        f"{book_5s:+.4f}"
    )

    print(
        f"Trade flow vs +5s return:      "
        f"{flow_5s:+.4f}"
    )

    print()
    print(
        "IMPORTANT: these correlations come from one market session only."
    )

    print(
        "They are exploratory diagnostics, not evidence of a predictive trading signal."
    )


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
            "Specific session ID YYYYMMDD_HHMMSS. "
            "If omitted, use latest complete session."
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

    print(
        f"Building features for session: "
        f"{session_id}"
    )

    book, trades = load_raw_data(
        book_file,
        trade_file,
    )

    book_features = (
        build_book_features(
            book
        )
    )

    trade_features = (
        build_trade_features(
            trades
        )
    )

    features = (
        combine_features(
            book_features,
            trade_features,
        )
    )

    features = (
        add_future_targets(
            features
        )
    )

    output_file = (
        PROCESSED_DIR
        / f"btcusdt_features_{session_id}.csv"
    )

    # IMPORTANT:
    # Preserve the frozen downstream schema.
    features.to_csv(
        output_file,
        index=True,
        index_label="received_at_utc",
    )

    print_summary(
        features
    )

    print()
    print("=" * 72)
    print("OUTPUT")
    print("=" * 72)

    print(
        f"Feature dataset saved to: "
        f"data/processed/"
        f"btcusdt_features_{session_id}.csv"
    )


if __name__ == "__main__":
    main()