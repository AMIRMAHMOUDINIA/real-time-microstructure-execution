from pathlib import Path
import hashlib

import numpy as np
import pandas as pd

import simulate_execution_development as engine


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

EXECUTION_PROTOCOL_FILE = PROJECT_ROOT / "EXECUTION_PROTOCOL.md"
PARAMETER_FILE = PROCESSED_DIR / "execution_parameters.csv"

ENGINE_FILE = (
    PROJECT_ROOT
    / "src"
    / "data"
    / "simulate_execution_development.py"
)

LATENCY_OUTPUT_FILE = (
    PROCESSED_DIR
    / "execution_latency_sensitivity_development.csv"
)

COST_OUTPUT_FILE = (
    PROCESSED_DIR
    / "execution_cost_sensitivity_development.csv"
)

SESSION_LATENCY_OUTPUT_FILE = (
    PROCESSED_DIR
    / "execution_session_latency_development.csv"
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


# =============================================================================
# FROZEN DEVELOPMENT SAMPLE
# =============================================================================

DEVELOPMENT_SESSIONS = [
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
# FROZEN EXECUTION SENSITIVITY GRIDS
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
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            sha.update(chunk)

    return sha.hexdigest()


def verify_frozen_inputs():
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
    ]

    print("=" * 105)
    print("FROZEN EXECUTION RESEARCH CHECKPOINT")
    print("=" * 105)

    for name, path, expected_hash in files:
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
                "Development evaluation aborted."
            )

    print()
    print(
        "Frozen checkpoint status: VERIFIED — UNCHANGED"
    )


# =============================================================================
# DRAW DOWN
# =============================================================================

def maximum_drawdown_bps(returns):
    returns = pd.Series(
        returns,
        dtype=float,
    ).dropna()

    if len(returns) == 0:
        return np.nan

    cumulative = returns.cumsum()

    running_max = cumulative.cummax()

    drawdown = (
        cumulative
        - running_max
    )

    return float(
        drawdown.min()
    )


# =============================================================================
# MECHANICAL VALIDATION FOR ARBITRARY LATENCY
# =============================================================================

def validate_latency_trades(
    trades,
    latency_ms,
):
    if len(trades) == 0:
        return False

    completed = trades[
        trades["status"] == "COMPLETED"
    ].copy()

    if len(completed) == 0:
        return False

    timestamp_columns = [
        "bucket_start_utc",
        "decision_time_utc",
        "target_entry_time_utc",
        "actual_entry_time_utc",
        "target_exit_time_utc",
        "actual_exit_time_utc",
    ]

    for column in timestamp_columns:
        completed[column] = pd.to_datetime(
            completed[column],
            utc=True,
            format="mixed",
            errors="coerce",
        )

    checks = []

    checks.append(
        (
            completed["decision_time_utc"]
            ==
            (
                completed["bucket_start_utc"]
                + pd.Timedelta(seconds=1)
            )
        ).all()
    )

    checks.append(
        (
            completed["target_entry_time_utc"]
            ==
            (
                completed["decision_time_utc"]
                + pd.Timedelta(
                    milliseconds=latency_ms
                )
            )
        ).all()
    )

    checks.append(
        (
            completed["actual_entry_time_utc"]
            >= completed["target_entry_time_utc"]
        ).all()
    )

    checks.append(
        (
            completed["target_exit_time_utc"]
            ==
            (
                completed["actual_entry_time_utc"]
                + pd.Timedelta(seconds=1)
            )
        ).all()
    )

    checks.append(
        (
            completed["actual_exit_time_utc"]
            >= completed["target_exit_time_utc"]
        ).all()
    )

    checks.append(
        (
            completed["decision_to_entry_ms"]
            >= latency_ms
        ).all()
    )

    checks.append(
        (
            completed["holding_time_actual_seconds"]
            >= 1.0
        ).all()
    )

    no_overlap = True

    for _, session_df in completed.groupby(
        "session_id"
    ):
        session_df = session_df.sort_values(
            "actual_entry_time_utc"
        ).reset_index(
            drop=True
        )

        for i in range(
            1,
            len(session_df),
        ):
            previous_exit = session_df.loc[
                i - 1,
                "actual_exit_time_utc",
            ]

            current_entry = session_df.loc[
                i,
                "actual_entry_time_utc",
            ]

            if current_entry < previous_exit:
                no_overlap = False
                break

        if not no_overlap:
            break

    checks.append(
        no_overlap
    )

    return bool(
        all(checks)
    )


# =============================================================================
# ONE SESSION / ONE LATENCY
# =============================================================================

def evaluate_session_latency(
    session_id,
    label,
    base_parameters,
    latency_ms,
):
    parameters = dict(
        base_parameters
    )

    parameters[
        "reference_latency_ms"
    ] = float(
        latency_ms
    )

    trades, summary = engine.simulate_session(
        session_id=session_id,
        label=label,
        parameters=parameters,
    )

    mechanical_pass = validate_latency_trades(
        trades=trades,
        latency_ms=latency_ms,
    )

    if not mechanical_pass:
        raise RuntimeError(
            f"Mechanical validation failed for "
            f"{label} at {latency_ms:.0f} ms."
        )

    completed = trades[
        trades["status"] == "COMPLETED"
    ].copy()

    returns = pd.to_numeric(
        completed[
            "gross_return_bps"
        ],
        errors="coerce",
    ).dropna()

    long_returns = pd.to_numeric(
        completed.loc[
            completed["direction"] == "LONG",
            "gross_return_bps",
        ],
        errors="coerce",
    ).dropna()

    short_returns = pd.to_numeric(
        completed.loc[
            completed["direction"] == "SHORT",
            "gross_return_bps",
        ],
        errors="coerce",
    ).dropna()

    if len(returns) == 0:
        raise RuntimeError(
            f"No completed trades for "
            f"{label} at {latency_ms:.0f} ms."
        )

    row = {
        "session_id":
            session_id,

        "label":
            label,

        "latency_ms":
            float(latency_ms),

        "mechanical_pass":
            mechanical_pass,

        "qualifying_signals":
            int(
                summary[
                    "qualifying_signals"
                ]
            ),

        "completed_trades":
            int(
                len(returns)
            ),

        "completed_long_trades":
            int(
                len(long_returns)
            ),

        "completed_short_trades":
            int(
                len(short_returns)
            ),

        "ignored_while_position_open":
            int(
                summary[
                    "ignored_while_position_open"
                ]
            ),

        "skipped_no_entry_quote":
            int(
                summary[
                    "skipped_no_entry_quote"
                ]
            ),

        "incomplete_no_exit_quote":
            int(
                summary[
                    "incomplete_no_exit_quote"
                ]
            ),

        "mean_gross_return_bps":
            float(
                returns.mean()
            ),

        "median_gross_return_bps":
            float(
                returns.median()
            ),

        "positive_trade_rate":
            float(
                (
                    returns > 0
                ).mean()
            ),

        "cumulative_gross_return_bps":
            float(
                returns.sum()
            ),

        "maximum_drawdown_bps":
            maximum_drawdown_bps(
                returns
            ),

        "break_even_cost_per_side_bps":
            float(
                returns.mean()
                / 2.0
            ),

        "long_mean_gross_return_bps":
            (
                float(
                    long_returns.mean()
                )
                if len(long_returns)
                else np.nan
            ),

        "short_mean_gross_return_bps":
            (
                float(
                    short_returns.mean()
                )
                if len(short_returns)
                else np.nan
            ),

        "mean_entry_quote_wait_ms":
            float(
                completed[
                    "entry_quote_wait_ms"
                ].mean()
            ),

        "p95_entry_quote_wait_ms":
            float(
                completed[
                    "entry_quote_wait_ms"
                ].quantile(
                    0.95
                )
            ),

        "mean_exit_quote_wait_ms":
            float(
                completed[
                    "exit_quote_wait_ms"
                ].mean()
            ),

        "p95_exit_quote_wait_ms":
            float(
                completed[
                    "exit_quote_wait_ms"
                ].quantile(
                    0.95
                )
            ),
    }

    return row, completed


# =============================================================================
# AGGREGATE ONE LATENCY
# =============================================================================

def summarize_latency(
    session_rows,
    all_completed_trades,
    latency_ms,
):
    session_df = pd.DataFrame(
        session_rows
    )

    trades_df = pd.concat(
        all_completed_trades,
        ignore_index=True,
    )

    gross_returns = pd.to_numeric(
        trades_df[
            "gross_return_bps"
        ],
        errors="coerce",
    ).dropna()

    session_means = pd.to_numeric(
        session_df[
            "mean_gross_return_bps"
        ],
        errors="coerce",
    ).dropna()

    equal_weight_mean = float(
        session_means.mean()
    )

    equal_weight_median = float(
        session_means.median()
    )

    row = {
        "latency_ms":
            float(latency_ms),

        "sessions":
            int(
                len(session_means)
            ),

        "positive_sessions":
            int(
                (
                    session_means > 0
                ).sum()
            ),

        "total_completed_trades":
            int(
                len(gross_returns)
            ),

        "equal_weight_mean_session_return_bps":
            equal_weight_mean,

        "equal_weight_median_session_return_bps":
            equal_weight_median,

        "pooled_mean_trade_return_bps":
            float(
                gross_returns.mean()
            ),

        "pooled_median_trade_return_bps":
            float(
                gross_returns.median()
            ),

        "pooled_positive_trade_rate":
            float(
                (
                    gross_returns > 0
                ).mean()
            ),

        "pooled_cumulative_return_bps":
            float(
                gross_returns.sum()
            ),

        "equal_weight_break_even_cost_per_side_bps":
            (
                equal_weight_mean
                / 2.0
            ),

        "mean_session_maximum_drawdown_bps":
            float(
                session_df[
                    "maximum_drawdown_bps"
                ].mean()
            ),

        "all_mechanical_checks_pass":
            bool(
                session_df[
                    "mechanical_pass"
                ].all()
            ),
    }

    return row


# =============================================================================
# COST FRONTIER
# =============================================================================

def build_cost_frontier(
    session_latency_df,
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
            DEVELOPMENT_SESSIONS
        ):
            raise RuntimeError(
                f"Unexpected number of development "
                f"sessions at {latency_ms:.0f} ms."
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
# MAIN
# =============================================================================

def main():
    verify_frozen_inputs()

    # The imported frozen engine also verifies the original
    # protocol and parameter files.
    engine.verify_frozen_inputs()

    base_parameters = (
        engine.load_parameters()
    )

    print()
    print("=" * 105)
    print("DEVELOPMENT-ONLY LATENCY AND COST EVALUATION")
    print("=" * 105)

    print(
        "Latency grid (ms):      "
        + ", ".join(
            f"{x:.0f}"
            for x in LATENCY_GRID_MS
        )
    )

    print(
        "Cost grid / side (bps): "
        + ", ".join(
            f"{x:.2f}"
            for x
            in COST_GRID_PER_SIDE_BPS
        )
    )

    print()
    print(
        "IMPORTANT: ONLY THE FIVE DEVELOPMENT "
        "SESSIONS ARE USED."
    )

    all_session_rows = []
    latency_summary_rows = []

    for latency_ms in LATENCY_GRID_MS:
        print()
        print("-" * 105)

        print(
            f"LATENCY: {latency_ms:.0f} ms"
        )

        print("-" * 105)

        session_rows = []
        latency_trade_frames = []

        for session in DEVELOPMENT_SESSIONS:
            row, completed = (
                evaluate_session_latency(
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

            latency_trade_frames.append(
                completed
            )

            print(
                f"{row['label']:<20} "
                f"trades={row['completed_trades']:>3}  "
                f"mean={row['mean_gross_return_bps']:+.4f} bps  "
                f"BE/side={row['break_even_cost_per_side_bps']:+.4f}  "
                f"mechanics=PASS"
            )

        latency_summary = summarize_latency(
            session_rows=session_rows,
            all_completed_trades=(
                latency_trade_frames
            ),
            latency_ms=latency_ms,
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

    cost_df = build_cost_frontier(
        session_latency_df
    )

    # =========================================================================
    # LATENCY SUMMARY
    # =========================================================================

    print()
    print("=" * 105)
    print("DEVELOPMENT LATENCY SENSITIVITY — EQUAL-WEIGHT SESSION RESULTS")
    print("=" * 105)

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
            include=[np.number]
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
    # REFERENCE LATENCY COST FRONTIER
    # =========================================================================

    print()
    print("=" * 105)
    print("REFERENCE 100 MS — DEVELOPMENT COST FRONTIER")
    print("=" * 105)

    reference_cost_df = (
        cost_df[
            cost_df[
                "latency_ms"
            ]
            == REFERENCE_LATENCY_MS
        ]
        .copy()
    )

    reference_display = (
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
        reference_display
        .select_dtypes(
            include=[np.number]
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
    # REFERENCE RESULT
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

    reference_break_even = float(
        reference_latency_row[
            "equal_weight_break_even_cost_per_side_bps"
        ]
    )

    print()
    print("=" * 105)
    print("REFERENCE DEVELOPMENT EXECUTION RESULT")
    print("=" * 105)

    print(
        f"Reference latency:              "
        f"{REFERENCE_LATENCY_MS:.0f} ms"
    )

    print(
        f"Equal-weight gross return:      "
        f"{reference_mean:+.4f} bps/trade"
    )

    print(
        f"Break-even additional cost:     "
        f"{reference_break_even:+.4f} bps/side"
    )

    print(
        f"Positive development sessions:  "
        f"{int(reference_latency_row['positive_sessions'])} / "
        f"{int(reference_latency_row['sessions'])}"
    )

    if reference_mean > 0:
        print(
            "Development Level 2 status:      "
            "POSITIVE BEFORE ADDITIONAL COST"
        )
    else:
        print(
            "Development Level 2 status:      "
            "FAILED"
        )

    # =========================================================================
    # SAVE
    # =========================================================================

    SESSION_LATENCY_OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
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

    print()
    print("=" * 105)
    print("OUTPUT")
    print("=" * 105)

    print(
        "Session-by-latency results:"
    )

    print(
        SESSION_LATENCY_OUTPUT_FILE
    )

    print()

    print(
        "Latency sensitivity:"
    )

    print(
        LATENCY_OUTPUT_FILE
    )

    print()

    print(
        "Latency × cost frontier:"
    )

    print(
        COST_OUTPUT_FILE
    )

    print()
    print(
        "NO HOLDOUT SESSION WAS LOADED "
        "OR EVALUATED."
    )

    print()
    print(
        "Holdout execution remains untouched."
    )


if __name__ == "__main__":
    main()