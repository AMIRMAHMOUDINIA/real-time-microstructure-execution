from pathlib import Path
import hashlib

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

SESSION_SUMMARY_FILE = (
    PROCESSED_DIR
    / "execution_summary_holdout.csv"
)

BOOTSTRAP_OUTPUT_FILE = (
    PROCESSED_DIR
    / "execution_stability_bootstrap_holdout.csv"
)

SESSION_OUTPUT_FILE = (
    PROCESSED_DIR
    / "execution_stability_sessions_holdout.csv"
)


# =============================================================================
# FROZEN INPUT HASHES
# =============================================================================

EXPECTED_TRADES_SHA256 = (
    "b5b76ddeddedcaac55d01ecf23e0a5ee6fa610085695604a3660fdec5e713b33"
)

EXPECTED_SESSION_SUMMARY_SHA256 = (
    "1cfbde4aa8001ffc33ad127e0bdef63b9367baae1594bad6cac7590b5b06eeae"
)


# =============================================================================
# DIAGNOSTIC SETTINGS
# =============================================================================

BLOCK_SECONDS = 30

BOOTSTRAP_REPETITIONS = 5000

RANDOM_SEED = 42

COST_GRID_PER_SIDE_BPS = [
    0.00,
    0.05,
    0.10,
]


# =============================================================================
# HASH HELPERS
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


def verify_frozen_inputs():
    checks = [
        (
            "Holdout trades",
            TRADES_FILE,
            EXPECTED_TRADES_SHA256,
        ),
        (
            "Holdout session summary",
            SESSION_SUMMARY_FILE,
            EXPECTED_SESSION_SUMMARY_SHA256,
        ),
    ]

    print("=" * 105)
    print("FROZEN HOLDOUT EXECUTION INPUT CHECK")
    print("=" * 105)

    for name, path, expected_hash in checks:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing frozen file:\n{path}"
            )

        actual_hash = sha256_file(path)

        print()
        print(name)

        print(
            f"  Expected: {expected_hash}"
        )

        print(
            f"  Actual:   {actual_hash}"
        )

        if actual_hash != expected_hash:
            raise RuntimeError(
                f"\n{name} has changed.\n"
                "Stability analysis aborted."
            )

    print()
    print(
        "Frozen input status: VERIFIED — UNCHANGED"
    )


# =============================================================================
# DATA
# =============================================================================

def load_trades():
    df = pd.read_csv(
        TRADES_FILE
    )

    df = df[
        df["status"] == "COMPLETED"
    ].copy()

    df["gross_return_bps"] = pd.to_numeric(
        df["gross_return_bps"],
        errors="coerce",
    )

    df["actual_entry_time_utc"] = pd.to_datetime(
        df["actual_entry_time_utc"],
        utc=True,
        format="mixed",
        errors="coerce",
    )

    df = df.dropna(
        subset=[
            "label",
            "gross_return_bps",
            "actual_entry_time_utc",
        ]
    ).copy()

    df = df.sort_values(
        [
            "label",
            "actual_entry_time_utc",
        ],
        kind="mergesort",
    ).reset_index(
        drop=True
    )

    return df


# =============================================================================
# BLOCK CONSTRUCTION
# =============================================================================

def build_session_blocks(df):
    session_blocks = {}

    for label, session_df in df.groupby(
        "label",
        sort=True,
    ):
        session_df = session_df.copy()

        session_df["block"] = (
            session_df[
                "actual_entry_time_utc"
            ]
            .dt.floor(
                f"{BLOCK_SECONDS}s"
            )
        )

        blocks = []

        for _, block_df in session_df.groupby(
            "block",
            sort=True,
        ):
            values = (
                block_df[
                    "gross_return_bps"
                ]
                .to_numpy(
                    dtype=float
                )
            )

            if len(values):
                blocks.append(
                    values
                )

        if len(blocks) == 0:
            raise RuntimeError(
                f"No valid blocks for {label}."
            )

        session_blocks[
            label
        ] = blocks

    return session_blocks


# =============================================================================
# ONE SESSION BLOCK RESAMPLE
# =============================================================================

def resample_session_mean(
    blocks,
    rng,
):
    number_of_blocks = len(
        blocks
    )

    selected_indices = rng.integers(
        low=0,
        high=number_of_blocks,
        size=number_of_blocks,
    )

    sampled_returns = []

    for index in selected_indices:
        sampled_returns.append(
            blocks[
                int(index)
            ]
        )

    sampled_returns = np.concatenate(
        sampled_returns
    )

    return float(
        sampled_returns.mean()
    )


# =============================================================================
# FIXED-SESSION BLOCK BOOTSTRAP
# =============================================================================

def fixed_session_block_bootstrap(
    session_blocks,
    rng,
):
    labels = sorted(
        session_blocks.keys()
    )

    distribution = np.empty(
        BOOTSTRAP_REPETITIONS,
        dtype=float,
    )

    for repetition in range(
        BOOTSTRAP_REPETITIONS
    ):
        session_means = []

        for label in labels:
            mean_return = (
                resample_session_mean(
                    blocks=session_blocks[
                        label
                    ],
                    rng=rng,
                )
            )

            session_means.append(
                mean_return
            )

        distribution[
            repetition
        ] = np.mean(
            session_means
        )

    return distribution


# =============================================================================
# HIERARCHICAL BOOTSTRAP
# =============================================================================

def hierarchical_bootstrap(
    session_blocks,
    rng,
):
    labels = np.array(
        sorted(
            session_blocks.keys()
        ),
        dtype=object,
    )

    number_of_sessions = len(
        labels
    )

    distribution = np.empty(
        BOOTSTRAP_REPETITIONS,
        dtype=float,
    )

    for repetition in range(
        BOOTSTRAP_REPETITIONS
    ):
        sampled_labels = rng.choice(
            labels,
            size=number_of_sessions,
            replace=True,
        )

        sampled_session_means = []

        for label in sampled_labels:
            mean_return = (
                resample_session_mean(
                    blocks=session_blocks[
                        label
                    ],
                    rng=rng,
                )
            )

            sampled_session_means.append(
                mean_return
            )

        distribution[
            repetition
        ] = np.mean(
            sampled_session_means
        )

    return distribution


# =============================================================================
# DISTRIBUTION SUMMARY
# =============================================================================

def summarize_distribution(
    distribution,
    cost_per_side_bps,
    method,
):
    net_distribution = (
        distribution
        - 2.0
        * cost_per_side_bps
    )

    return {
        "method":
            method,

        "bootstrap_repetitions":
            BOOTSTRAP_REPETITIONS,

        "block_seconds":
            BLOCK_SECONDS,

        "cost_per_side_bps":
            cost_per_side_bps,

        "round_trip_cost_bps":
            2.0
            * cost_per_side_bps,

        "bootstrap_mean_net_bps":
            float(
                np.mean(
                    net_distribution
                )
            ),

        "bootstrap_median_net_bps":
            float(
                np.median(
                    net_distribution
                )
            ),

        "ci_2_5_bps":
            float(
                np.quantile(
                    net_distribution,
                    0.025,
                )
            ),

        "ci_97_5_bps":
            float(
                np.quantile(
                    net_distribution,
                    0.975,
                )
            ),

        "probability_positive":
            float(
                np.mean(
                    net_distribution
                    > 0
                )
            ),
    }


# =============================================================================
# SESSION POINT ESTIMATES
# =============================================================================

def build_session_diagnostics(
    df
):
    rows = []

    session_means = (
        df.groupby(
            "label"
        )[
            "gross_return_bps"
        ]
        .mean()
        .sort_index()
    )

    full_equal_weight_mean = float(
        session_means.mean()
    )

    for label in session_means.index:
        remaining = session_means.drop(
            index=label
        )

        rows.append(
            {
                "label":
                    label,

                "session_mean_gross_bps":
                    float(
                        session_means.loc[
                            label
                        ]
                    ),

                "full_equal_weight_mean_bps":
                    full_equal_weight_mean,

                "leave_one_session_out_mean_bps":
                    float(
                        remaining.mean()
                    ),

                "leave_one_out_positive":
                    bool(
                        remaining.mean()
                        > 0
                    ),
            }
        )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# MAIN
# =============================================================================

def main():
    verify_frozen_inputs()

    df = load_trades()

    session_blocks = (
        build_session_blocks(
            df
        )
    )

    print()
    print("=" * 105)
    print("EXECUTION STABILITY DIAGNOSTIC")
    print("=" * 105)

    print(
        f"Completed trades:         "
        f"{len(df)}"
    )

    print(
        f"Holdout sessions:         "
        f"{df['label'].nunique()}"
    )

    print(
        f"Time block length:        "
        f"{BLOCK_SECONDS} seconds"
    )

    print(
        f"Bootstrap repetitions:    "
        f"{BOOTSTRAP_REPETITIONS}"
    )

    print(
        f"Random seed:              "
        f"{RANDOM_SEED}"
    )

    print()

    print(
        "Blocks per session:"
    )

    for label in sorted(
        session_blocks.keys()
    ):
        print(
            f"  {label}: "
            f"{len(session_blocks[label])}"
        )

    # =========================================================================
    # POINT ESTIMATES / LEAVE-ONE-SESSION-OUT
    # =========================================================================

    session_df = (
        build_session_diagnostics(
            df
        )
    )

    print()
    print("=" * 105)
    print("LEAVE-ONE-SESSION-OUT STABILITY")
    print("=" * 105)

    print(
        session_df
        .round(
            6
        )
        .to_string(
            index=False
        )
    )

    minimum_leave_one_out = float(
        session_df[
            "leave_one_session_out_mean_bps"
        ].min()
    )

    print()
    print(
        "Minimum leave-one-session-out "
        f"mean: {minimum_leave_one_out:+.6f} bps/trade"
    )

    # =========================================================================
    # BOOTSTRAPS
    # =========================================================================

    fixed_rng = np.random.default_rng(
        RANDOM_SEED
    )

    hierarchical_rng = np.random.default_rng(
        RANDOM_SEED
        + 1
    )

    fixed_distribution = (
        fixed_session_block_bootstrap(
            session_blocks=session_blocks,
            rng=fixed_rng,
        )
    )

    hierarchical_distribution = (
        hierarchical_bootstrap(
            session_blocks=session_blocks,
            rng=hierarchical_rng,
        )
    )

    rows = []

    for cost_per_side in (
        COST_GRID_PER_SIDE_BPS
    ):
        rows.append(
            summarize_distribution(
                distribution=(
                    fixed_distribution
                ),
                cost_per_side_bps=(
                    cost_per_side
                ),
                method=(
                    "fixed_session_30s_block_bootstrap"
                ),
            )
        )

        rows.append(
            summarize_distribution(
                distribution=(
                    hierarchical_distribution
                ),
                cost_per_side_bps=(
                    cost_per_side
                ),
                method=(
                    "hierarchical_session_plus_30s_block_bootstrap"
                ),
            )
        )

    bootstrap_df = pd.DataFrame(
        rows
    )

    print()
    print("=" * 105)
    print("BOOTSTRAP STABILITY RESULTS")
    print("=" * 105)

    display_columns = [
        "method",
        "cost_per_side_bps",
        "bootstrap_mean_net_bps",
        "bootstrap_median_net_bps",
        "ci_2_5_bps",
        "ci_97_5_bps",
        "probability_positive",
    ]

    print(
        bootstrap_df[
            display_columns
        ]
        .round(
            6
        )
        .to_string(
            index=False
        )
    )

    # =========================================================================
    # REFERENCE INTERPRETATION
    # =========================================================================

    gross_hierarchical = (
        bootstrap_df[
            (
                bootstrap_df[
                    "method"
                ]
                ==
                "hierarchical_session_plus_30s_block_bootstrap"
            )
            &
            (
                bootstrap_df[
                    "cost_per_side_bps"
                ]
                == 0.00
            )
        ]
        .iloc[0]
    )

    cost_005_hierarchical = (
        bootstrap_df[
            (
                bootstrap_df[
                    "method"
                ]
                ==
                "hierarchical_session_plus_30s_block_bootstrap"
            )
            &
            (
                bootstrap_df[
                    "cost_per_side_bps"
                ]
                == 0.05
            )
        ]
        .iloc[0]
    )

    cost_010_hierarchical = (
        bootstrap_df[
            (
                bootstrap_df[
                    "method"
                ]
                ==
                "hierarchical_session_plus_30s_block_bootstrap"
            )
            &
            (
                bootstrap_df[
                    "cost_per_side_bps"
                ]
                == 0.10
            )
        ]
        .iloc[0]
    )

    print()
    print("=" * 105)
    print("REFERENCE STABILITY INTERPRETATION")
    print("=" * 105)

    print(
        "Hierarchical bootstrap — gross:"
    )

    print(
        f"  Mean:          "
        f"{gross_hierarchical['bootstrap_mean_net_bps']:+.6f} bps"
    )

    print(
        f"  95% interval:  "
        f"[{gross_hierarchical['ci_2_5_bps']:+.6f}, "
        f"{gross_hierarchical['ci_97_5_bps']:+.6f}]"
    )

    print(
        f"  P(mean > 0):   "
        f"{gross_hierarchical['probability_positive']:.4f}"
    )

    print()

    print(
        "Hierarchical bootstrap — 0.05 bps/side:"
    )

    print(
        f"  Mean:          "
        f"{cost_005_hierarchical['bootstrap_mean_net_bps']:+.6f} bps"
    )

    print(
        f"  95% interval:  "
        f"[{cost_005_hierarchical['ci_2_5_bps']:+.6f}, "
        f"{cost_005_hierarchical['ci_97_5_bps']:+.6f}]"
    )

    print(
        f"  P(mean > 0):   "
        f"{cost_005_hierarchical['probability_positive']:.4f}"
    )

    print()

    print(
        "Hierarchical bootstrap — 0.10 bps/side:"
    )

    print(
        f"  Mean:          "
        f"{cost_010_hierarchical['bootstrap_mean_net_bps']:+.6f} bps"
    )

    print(
        f"  95% interval:  "
        f"[{cost_010_hierarchical['ci_2_5_bps']:+.6f}, "
        f"{cost_010_hierarchical['ci_97_5_bps']:+.6f}]"
    )

    print(
        f"  P(mean > 0):   "
        f"{cost_010_hierarchical['probability_positive']:.4f}"
    )

    # =========================================================================
    # SAVE
    # =========================================================================

    BOOTSTRAP_OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    bootstrap_df.to_csv(
        BOOTSTRAP_OUTPUT_FILE,
        index=False,
    )

    session_df.to_csv(
        SESSION_OUTPUT_FILE,
        index=False,
    )

    print()
    print("=" * 105)
    print("OUTPUT")
    print("=" * 105)

    print(
        "Bootstrap stability results:"
    )

    print(
        BOOTSTRAP_OUTPUT_FILE
    )

    print()

    print(
        "Session stability results:"
    )

    print(
        SESSION_OUTPUT_FILE
    )

    print()
    print(
        "IMPORTANT: this is a post-hoc uncertainty "
        "diagnostic, not a new strategy-selection test."
    )

    print(
        "No threshold, signal, latency, holding period, "
        "execution rule, or cost grid is modified."
    )

    print()

    print(
        "With only five holdout sessions, bootstrap intervals "
        "remain conditional on the observed market windows and "
        "must not be interpreted as guarantees across all future regimes."
    )


if __name__ == "__main__":
    main()