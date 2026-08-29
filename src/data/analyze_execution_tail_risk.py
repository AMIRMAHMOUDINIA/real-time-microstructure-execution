from pathlib import Path
import hashlib
import math

import numpy as np
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

TRADES_FILE = (
    PROCESSED_DIR
    / "execution_trades_holdout.csv"
)

SUMMARY_FILE = (
    PROCESSED_DIR
    / "execution_tail_diagnostics_holdout.csv"
)

SESSION_DIRECTION_FILE = (
    PROCESSED_DIR
    / "execution_direction_diagnostics_holdout.csv"
)


# =============================================================================
# FROZEN INPUT HASH
# =============================================================================

EXPECTED_TRADES_SHA256 = (
    "b5b76ddeddedcaac55d01ecf23e0a5ee6fa610085695604a3660fdec5e713b33"
)


# =============================================================================
# HASH
# =============================================================================

def sha256_file(path):
    sha = hashlib.sha256()

    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            sha.update(chunk)

    return sha.hexdigest()


def verify_frozen_trades():
    if not TRADES_FILE.exists():
        raise FileNotFoundError(
            f"Missing frozen holdout trade file:\n{TRADES_FILE}"
        )

    actual_hash = sha256_file(
        TRADES_FILE
    )

    print("=" * 100)
    print("FROZEN HOLDOUT TRADE FILE CHECK")
    print("=" * 100)

    print(
        f"Expected SHA256: {EXPECTED_TRADES_SHA256}"
    )

    print(
        f"Actual SHA256:   {actual_hash}"
    )

    if actual_hash != EXPECTED_TRADES_SHA256:
        raise RuntimeError(
            "\nFrozen holdout trade file has changed.\n"
            "Diagnostic analysis aborted."
        )

    print(
        "Frozen trade status: VERIFIED — UNCHANGED"
    )


# =============================================================================
# HELPERS
# =============================================================================

def top_n_count(n, fraction):
    return max(
        1,
        int(
            math.ceil(
                n * fraction
            )
        ),
    )


def contribution_of_largest(
    returns,
    fraction,
):
    returns = (
        pd.Series(
            returns,
            dtype=float,
        )
        .dropna()
    )

    n = len(returns)

    if n == 0:
        return np.nan

    total = returns.sum()

    count = top_n_count(
        n,
        fraction,
    )

    largest = (
        returns
        .sort_values(
            ascending=False
        )
        .head(count)
        .sum()
    )

    if total == 0:
        return np.nan

    return float(
        largest / total
    )


def contribution_of_worst(
    returns,
    fraction,
):
    returns = (
        pd.Series(
            returns,
            dtype=float,
        )
        .dropna()
    )

    n = len(returns)

    if n == 0:
        return np.nan

    total = returns.sum()

    count = top_n_count(
        n,
        fraction,
    )

    worst = (
        returns
        .sort_values(
            ascending=True
        )
        .head(count)
        .sum()
    )

    if total == 0:
        return np.nan

    return float(
        worst / total
    )


def mean_without_top_fraction(
    returns,
    fraction,
):
    returns = (
        pd.Series(
            returns,
            dtype=float,
        )
        .dropna()
        .sort_values(
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )

    n = len(returns)

    if n == 0:
        return np.nan

    count = top_n_count(
        n,
        fraction,
    )

    remaining = (
        returns.iloc[
            count:
        ]
    )

    if len(remaining) == 0:
        return np.nan

    return float(
        remaining.mean()
    )


def trades_needed_for_positive_pnl_fraction(
    returns,
    target_fraction,
):
    positive = (
        pd.Series(
            returns,
            dtype=float,
        )
        .dropna()
    )

    positive = positive[
        positive > 0
    ]

    if len(positive) == 0:
        return 0

    positive = positive.sort_values(
        ascending=False
    )

    total_positive = positive.sum()

    cumulative = positive.cumsum()

    target = (
        total_positive
        * target_fraction
    )

    return int(
        (
            cumulative
            < target
        ).sum()
        + 1
    )


# =============================================================================
# LOAD
# =============================================================================

def load_completed_trades():
    df = pd.read_csv(
        TRADES_FILE
    )

    df = df[
        df["status"]
        == "COMPLETED"
    ].copy()

    df["gross_return_bps"] = pd.to_numeric(
        df["gross_return_bps"],
        errors="coerce",
    )

    df = df.dropna(
        subset=[
            "gross_return_bps",
        ]
    ).copy()

    return df


# =============================================================================
# MAIN
# =============================================================================

def main():
    verify_frozen_trades()

    df = load_completed_trades()

    returns = df[
        "gross_return_bps"
    ]

    n = len(returns)

    total_pnl = float(
        returns.sum()
    )

    positive = returns[
        returns > 0
    ]

    negative = returns[
        returns < 0
    ]

    zero = returns[
        returns == 0
    ]

    print()
    print("=" * 100)
    print("HOLDOUT EXECUTION RETURN DISTRIBUTION")
    print("=" * 100)

    print(
        f"Completed trades:         {n}"
    )

    print(
        f"Mean return:              {returns.mean():+.6f} bps"
    )

    print(
        f"Median return:            {returns.median():+.6f} bps"
    )

    print(
        f"Std deviation:            {returns.std():.6f} bps"
    )

    print(
        f"Minimum trade:            {returns.min():+.6f} bps"
    )

    print(
        f"Maximum trade:            {returns.max():+.6f} bps"
    )

    print(
        f"Total gross return:       {total_pnl:+.6f} bps"
    )

    print()

    print(
        f"Positive trades:          {len(positive)} "
        f"({len(positive) / n:.2%})"
    )

    print(
        f"Negative trades:          {len(negative)} "
        f"({len(negative) / n:.2%})"
    )

    print(
        f"Exactly zero trades:      {len(zero)} "
        f"({len(zero) / n:.2%})"
    )

    if len(positive):
        print(
            f"Mean winning trade:       {positive.mean():+.6f} bps"
        )

    if len(negative):
        print(
            f"Mean losing trade:        {negative.mean():+.6f} bps"
        )

    # =========================================================================
    # QUANTILES
    # =========================================================================

    quantiles = [
        0.01,
        0.05,
        0.10,
        0.25,
        0.50,
        0.75,
        0.90,
        0.95,
        0.99,
    ]

    print()
    print("=" * 100)
    print("RETURN QUANTILES")
    print("=" * 100)

    for q in quantiles:
        value = float(
            returns.quantile(
                q
            )
        )

        print(
            f"{q:>5.0%}: {value:+.6f} bps"
        )

    # =========================================================================
    # PNL CONCENTRATION
    # =========================================================================

    print()
    print("=" * 100)
    print("PNL CONCENTRATION")
    print("=" * 100)

    fractions = [
        0.01,
        0.05,
        0.10,
    ]

    rows = []

    for fraction in fractions:
        count = top_n_count(
            n,
            fraction,
        )

        top_contribution = (
            contribution_of_largest(
                returns,
                fraction,
            )
        )

        worst_contribution = (
            contribution_of_worst(
                returns,
                fraction,
            )
        )

        mean_without_top = (
            mean_without_top_fraction(
                returns,
                fraction,
            )
        )

        rows.append(
            {
                "fraction":
                    fraction,

                "trade_count":
                    count,

                "top_fraction_of_total_pnl":
                    top_contribution,

                "worst_fraction_of_total_pnl":
                    worst_contribution,

                "mean_return_without_top_bps":
                    mean_without_top,
            }
        )

        print()

        print(
            f"Top {fraction:.0%} = {count} trades"
        )

        print(
            f"  Share of total gross PnL: "
            f"{top_contribution:.4f}"
        )

        print(
            f"  Mean after removing top {fraction:.0%}: "
            f"{mean_without_top:+.6f} bps"
        )

        print(
            f"Worst {fraction:.0%} share of total PnL: "
            f"{worst_contribution:.4f}"
        )

    # =========================================================================
    # POSITIVE PNL CONCENTRATION
    # =========================================================================

    print()
    print("=" * 100)
    print("NUMBER OF WINNERS REQUIRED TO EXPLAIN POSITIVE PNL")
    print("=" * 100)

    for target_fraction in [
        0.50,
        0.80,
        0.90,
    ]:
        count = (
            trades_needed_for_positive_pnl_fraction(
                returns,
                target_fraction,
            )
        )

        print(
            f"{target_fraction:.0%} of positive PnL: "
            f"{count} trades"
        )

    # =========================================================================
    # DIRECTION
    # =========================================================================

    print()
    print("=" * 100)
    print("LONG VS SHORT")
    print("=" * 100)

    direction_summary = (
        df.groupby(
            "direction"
        )
        .agg(
            trades=(
                "gross_return_bps",
                "size",
            ),
            mean_return_bps=(
                "gross_return_bps",
                "mean",
            ),
            median_return_bps=(
                "gross_return_bps",
                "median",
            ),
            total_return_bps=(
                "gross_return_bps",
                "sum",
            ),
            positive_rate=(
                "gross_return_bps",
                lambda x:
                    (
                        x > 0
                    ).mean(),
            ),
        )
        .reset_index()
    )

    print(
        direction_summary
        .round(
            6
        )
        .to_string(
            index=False
        )
    )

    # =========================================================================
    # SESSION × DIRECTION
    # =========================================================================

    print()
    print("=" * 100)
    print("SESSION × DIRECTION")
    print("=" * 100)

    session_direction = (
        df.groupby(
            [
                "label",
                "direction",
            ]
        )
        .agg(
            trades=(
                "gross_return_bps",
                "size",
            ),
            mean_return_bps=(
                "gross_return_bps",
                "mean",
            ),
            median_return_bps=(
                "gross_return_bps",
                "median",
            ),
            total_return_bps=(
                "gross_return_bps",
                "sum",
            ),
            positive_rate=(
                "gross_return_bps",
                lambda x:
                    (
                        x > 0
                    ).mean(),
            ),
        )
        .reset_index()
    )

    print(
        session_direction
        .round(
            6
        )
        .to_string(
            index=False
        )
    )

    # =========================================================================
    # SESSION ROBUSTNESS TO REMOVING EXTREME WINNERS
    # =========================================================================

    print()
    print("=" * 100)
    print("SESSION MEANS AFTER REMOVING TOP 5% OF TRADES")
    print("=" * 100)

    session_rows = []

    for label, session_df in df.groupby(
        "label"
    ):
        session_returns = session_df[
            "gross_return_bps"
        ]

        original_mean = float(
            session_returns.mean()
        )

        trimmed_mean = (
            mean_without_top_fraction(
                session_returns,
                0.05,
            )
        )

        session_rows.append(
            {
                "label":
                    label,

                "trades":
                    len(
                        session_returns
                    ),

                "original_mean_bps":
                    original_mean,

                "mean_without_top_5pct_bps":
                    trimmed_mean,

                "remains_positive":
                    bool(
                        trimmed_mean > 0
                    ),
            }
        )

    session_robustness = pd.DataFrame(
        session_rows
    )

    print(
        session_robustness
        .round(
            6
        )
        .to_string(
            index=False
        )
    )

    # =========================================================================
    # SAVE
    # =========================================================================

    concentration_df = pd.DataFrame(
        rows
    )

    concentration_df[
        "total_completed_trades"
    ] = n

    concentration_df[
        "overall_mean_return_bps"
    ] = float(
        returns.mean()
    )

    concentration_df[
        "overall_total_return_bps"
    ] = total_pnl

    SUMMARY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    concentration_df.to_csv(
        SUMMARY_FILE,
        index=False,
    )

    session_direction.to_csv(
        SESSION_DIRECTION_FILE,
        index=False,
    )

    print()
    print("=" * 100)
    print("OUTPUT")
    print("=" * 100)

    print(
        "Tail diagnostics:"
    )

    print(
        SUMMARY_FILE
    )

    print()

    print(
        "Session-direction diagnostics:"
    )

    print(
        SESSION_DIRECTION_FILE
    )

    print()
    print(
        "IMPORTANT: this analysis is diagnostic only."
    )

    print(
        "No execution parameter, threshold, signal, "
        "latency, cost assumption, or trading rule "
        "is changed by these results."
    )


if __name__ == "__main__":
    main()