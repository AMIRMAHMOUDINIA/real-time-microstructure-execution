from pathlib import Path
import hashlib

import numpy as np
import pandas as pd

import simulate_execution_development as engine
import evaluate_execution_development as dev_eval


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

EXECUTION_PROTOCOL_FILE = (
    PROJECT_ROOT
    / "EXECUTION_PROTOCOL.md"
)

PARAMETER_FILE = (
    PROCESSED_DIR
    / "execution_parameters.csv"
)

ENGINE_FILE = (
    PROJECT_ROOT
    / "src"
    / "data"
    / "simulate_execution_development.py"
)

DEVELOPMENT_EVALUATOR_FILE = (
    PROJECT_ROOT
    / "src"
    / "data"
    / "evaluate_execution_development.py"
)

DEVELOPMENT_SESSION_LATENCY_FILE = (
    PROCESSED_DIR
    / "execution_session_latency_development.csv"
)

DEVELOPMENT_LATENCY_FILE = (
    PROCESSED_DIR
    / "execution_latency_sensitivity_development.csv"
)

DEVELOPMENT_COST_FILE = (
    PROCESSED_DIR
    / "execution_cost_sensitivity_development.csv"
)


# =============================================================================
# HOLDOUT OUTPUT FILES
# =============================================================================

TRADES_OUTPUT_FILE = (
    PROCESSED_DIR
    / "execution_trades_holdout.csv"
)

SUMMARY_OUTPUT_FILE = (
    PROCESSED_DIR
    / "execution_summary_holdout.csv"
)

SESSION_LATENCY_OUTPUT_FILE = (
    PROCESSED_DIR
    / "execution_session_latency_holdout.csv"
)

LATENCY_OUTPUT_FILE = (
    PROCESSED_DIR
    / "execution_latency_sensitivity_holdout.csv"
)

COST_OUTPUT_FILE = (
    PROCESSED_DIR
    / "execution_cost_sensitivity_holdout.csv"
)

COMPARISON_OUTPUT_FILE = (
    PROCESSED_DIR
    / "execution_development_vs_holdout.csv"
)


# =============================================================================
# FROZEN HASHES
# =============================================================================

EXPECTED_PROTOCOL_SHA256 = (
    "ef534c27856907e45ac871db8d4d499ddb338ffe114169f3ea2ee796f8265d6e"
)

EXPECTED_PARAMETER_SHA256 = (
    "1fc3aa7cd92408161c41c067d4329d2f93953361637fbd143b03f2c0a1e2298b"
)

EXPECTED_ENGINE_SHA256 = (
    "7a24cbe27a2f7e92e2d935ed22cb7de7f764f457a1e96f1f868fc1266ce39e23"
)

EXPECTED_DEVELOPMENT_EVALUATOR_SHA256 = (
    "a1e7335beb0890a2f7bffc8f94ba0b0147f8f0d7d5b7fb9382aaebec9f08c053"
)

EXPECTED_DEVELOPMENT_SESSION_LATENCY_SHA256 = (
    "cb1def97b2b756d3e91961029cf9888ff0fa030531f6bf9bc31e3d4a11fc43b5"
)

EXPECTED_DEVELOPMENT_LATENCY_SHA256 = (
    "82e8900be4afc022adc5b1069190b37ddb708f8c5eff0ab35269eb209b6b8790"
)

EXPECTED_DEVELOPMENT_COST_SHA256 = (
    "f553468e766651c9c4718dbeb1a27fe3bcf409db05136d4f7167a681d77025a0"
)


# =============================================================================
# PRE-REGISTERED HOLDOUT SAMPLE
# =============================================================================

HOLDOUT_SESSIONS = [
    {
        "session_id": "20260826_202754",
        "label": "holdout_1",
    },
    {
        "session_id": "20260827_083158",
        "label": "holdout_2",
    },
    {
        "session_id": "20260827_195947",
        "label": "holdout_3",
    },
    {
        "session_id": "20260828_153334",
        "label": "holdout_4",
    },
    {
        "session_id": "20260829_091754",
        "label": "holdout_5",
    },
]


# =============================================================================
# FROZEN SENSITIVITY GRIDS
# =============================================================================

LATENCY_GRID_MS = [
    0.0,
    50.0,
    100.0,
    250.0,
    500.0,
    1000.0,
]

REFERENCE_LATENCY_MS = 100.0

COST_GRID_PER_SIDE_BPS = [
    0.00,
    0.05,
    0.10,
    0.25,
    0.50,
    1.00,
    2.00,
    5.00,
]


# =============================================================================
# HASH HELPERS
# =============================================================================

def sha256_file(path):
    sha = hashlib.sha256()

    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            sha.update(
                chunk
            )

    return sha.hexdigest()


def verify_frozen_research_checkpoint():
    files = [
        (
            "Execution protocol",
            EXECUTION_PROTOCOL_FILE,
            EXPECTED_PROTOCOL_SHA256,
        ),
        (
            "Execution parameters",
            PARAMETER_FILE,
            EXPECTED_PARAMETER_SHA256,
        ),
        (
            "Execution engine",
            ENGINE_FILE,
            EXPECTED_ENGINE_SHA256,
        ),
        (
            "Development evaluator",
            DEVELOPMENT_EVALUATOR_FILE,
            EXPECTED_DEVELOPMENT_EVALUATOR_SHA256,
        ),
        (
            "Development session-latency results",
            DEVELOPMENT_SESSION_LATENCY_FILE,
            EXPECTED_DEVELOPMENT_SESSION_LATENCY_SHA256,
        ),
        (
            "Development latency results",
            DEVELOPMENT_LATENCY_FILE,
            EXPECTED_DEVELOPMENT_LATENCY_SHA256,
        ),
        (
            "Development cost results",
            DEVELOPMENT_COST_FILE,
            EXPECTED_DEVELOPMENT_COST_SHA256,
        ),
    ]

    print("=" * 110)
    print("PRE-HOLDOUT FROZEN RESEARCH CHECKPOINT")
    print("=" * 110)

    for name, path, expected_hash in files:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing frozen research file:\n"
                f"{path}"
            )

        actual_hash = sha256_file(
            path
        )

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
                "HOLDOUT EXECUTION ABORTED."
            )

    print()
    print(
        "Frozen research checkpoint: VERIFIED — UNCHANGED"
    )


# =============================================================================
# COST FRONTIER
# =============================================================================

def build_holdout_cost_frontier(
    session_latency_df
):
    rows = []

    for latency_ms in LATENCY_GRID_MS:
        latency_sessions = (
            session_latency_df[
                session_latency_df[
                    "latency_ms"
                ]
                == latency_ms
            ]
            .copy()
        )

        if len(latency_sessions) != len(
            HOLDOUT_SESSIONS
        ):
            raise RuntimeError(
                f"Expected {len(HOLDOUT_SESSIONS)} "
                f"holdout sessions at "
                f"{latency_ms:.0f} ms, "
                f"found {len(latency_sessions)}."
            )

        gross_session_means = pd.to_numeric(
            latency_sessions[
                "mean_gross_return_bps"
            ],
            errors="coerce",
        )

        for cost_per_side in (
            COST_GRID_PER_SIDE_BPS
        ):
            round_trip_cost = (
                2.0
                * cost_per_side
            )

            net_session_means = (
                gross_session_means
                - round_trip_cost
            )

            rows.append(
                {
                    "latency_ms":
                        float(
                            latency_ms
                        ),

                    "additional_cost_per_side_bps":
                        float(
                            cost_per_side
                        ),

                    "additional_round_trip_cost_bps":
                        float(
                            round_trip_cost
                        ),

                    "equal_weight_mean_net_return_bps":
                        float(
                            net_session_means.mean()
                        ),

                    "equal_weight_median_net_return_bps":
                        float(
                            net_session_means.median()
                        ),

                    "positive_sessions":
                        int(
                            (
                                net_session_means
                                > 0
                            ).sum()
                        ),

                    "sessions":
                        int(
                            len(
                                net_session_means
                            )
                        ),
                }
            )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# REFERENCE TRADE FILE
# =============================================================================

def build_reference_trade_file(
    base_parameters
):
    parameters = dict(
        base_parameters
    )

    parameters[
        "reference_latency_ms"
    ] = REFERENCE_LATENCY_MS

    frames = []

    for session in HOLDOUT_SESSIONS:
        trades, _ = engine.simulate_session(
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
            parameters=parameters,
        )

        if len(trades):
            frames.append(
                trades
            )

    if not frames:
        raise RuntimeError(
            "No holdout reference trades generated."
        )

    return pd.concat(
        frames,
        ignore_index=True,
    )


# =============================================================================
# DEVELOPMENT VS HOLDOUT COMPARISON
# =============================================================================

def build_development_holdout_comparison(
    holdout_latency_df
):
    development_latency_df = pd.read_csv(
        DEVELOPMENT_LATENCY_FILE
    )

    rows = []

    for latency_ms in LATENCY_GRID_MS:
        dev_matches = (
            development_latency_df[
                development_latency_df[
                    "latency_ms"
                ]
                == latency_ms
            ]
        )

        hold_matches = (
            holdout_latency_df[
                holdout_latency_df[
                    "latency_ms"
                ]
                == latency_ms
            ]
        )

        if (
            len(dev_matches) != 1
            or len(hold_matches) != 1
        ):
            raise RuntimeError(
                f"Could not uniquely match "
                f"{latency_ms:.0f} ms results."
            )

        dev = dev_matches.iloc[0]
        hold = hold_matches.iloc[0]

        development_mean = float(
            dev[
                "equal_weight_mean_session_return_bps"
            ]
        )

        holdout_mean = float(
            hold[
                "equal_weight_mean_session_return_bps"
            ]
        )

        if development_mean != 0:
            retention_ratio = (
                holdout_mean
                / development_mean
            )
        else:
            retention_ratio = np.nan

        rows.append(
            {
                "latency_ms":
                    float(
                        latency_ms
                    ),

                "development_equal_weight_mean_bps":
                    development_mean,

                "holdout_equal_weight_mean_bps":
                    holdout_mean,

                "holdout_minus_development_bps":
                    (
                        holdout_mean
                        - development_mean
                    ),

                "holdout_to_development_ratio":
                    retention_ratio,

                "development_positive_sessions":
                    int(
                        dev[
                            "positive_sessions"
                        ]
                    ),

                "holdout_positive_sessions":
                    int(
                        hold[
                            "positive_sessions"
                        ]
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
    # =========================================================================
    # VERIFY ALL FROZEN PRE-HOLDOUT RESEARCH
    # =========================================================================

    verify_frozen_research_checkpoint()

    # Frozen engine performs its own independent
    # protocol + parameter verification.
    engine.verify_frozen_inputs()

    base_parameters = (
        engine.load_parameters()
    )

    # Confirm this holdout evaluator uses exactly
    # the same frozen grids as the development evaluator.
    if list(dev_eval.LATENCY_GRID_MS) != LATENCY_GRID_MS:
        raise RuntimeError(
            "Latency grid differs from frozen "
            "development evaluator."
        )

    if (
        list(
            dev_eval.COST_GRID_PER_SIDE_BPS
        )
        != COST_GRID_PER_SIDE_BPS
    ):
        raise RuntimeError(
            "Cost grid differs from frozen "
            "development evaluator."
        )

    print()
    print("=" * 110)
    print("ONE-SHOT PRE-REGISTERED HOLDOUT EXECUTION EVALUATION")
    print("=" * 110)

    print(
        "Primary signal:          "
        "median_book_imbalance"
    )

    print(
        "Thresholds:              "
        f"{base_parameters['lower_threshold']:+.10f} / "
        f"{base_parameters['upper_threshold']:+.10f}"
    )

    print(
        "Holding period:          "
        f"{base_parameters['holding_period_seconds']:.1f} s"
    )

    print(
        "Reference latency:       "
        f"{REFERENCE_LATENCY_MS:.0f} ms"
    )

    print(
        "Execution:               "
        "aggressive bid/ask"
    )

    print(
        "Position overlap:        "
        "not allowed"
    )

    print()

    print(
        "Latency grid (ms):        "
        + ", ".join(
            f"{x:.0f}"
            for x in LATENCY_GRID_MS
        )
    )

    print(
        "Cost grid / side (bps):   "
        + ", ".join(
            f"{x:.2f}"
            for x
            in COST_GRID_PER_SIDE_BPS
        )
    )

    print()
    print(
        "THIS IS THE FIRST CONFIRMATORY EXECUTION "
        "EVALUATION OF THE FIVE HOLDOUT SESSIONS."
    )

    # =========================================================================
    # HOLDOUT LATENCY EVALUATION
    # =========================================================================

    all_session_rows = []
    latency_summary_rows = []

    for latency_ms in LATENCY_GRID_MS:
        print()
        print("-" * 110)

        print(
            f"HOLDOUT LATENCY: "
            f"{latency_ms:.0f} ms"
        )

        print("-" * 110)

        session_rows = []
        completed_trade_frames = []

        for session in HOLDOUT_SESSIONS:
            row, completed = (
                dev_eval.evaluate_session_latency(
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
                    base_parameters=(
                        base_parameters
                    ),
                    latency_ms=(
                        latency_ms
                    ),
                )
            )

            session_rows.append(
                row
            )

            all_session_rows.append(
                row
            )

            completed_trade_frames.append(
                completed
            )

            print(
                f"{row['label']:<12} "
                f"trades={row['completed_trades']:>3}  "
                f"mean={row['mean_gross_return_bps']:+.4f} bps  "
                f"BE/side={row['break_even_cost_per_side_bps']:+.4f}  "
                f"mechanics=PASS"
            )

        latency_summary = (
            dev_eval.summarize_latency(
                session_rows=session_rows,
                all_completed_trades=(
                    completed_trade_frames
                ),
                latency_ms=latency_ms,
            )
        )

        latency_summary_rows.append(
            latency_summary
        )

        print()

        print(
            "Equal-weight session mean: "
            f"{latency_summary['equal_weight_mean_session_return_bps']:+.4f} "
            "bps/trade"
        )

        print(
            "Positive sessions:          "
            f"{latency_summary['positive_sessions']} / "
            f"{latency_summary['sessions']}"
        )

        print(
            "Break-even cost / side:     "
            f"{latency_summary['equal_weight_break_even_cost_per_side_bps']:+.4f} "
            "bps"
        )

    session_latency_df = pd.DataFrame(
        all_session_rows
    )

    latency_df = pd.DataFrame(
        latency_summary_rows
    )

    # =========================================================================
    # COST FRONTIER
    # =========================================================================

    cost_df = build_holdout_cost_frontier(
        session_latency_df
    )

    # =========================================================================
    # REFERENCE 100 MS TRADE FILE
    # =========================================================================

    reference_trades = (
        build_reference_trade_file(
            base_parameters
        )
    )

    reference_summary = (
        session_latency_df[
            session_latency_df[
                "latency_ms"
            ]
            == REFERENCE_LATENCY_MS
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    if len(reference_summary) != len(
        HOLDOUT_SESSIONS
    ):
        raise RuntimeError(
            "Reference holdout session count is incorrect."
        )

    # =========================================================================
    # LATENCY SUMMARY
    # =========================================================================

    print()
    print("=" * 110)
    print("HOLDOUT LATENCY SENSITIVITY — EQUAL-WEIGHT SESSION RESULTS")
    print("=" * 110)

    latency_display = latency_df[
        [
            "latency_ms",
            "total_completed_trades",
            "equal_weight_mean_session_return_bps",
            "equal_weight_median_session_return_bps",
            "positive_sessions",
            "pooled_positive_trade_rate",
            "equal_weight_break_even_cost_per_side_bps",
        ]
    ].copy()

    numeric_columns = (
        latency_display
        .select_dtypes(
            include=[
                np.number
            ]
        )
        .columns
    )

    latency_display[
        numeric_columns
    ] = latency_display[
        numeric_columns
    ].round(
        4
    )

    print(
        latency_display.to_string(
            index=False
        )
    )

    # =========================================================================
    # REFERENCE 100 MS SESSION RESULTS
    # =========================================================================

    print()
    print("=" * 110)
    print("PRIMARY HOLDOUT EXECUTION ENDPOINT — 100 MS")
    print("=" * 110)

    reference_display = reference_summary[
        [
            "label",
            "completed_trades",
            "completed_long_trades",
            "completed_short_trades",
            "mean_gross_return_bps",
            "median_gross_return_bps",
            "positive_trade_rate",
            "maximum_drawdown_bps",
            "break_even_cost_per_side_bps",
            "mean_entry_quote_wait_ms",
            "p95_entry_quote_wait_ms",
        ]
    ].copy()

    numeric_columns = (
        reference_display
        .select_dtypes(
            include=[
                np.number
            ]
        )
        .columns
    )

    reference_display[
        numeric_columns
    ] = reference_display[
        numeric_columns
    ].round(
        4
    )

    print(
        reference_display.to_string(
            index=False
        )
    )

    # =========================================================================
    # REFERENCE 100 MS COST FRONTIER
    # =========================================================================

    print()
    print("=" * 110)
    print("REFERENCE 100 MS — HOLDOUT COST FRONTIER")
    print("=" * 110)

    reference_cost_df = (
        cost_df[
            cost_df[
                "latency_ms"
            ]
            == REFERENCE_LATENCY_MS
        ]
        .copy()
    )

    reference_cost_display = (
        reference_cost_df[
            [
                "additional_cost_per_side_bps",
                "additional_round_trip_cost_bps",
                "equal_weight_mean_net_return_bps",
                "equal_weight_median_net_return_bps",
                "positive_sessions",
            ]
        ]
        .copy()
    )

    numeric_columns = (
        reference_cost_display
        .select_dtypes(
            include=[
                np.number
            ]
        )
        .columns
    )

    reference_cost_display[
        numeric_columns
    ] = reference_cost_display[
        numeric_columns
    ].round(
        4
    )

    print(
        reference_cost_display.to_string(
            index=False
        )
    )

    # =========================================================================
    # PRIMARY ENDPOINT
    # =========================================================================

    reference_latency_row = (
        latency_df[
            latency_df[
                "latency_ms"
            ]
            == REFERENCE_LATENCY_MS
        ]
        .iloc[0]
    )

    reference_mean = float(
        reference_latency_row[
            "equal_weight_mean_session_return_bps"
        ]
    )

    reference_median = float(
        reference_latency_row[
            "equal_weight_median_session_return_bps"
        ]
    )

    reference_break_even = float(
        reference_latency_row[
            "equal_weight_break_even_cost_per_side_bps"
        ]
    )

    reference_positive_sessions = int(
        reference_latency_row[
            "positive_sessions"
        ]
    )

    print()
    print("=" * 110)
    print("CONFIRMATORY HOLDOUT EXECUTION RESULT")
    print("=" * 110)

    print(
        f"Reference latency:                 "
        f"{REFERENCE_LATENCY_MS:.0f} ms"
    )

    print(
        f"Equal-weight gross return:         "
        f"{reference_mean:+.4f} bps/trade"
    )

    print(
        f"Equal-weight median session mean:  "
        f"{reference_median:+.4f} bps/trade"
    )

    print(
        f"Positive holdout sessions:         "
        f"{reference_positive_sessions} / "
        f"{len(HOLDOUT_SESSIONS)}"
    )

    print(
        f"Break-even additional cost:        "
        f"{reference_break_even:+.4f} bps/side"
    )

    if reference_mean > 0:
        level_2_status = "PASS"
    else:
        level_2_status = "FAIL"

    print(
        f"Execution Level 2 status:          "
        f"{level_2_status}"
    )

    # =========================================================================
    # COST ROBUSTNESS STATUS
    # =========================================================================

    positive_cost_rows = (
        reference_cost_df[
            reference_cost_df[
                "equal_weight_mean_net_return_bps"
            ]
            > 0
        ]
        .copy()
    )

    if len(positive_cost_rows):
        maximum_positive_grid_cost = float(
            positive_cost_rows[
                "additional_cost_per_side_bps"
            ].max()
        )
    else:
        maximum_positive_grid_cost = np.nan

    print()
    print(
        "Largest pre-specified grid cost with "
        "positive mean:"
    )

    if np.isnan(
        maximum_positive_grid_cost
    ):
        print(
            "  None"
        )
    else:
        print(
            f"  {maximum_positive_grid_cost:.2f} "
            "bps/side"
        )

    # =========================================================================
    # DEVELOPMENT VS HOLDOUT
    # =========================================================================

    comparison_df = (
        build_development_holdout_comparison(
            latency_df
        )
    )

    print()
    print("=" * 110)
    print("DEVELOPMENT VS HOLDOUT EXECUTION")
    print("=" * 110)

    comparison_display = comparison_df.copy()

    numeric_columns = (
        comparison_display
        .select_dtypes(
            include=[
                np.number
            ]
        )
        .columns
    )

    comparison_display[
        numeric_columns
    ] = comparison_display[
        numeric_columns
    ].round(
        4
    )

    print(
        comparison_display.to_string(
            index=False
        )
    )

    # =========================================================================
    # SAVE OUTPUT
    # =========================================================================

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    reference_trades.to_csv(
        TRADES_OUTPUT_FILE,
        index=False,
    )

    reference_summary.to_csv(
        SUMMARY_OUTPUT_FILE,
        index=False,
    )

    session_latency_df.to_csv(
        SESSION_LATENCY_OUTPUT_FILE,
        index=False,
    )

    latency_df.to_csv(
        LATENCY_OUTPUT_FILE,
        index=False,
    )

    cost_df.to_csv(
        COST_OUTPUT_FILE,
        index=False,
    )

    comparison_df.to_csv(
        COMPARISON_OUTPUT_FILE,
        index=False,
    )

    # =========================================================================
    # OUTPUT
    # =========================================================================

    print()
    print("=" * 110)
    print("OUTPUT")
    print("=" * 110)

    print(
        "Reference holdout trades:"
    )

    print(
        TRADES_OUTPUT_FILE
    )

    print()

    print(
        "Reference holdout session summary:"
    )

    print(
        SUMMARY_OUTPUT_FILE
    )

    print()

    print(
        "Holdout session-by-latency results:"
    )

    print(
        SESSION_LATENCY_OUTPUT_FILE
    )

    print()

    print(
        "Holdout latency sensitivity:"
    )

    print(
        LATENCY_OUTPUT_FILE
    )

    print()

    print(
        "Holdout latency × cost frontier:"
    )

    print(
        COST_OUTPUT_FILE
    )

    print()

    print(
        "Development-vs-holdout execution comparison:"
    )

    print(
        COMPARISON_OUTPUT_FILE
    )

    print()
    print("=" * 110)
    print("INTERPRETATION GUARDRAIL")
    print("=" * 110)

    print(
        "The holdout sessions were not used to choose "
        "the signal, thresholds, holding period, latency grid, "
        "cost grid, or execution rules."
    )

    print()

    print(
        "A positive Level 2 result means the signal survived "
        "the modeled aggressive bid/ask execution assumptions."
    )

    print()

    print(
        "It does NOT establish production profitability because "
        "real exchange fees, market impact, order acknowledgements, "
        "network latency, fill uncertainty, and longer market regimes "
        "remain outside this experiment."
    )


if __name__ == "__main__":
    main()