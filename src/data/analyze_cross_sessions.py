from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE = (
    PROCESSED_DIR
    / "cross_session_robustness_summary.csv"
)


# =============================================================================
# FROZEN ROBUSTNESS SESSIONS
#
# Failed / incomplete collections are intentionally excluded.
#
# In particular:
#     20260826_150217
#
# was interrupted by a WebSocket disconnect and is NOT part of the sample.
# =============================================================================

ROBUSTNESS_SESSIONS = [
    {
        "session_id": "20260824_135129",
        "label": "afternoon_1",
    },
    {
        "session_id": "20260825_084855",
        "label": "morning_1",
    },
    {
        "session_id": "20260826_085550",
        "label": "morning_2",
    },
    {
        "session_id": "20260826_144545",
        "label": "evening_1",
    },
    {
        "session_id": "20260826_151328",
        "label": "late_afternoon_1",
    },
]


# =============================================================================
# TIME HELPERS
# =============================================================================

def parse_session_start_utc(session_id):
    """
    Parse session IDs of the form:

        YYYYMMDD_HHMMSS

    Session IDs are generated in UTC by collect_live_session.py.
    """

    parsed = datetime.strptime(
        session_id,
        "%Y%m%d_%H%M%S",
    )

    return parsed.replace(
        tzinfo=timezone.utc
    )


def format_gap(hours):
    """
    Human-readable representation of a time gap.
    """

    if pd.isna(hours):
        return "FIRST"

    total_minutes = round(
        hours * 60
    )

    days = total_minutes // (24 * 60)

    remaining_minutes = (
        total_minutes % (24 * 60)
    )

    gap_hours = (
        remaining_minutes // 60
    )

    minutes = (
        remaining_minutes % 60
    )

    if days > 0:
        return (
            f"{days}d "
            f"{gap_hours}h "
            f"{minutes}m"
        )

    return (
        f"{gap_hours}h "
        f"{minutes}m"
    )


# =============================================================================
# ANALYSIS HELPERS
# =============================================================================

def safe_correlation(
    df,
    signal_col,
    target_col,
):
    """
    Pearson correlation using valid observations only.
    """

    subset = df[
        [
            signal_col,
            target_col,
        ]
    ].dropna()

    if len(subset) < 2:
        return float("nan")

    if (
        subset[
            signal_col
        ].nunique()
        < 2
    ):
        return float("nan")

    if (
        subset[
            target_col
        ].nunique()
        < 2
    ):
        return float("nan")

    return (
        subset[
            signal_col
        ].corr(
            subset[
                target_col
            ]
        )
    )


def bucket_spread(
    df,
    signal_col,
    target_col,
    min_trades=None,
):
    """
    Reproduce the frozen single-session quantile methodology.

    Book imbalance:
        All eligible seconds.

    Unrestricted trade flow:
        Zero-trade seconds must be removed BEFORE
        this function is called.

    Activity-filtered analyses:
        Keep observations satisfying the frozen
        thresholds of >=5, >=10 or >=25 trades/sec.
    """

    subset = df.copy()

    if min_trades is not None:
        subset = subset[
            subset["trades"]
            >= min_trades
        ].copy()

    subset = subset.dropna(
        subset=[
            signal_col,
            target_col,
        ]
    ).copy()

    if len(subset) < 10:
        return {
            "observations":
                len(subset),

            "buckets":
                0,

            "low_return":
                float("nan"),

            "high_return":
                float("nan"),

            "spread":
                float("nan"),
        }

    try:
        subset["bucket"] = pd.qcut(
            subset[
                signal_col
            ],
            q=5,
            labels=False,
            duplicates="drop",
        )

        subset["bucket"] = (
            subset["bucket"] + 1
        )

    except ValueError:
        return {
            "observations":
                len(subset),

            "buckets":
                0,

            "low_return":
                float("nan"),

            "high_return":
                float("nan"),

            "spread":
                float("nan"),
        }

    subset = subset.dropna(
        subset=["bucket"]
    )

    actual_buckets = (
        subset[
            "bucket"
        ].nunique()
    )

    if actual_buckets < 2:
        return {
            "observations":
                len(subset),

            "buckets":
                actual_buckets,

            "low_return":
                float("nan"),

            "high_return":
                float("nan"),

            "spread":
                float("nan"),
        }

    bucket_summary = (
        subset.groupby(
            "bucket"
        )
        .agg(
            mean_future_return_bps=(
                target_col,
                "mean",
            )
        )
    )

    lowest = (
        bucket_summary.iloc[0]
    )

    highest = (
        bucket_summary.iloc[-1]
    )

    low_return = (
        lowest[
            "mean_future_return_bps"
        ]
    )

    high_return = (
        highest[
            "mean_future_return_bps"
        ]
    )

    difference = (
        high_return
        - low_return
    )

    return {
        "observations":
            len(subset),

        "buckets":
            actual_buckets,

        "low_return":
            low_return,

        "high_return":
            high_return,

        "spread":
            difference,
    }


def mid_price_move_bps(df):
    """
    Full-session mid-price change in basis points.
    """

    mid = df[
        "mid_price"
    ].dropna()

    if len(mid) < 2:
        return float("nan")

    first_mid = (
        mid.iloc[0]
    )

    last_mid = (
        mid.iloc[-1]
    )

    return (
        (
            last_mid
            / first_mid
        )
        - 1.0
    ) * 10_000


# =============================================================================
# SESSION ANALYSIS
# =============================================================================

def analyze_session(
    session_id,
    label,
):
    """
    Calculate frozen robustness statistics for one session.
    """

    feature_file = (
        PROCESSED_DIR
        / (
            f"btcusdt_features_"
            f"{session_id}.csv"
        )
    )

    if not feature_file.exists():
        raise FileNotFoundError(
            f"Missing feature file "
            f"for session "
            f"{session_id}:\n"
            f"{feature_file}"
        )

    df = pd.read_csv(
        feature_file
    )

    start_utc = (
        parse_session_start_utc(
            session_id
        )
    )

    move_bps = (
        mid_price_move_bps(
            df
        )
    )

    # -------------------------------------------------------------------------
    # MATCH THE FROZEN SINGLE-SESSION METHODOLOGY
    # -------------------------------------------------------------------------

    trades_only = df[
        df["trades"] > 0
    ].copy()

    # -------------------------------------------------------------------------
    # CORRELATIONS
    # -------------------------------------------------------------------------

    book_corr_1s = (
        safe_correlation(
            df,
            "median_book_imbalance",
            "future_return_1s_bps",
        )
    )

    book_corr_5s = (
        safe_correlation(
            df,
            "median_book_imbalance",
            "future_return_5s_bps",
        )
    )

    flow_corr_1s = (
        safe_correlation(
            df,
            "trade_flow_imbalance",
            "future_return_1s_bps",
        )
    )

    flow_corr_5s = (
        safe_correlation(
            df,
            "trade_flow_imbalance",
            "future_return_5s_bps",
        )
    )

    # -------------------------------------------------------------------------
    # UNFILTERED BOOK BUCKETS
    # -------------------------------------------------------------------------

    book_1s = (
        bucket_spread(
            df,
            "median_book_imbalance",
            "future_return_1s_bps",
        )
    )

    book_5s = (
        bucket_spread(
            df,
            "median_book_imbalance",
            "future_return_5s_bps",
        )
    )

    # -------------------------------------------------------------------------
    # UNFILTERED TRADE-FLOW BUCKETS
    #
    # Zero-trade seconds excluded.
    # -------------------------------------------------------------------------

    flow_1s = (
        bucket_spread(
            trades_only,
            "trade_flow_imbalance",
            "future_return_1s_bps",
        )
    )

    flow_5s = (
        bucket_spread(
            trades_only,
            "trade_flow_imbalance",
            "future_return_5s_bps",
        )
    )

    # -------------------------------------------------------------------------
    # FROZEN ACTIVITY FILTERS
    # -------------------------------------------------------------------------

    book_1s_ge5 = (
        bucket_spread(
            df,
            "median_book_imbalance",
            "future_return_1s_bps",
            min_trades=5,
        )
    )

    book_1s_ge10 = (
        bucket_spread(
            df,
            "median_book_imbalance",
            "future_return_1s_bps",
            min_trades=10,
        )
    )

    book_1s_ge25 = (
        bucket_spread(
            df,
            "median_book_imbalance",
            "future_return_1s_bps",
            min_trades=25,
        )
    )

    flow_1s_ge5 = (
        bucket_spread(
            df,
            "trade_flow_imbalance",
            "future_return_1s_bps",
            min_trades=5,
        )
    )

    flow_1s_ge10 = (
        bucket_spread(
            df,
            "trade_flow_imbalance",
            "future_return_1s_bps",
            min_trades=10,
        )
    )

    flow_1s_ge25 = (
        bucket_spread(
            df,
            "trade_flow_imbalance",
            "future_return_1s_bps",
            min_trades=25,
        )
    )

    return {
        "session_id":
            session_id,

        "label":
            label,

        "session_start_utc":
            start_utc.isoformat(),

        "observations":
            len(df),

        "mid_price_move_bps":
            move_bps,

        "zero_trade_seconds":
            int(
                (
                    df["trades"] == 0
                ).sum()
            ),

        "seconds_ge5_trades":
            int(
                (
                    df["trades"] >= 5
                ).sum()
            ),

        "seconds_ge10_trades":
            int(
                (
                    df["trades"] >= 10
                ).sum()
            ),

        "seconds_ge25_trades":
            int(
                (
                    df["trades"] >= 25
                ).sum()
            ),

        "book_corr_1s":
            book_corr_1s,

        "book_corr_5s":
            book_corr_5s,

        "flow_corr_1s":
            flow_corr_1s,

        "flow_corr_5s":
            flow_corr_5s,

        "book_buckets_1s":
            book_1s[
                "buckets"
            ],

        "book_qhigh_minus_qlow_1s_bps":
            book_1s[
                "spread"
            ],

        "book_qhigh_minus_qlow_5s_bps":
            book_5s[
                "spread"
            ],

        "flow_buckets_1s":
            flow_1s[
                "buckets"
            ],

        "flow_qhigh_minus_qlow_1s_bps":
            flow_1s[
                "spread"
            ],

        "flow_qhigh_minus_qlow_5s_bps":
            flow_5s[
                "spread"
            ],

        "book_qspread_1s_ge5_bps":
            book_1s_ge5[
                "spread"
            ],

        "book_qspread_1s_ge10_bps":
            book_1s_ge10[
                "spread"
            ],

        "book_qspread_1s_ge25_bps":
            book_1s_ge25[
                "spread"
            ],

        "flow_qspread_1s_ge5_bps":
            flow_1s_ge5[
                "spread"
            ],

        "flow_qspread_1s_ge10_bps":
            flow_1s_ge10[
                "spread"
            ],

        "flow_qspread_1s_ge25_bps":
            flow_1s_ge25[
                "spread"
            ],
    }


# =============================================================================
# CROSS-SESSION HELPERS
# =============================================================================

def add_temporal_gaps(summary):
    """
    Add the time gap from the previous chronologically
    ordered robustness session.

    No observations are removed on the basis of this gap.
    It is purely a sampling-dependence diagnostic.
    """

    summary = (
        summary.copy()
    )

    summary[
        "session_start_utc_dt"
    ] = pd.to_datetime(
        summary[
            "session_start_utc"
        ],
        utc=True,
    )

    summary = (
        summary.sort_values(
            "session_start_utc_dt"
        )
        .reset_index(
            drop=True
        )
    )

    summary[
        "hours_since_previous"
    ] = (
        summary[
            "session_start_utc_dt"
        ]
        .diff()
        .dt.total_seconds()
        / 3600
    )

    summary[
        "gap_from_previous"
    ] = (
        summary[
            "hours_since_previous"
        ]
        .apply(
            format_gap
        )
    )

    summary = summary.drop(
        columns=[
            "session_start_utc_dt"
        ]
    )

    return summary


def print_metric_consistency(
    summary,
    metric,
    title,
):
    """
    Equal-weight each session rather than pooling seconds.
    """

    values = (
        summary[
            metric
        ]
        .dropna()
    )

    print()
    print("=" * 92)
    print(title)
    print("=" * 92)

    if len(values) == 0:
        print(
            "No valid session-level values."
        )
        return

    positive = int(
        (
            values > 0
        ).sum()
    )

    negative = int(
        (
            values < 0
        ).sum()
    )

    zero = int(
        (
            values == 0
        ).sum()
    )

    print(
        f"Sessions:                 "
        f"{len(values)}"
    )

    print(
        f"Positive sessions:        "
        f"{positive} / {len(values)}"
    )

    print(
        f"Negative sessions:        "
        f"{negative} / {len(values)}"
    )

    print(
        f"Zero sessions:            "
        f"{zero} / {len(values)}"
    )

    print(
        f"Equal-weighted mean:      "
        f"{values.mean():+.4f}"
    )

    print(
        f"Median across sessions:   "
        f"{values.median():+.4f}"
    )

    print(
        f"Minimum session value:    "
        f"{values.min():+.4f}"
    )

    print(
        f"Maximum session value:    "
        f"{values.max():+.4f}"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 92)

    print(
        "BTCUSDT CROSS-SESSION "
        "ROBUSTNESS ANALYSIS"
    )

    print("=" * 92)

    rows = []

    for session in ROBUSTNESS_SESSIONS:

        print(
            f"Reading "
            f"{session['label']}: "
            f"{session['session_id']}"
        )

        row = analyze_session(
            session_id=(
                session[
                    "session_id"
                ]
            ),
            label=(
                session[
                    "label"
                ]
            ),
        )

        rows.append(
            row
        )

    summary = pd.DataFrame(
        rows
    )

    summary = (
        add_temporal_gaps(
            summary
        )
    )

    # -------------------------------------------------------------------------
    # SAVE FULL-PRECISION RESULTS
    # -------------------------------------------------------------------------

    summary.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # -------------------------------------------------------------------------
    # TEMPORAL SAMPLING DIAGNOSTIC
    # -------------------------------------------------------------------------

    print()
    print("=" * 92)

    print(
        "TEMPORAL SAMPLING "
        "DIAGNOSTIC"
    )

    print("=" * 92)

    temporal_columns = [
        "label",
        "session_id",
        "session_start_utc",
        "gap_from_previous",
        "hours_since_previous",
    ]

    temporal_df = (
        summary[
            temporal_columns
        ].copy()
    )

    temporal_df[
        "hours_since_previous"
    ] = (
        temporal_df[
            "hours_since_previous"
        ].round(3)
    )

    print(
        temporal_df.to_string(
            index=False
        )
    )

    print()

    print(
        "The gap is reported for sampling "
        "diagnostics only."
    )

    print(
        "Nearby windows are not automatically "
        "treated as fully independent regimes."
    )

    # -------------------------------------------------------------------------
    # MAIN +1 SECOND COMPARISON
    # -------------------------------------------------------------------------

    display_columns = [
        "label",
        "session_id",
        "observations",
        "mid_price_move_bps",
        "book_corr_1s",
        "book_qhigh_minus_qlow_1s_bps",
        "flow_corr_1s",
        "flow_qhigh_minus_qlow_1s_bps",
    ]

    print()
    print("=" * 92)

    print(
        "SESSION-LEVEL COMPARISON"
    )

    print("=" * 92)

    display_df = (
        summary[
            display_columns
        ].copy()
    )

    numeric_columns = [
        "mid_price_move_bps",
        "book_corr_1s",
        "book_qhigh_minus_qlow_1s_bps",
        "flow_corr_1s",
        "flow_qhigh_minus_qlow_1s_bps",
    ]

    display_df[
        numeric_columns
    ] = (
        display_df[
            numeric_columns
        ].round(4)
    )

    print(
        display_df.to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # +5 SECOND COMPARISON
    # -------------------------------------------------------------------------

    print()
    print("=" * 92)

    print(
        "+5 SECOND COMPARISON"
    )

    print("=" * 92)

    five_second_columns = [
        "label",
        "book_corr_5s",
        "book_qhigh_minus_qlow_5s_bps",
        "flow_corr_5s",
        "flow_qhigh_minus_qlow_5s_bps",
    ]

    five_second_df = (
        summary[
            five_second_columns
        ].copy()
    )

    for col in (
        five_second_columns[1:]
    ):
        five_second_df[
            col
        ] = (
            five_second_df[
                col
            ].round(4)
        )

    print(
        five_second_df.to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # BOOK ACTIVITY FILTERS
    # -------------------------------------------------------------------------

    print()
    print("=" * 92)

    print(
        "BOOK IMBALANCE +1S: "
        "FROZEN ACTIVITY FILTERS"
    )

    print("=" * 92)

    book_activity_columns = [
        "label",
        "book_qspread_1s_ge5_bps",
        "book_qspread_1s_ge10_bps",
        "book_qspread_1s_ge25_bps",
    ]

    book_activity_df = (
        summary[
            book_activity_columns
        ].copy()
    )

    for col in (
        book_activity_columns[1:]
    ):
        book_activity_df[
            col
        ] = (
            book_activity_df[
                col
            ].round(4)
        )

    print(
        book_activity_df.to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # TRADE-FLOW ACTIVITY FILTERS
    # -------------------------------------------------------------------------

    print()
    print("=" * 92)

    print(
        "TRADE-FLOW IMBALANCE +1S: "
        "FROZEN ACTIVITY FILTERS"
    )

    print("=" * 92)

    flow_activity_columns = [
        "label",
        "flow_qspread_1s_ge5_bps",
        "flow_qspread_1s_ge10_bps",
        "flow_qspread_1s_ge25_bps",
    ]

    flow_activity_df = (
        summary[
            flow_activity_columns
        ].copy()
    )

    for col in (
        flow_activity_columns[1:]
    ):
        flow_activity_df[
            col
        ] = (
            flow_activity_df[
                col
            ].round(4)
        )

    print(
        flow_activity_df.to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # QUANTILE DIAGNOSTIC
    # -------------------------------------------------------------------------

    print()
    print("=" * 92)

    print(
        "QUANTILE CONSTRUCTION "
        "DIAGNOSTIC"
    )

    print("=" * 92)

    bucket_columns = [
        "label",
        "book_buckets_1s",
        "flow_buckets_1s",
    ]

    print(
        summary[
            bucket_columns
        ].to_string(
            index=False
        )
    )

    print()

    print(
        "Trade-flow quantiles use only "
        "seconds with trades > 0, matching "
        "the frozen single-session analysis."
    )

    print(
        "Fewer than five trade-flow buckets "
        "can occur when observations are tied "
        "at -1 or +1."
    )

    # -------------------------------------------------------------------------
    # CROSS-SESSION CONSISTENCY
    # -------------------------------------------------------------------------

    print_metric_consistency(
        summary,
        (
            "book_qhigh_minus_"
            "qlow_1s_bps"
        ),
        (
            "BOOK IMBALANCE: "
            "+1S Q-HIGH MINUS "
            "Q-LOW CONSISTENCY"
        ),
    )

    print_metric_consistency(
        summary,
        (
            "book_qhigh_minus_"
            "qlow_5s_bps"
        ),
        (
            "BOOK IMBALANCE: "
            "+5S Q-HIGH MINUS "
            "Q-LOW CONSISTENCY"
        ),
    )

    print_metric_consistency(
        summary,
        (
            "flow_qhigh_minus_"
            "qlow_1s_bps"
        ),
        (
            "TRADE FLOW: "
            "+1S Q-HIGH MINUS "
            "Q-LOW CONSISTENCY"
        ),
    )

    print_metric_consistency(
        summary,
        (
            "flow_qhigh_minus_"
            "qlow_5s_bps"
        ),
        (
            "TRADE FLOW: "
            "+5S Q-HIGH MINUS "
            "Q-LOW CONSISTENCY"
        ),
    )

    print_metric_consistency(
        summary,
        (
            "book_qspread_"
            "1s_ge25_bps"
        ),
        (
            "BOOK IMBALANCE: "
            "+1S Q-SPREAD WITH "
            ">=25 TRADES/SECOND"
        ),
    )

    # -------------------------------------------------------------------------
    # OUTPUT
    # -------------------------------------------------------------------------

    print()
    print("=" * 92)

    print(
        "OUTPUT"
    )

    print("=" * 92)

    print(
        f"Saved to: "
        f"{OUTPUT_FILE}"
    )

    print()
    print("=" * 92)

    print(
        "IMPORTANT"
    )

    print("=" * 92)

    print(
        "Sessions are equal-weighted experimental "
        "windows rather than pooled second-level "
        "observations.\n"
        "\n"
        "The signal definitions, horizons, "
        "quantile construction, and activity "
        "thresholds remain frozen.\n"
        "\n"
        "Temporal gaps are reported explicitly "
        "because closely spaced windows should "
        "not automatically be interpreted as "
        "fully independent market regimes.\n"
        "\n"
        "The failed WebSocket session "
        "20260826_150217 is excluded.\n"
        "\n"
        "With five valid windows, the analysis "
        "remains exploratory and is not evidence "
        "of executable alpha."
    )


if __name__ == "__main__":
    main()