from pathlib import Path
import hashlib

import numpy as np
import pandas as pd


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

EXECUTION_PROTOCOL_FILE = PROJECT_ROOT / "EXECUTION_PROTOCOL.md"

PARAMETER_FILE = (
    PROCESSED_DIR
    / "execution_parameters.csv"
)

TRADES_OUTPUT_FILE = (
    PROCESSED_DIR
    / "execution_trades_development.csv"
)

SUMMARY_OUTPUT_FILE = (
    PROCESSED_DIR
    / "execution_summary_development.csv"
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


# =============================================================================
# DEVELOPMENT SAMPLE ONLY
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
# FROZEN EXECUTION SETTINGS
# =============================================================================

SIGNAL_COLUMN = "median_book_imbalance"

REFERENCE_LATENCY_MS = 100.0

HOLDING_PERIOD_SECONDS = 1.0


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
    if not EXECUTION_PROTOCOL_FILE.exists():
        raise FileNotFoundError(
            f"Missing execution protocol:\n"
            f"{EXECUTION_PROTOCOL_FILE}"
        )

    if not PARAMETER_FILE.exists():
        raise FileNotFoundError(
            f"Missing execution parameter file:\n"
            f"{PARAMETER_FILE}"
        )

    actual_protocol_hash = sha256_file(
        EXECUTION_PROTOCOL_FILE
    )

    actual_parameter_hash = sha256_file(
        PARAMETER_FILE
    )

    print("=" * 100)
    print("FROZEN EXECUTION INPUT CHECK")
    print("=" * 100)

    print(
        f"Protocol expected:  "
        f"{EXPECTED_PROTOCOL_SHA256}"
    )

    print(
        f"Protocol actual:    "
        f"{actual_protocol_hash}"
    )

    print()

    print(
        f"Parameters expected: "
        f"{EXPECTED_PARAMETER_SHA256}"
    )

    print(
        f"Parameters actual:   "
        f"{actual_parameter_hash}"
    )

    if actual_protocol_hash != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError(
            "\nEXECUTION_PROTOCOL.md has changed.\n"
            "Simulation aborted."
        )

    if actual_parameter_hash != EXPECTED_PARAMETER_SHA256:
        raise RuntimeError(
            "\nexecution_parameters.csv has changed.\n"
            "Simulation aborted."
        )

    print()
    print(
        "Frozen input status: VERIFIED — UNCHANGED"
    )


# =============================================================================
# PARAMETER LOADING
# =============================================================================

def load_parameters():
    params = pd.read_csv(
        PARAMETER_FILE,
        dtype=str,
    )

    def get_value(parameter_name):
        matches = params[
            params["parameter"] == parameter_name
        ]

        if len(matches) != 1:
            raise RuntimeError(
                f"Expected exactly one parameter named "
                f"{parameter_name}, found {len(matches)}."
            )

        return matches.iloc[0]["value"]

    lower_threshold = float(
        get_value(
            "lower_threshold"
        )
    )

    upper_threshold = float(
        get_value(
            "upper_threshold"
        )
    )

    signal_column = get_value(
        "signal_column"
    )

    holding_period_seconds = float(
        get_value(
            "holding_period_seconds"
        )
    )

    reference_latency_ms = float(
        get_value(
            "reference_latency_ms"
        )
    )

    if signal_column != SIGNAL_COLUMN:
        raise RuntimeError(
            "Signal column in execution_parameters.csv "
            "does not match frozen simulator setting."
        )

    if not np.isclose(
        holding_period_seconds,
        HOLDING_PERIOD_SECONDS,
    ):
        raise RuntimeError(
            "Holding period does not match frozen setting."
        )

    if not np.isclose(
        reference_latency_ms,
        REFERENCE_LATENCY_MS,
    ):
        raise RuntimeError(
            "Reference latency does not match frozen setting."
        )

    return {
        "lower_threshold": lower_threshold,
        "upper_threshold": upper_threshold,
        "signal_column": signal_column,
        "holding_period_seconds": holding_period_seconds,
        "reference_latency_ms": reference_latency_ms,
    }


# =============================================================================
# FEATURE LOADING
# =============================================================================

def load_features(session_id):
    path = (
        PROCESSED_DIR
        / f"btcusdt_features_{session_id}.csv"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Missing feature file:\n{path}"
        )

    df = pd.read_csv(
        path
    )

    required_columns = [
        "received_at_utc",
        SIGNAL_COLUMN,
    ]

    for column in required_columns:
        if column not in df.columns:
            raise KeyError(
                f"Missing required feature column "
                f"{column} in:\n{path}"
            )

    df["received_at_utc"] = pd.to_datetime(
        df["received_at_utc"],
        utc=True,
        format="mixed",
        errors="coerce",
    )

    df[SIGNAL_COLUMN] = pd.to_numeric(
        df[SIGNAL_COLUMN],
        errors="coerce",
    )

    df = df.dropna(
        subset=[
            "received_at_utc",
        ]
    ).copy()

    df = df.sort_values(
        "received_at_utc",
        kind="mergesort",
    ).reset_index(
        drop=True
    )

    return df


# =============================================================================
# RAW QUOTE LOADING
# =============================================================================

def load_book(session_id):
    path = (
        RAW_DIR
        / f"btcusdt_book_{session_id}.csv"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Missing raw book file:\n{path}"
        )

    df = pd.read_csv(
        path
    )

    required_columns = [
        "received_at_utc",
        "bid_price",
        "ask_price",
    ]

    for column in required_columns:
        if column not in df.columns:
            raise KeyError(
                f"Missing required raw-book column "
                f"{column} in:\n{path}"
            )

    df["received_at_utc"] = pd.to_datetime(
        df["received_at_utc"],
        utc=True,
        format="mixed",
        errors="coerce",
    )

    for column in [
        "bid_price",
        "ask_price",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    if "bid_quantity" in df.columns:
        df["bid_quantity"] = pd.to_numeric(
            df["bid_quantity"],
            errors="coerce",
        )

    if "ask_quantity" in df.columns:
        df["ask_quantity"] = pd.to_numeric(
            df["ask_quantity"],
            errors="coerce",
        )

    if "update_id" in df.columns:
        df["update_id"] = pd.to_numeric(
            df["update_id"],
            errors="coerce",
        )

    df = df.dropna(
        subset=[
            "received_at_utc",
            "bid_price",
            "ask_price",
        ]
    ).copy()

    df = df[
        (df["bid_price"] > 0)
        &
        (df["ask_price"] > 0)
        &
        (df["ask_price"] >= df["bid_price"])
    ].copy()

    df = df.sort_values(
        "received_at_utc",
        kind="mergesort",
    ).reset_index(
        drop=True
    )

    if len(df) == 0:
        raise RuntimeError(
            f"No valid book quotes in session "
            f"{session_id}."
        )

    return df


# =============================================================================
# QUOTE LOOKUP
# =============================================================================

def first_quote_at_or_after(
    book,
    quote_times,
    target_time,
):
    """
    Return the first observed raw-book quote whose received_at_utc
    timestamp is greater than or equal to target_time.

    IMPORTANT:
    This deliberately uses pandas' native timestamp-aware searchsorted
    rather than integer timestamp representations.

    Pandas 3 may store DatetimeArray values internally at microsecond
    resolution while Timestamp.value is expressed in nanoseconds.
    Comparing those integer forms directly would therefore introduce
    a 1000x unit mismatch.
    """

    position = quote_times.searchsorted(
        target_time,
        side="left",
    )

    position = int(
        position
    )

    if position >= len(book):
        return None

    return book.iloc[
        position
    ]


# =============================================================================
# SIGNAL DIRECTION
# =============================================================================

def classify_signal(
    signal,
    lower_threshold,
    upper_threshold,
):
    if pd.isna(signal):
        return "FLAT"

    if signal <= lower_threshold:
        return "SHORT"

    if signal >= upper_threshold:
        return "LONG"

    return "FLAT"


# =============================================================================
# RETURN CALCULATION
# =============================================================================

def gross_return_bps(
    direction,
    entry_bid,
    entry_ask,
    exit_bid,
    exit_ask,
):
    if direction == "LONG":
        return (
            (
                exit_bid
                / entry_ask
            )
            - 1.0
        ) * 10_000

    if direction == "SHORT":
        return (
            (
                entry_bid
                / exit_ask
            )
            - 1.0
        ) * 10_000

    raise ValueError(
        f"Unexpected direction: {direction}"
    )


# =============================================================================
# SESSION SIMULATION
# =============================================================================

def simulate_session(
    session_id,
    label,
    parameters,
):
    features = load_features(
        session_id
    )

    book = load_book(
        session_id
    )

    # -------------------------------------------------------------------------
    # Unit-safe timestamp sequence.
    #
    # Do NOT convert one side to .asi8 and the other to Timestamp.value.
    # Native pandas datetime comparison preserves the correct time unit.
    # -------------------------------------------------------------------------

    quote_times = pd.DatetimeIndex(
        book["received_at_utc"]
    )

    lower_threshold = parameters[
        "lower_threshold"
    ]

    upper_threshold = parameters[
        "upper_threshold"
    ]

    latency = pd.Timedelta(
        milliseconds=parameters[
            "reference_latency_ms"
        ]
    )

    holding_period = pd.Timedelta(
        seconds=parameters[
            "holding_period_seconds"
        ]
    )

    rows = []

    qualifying_signals = 0
    qualifying_long_signals = 0
    qualifying_short_signals = 0

    ignored_while_position_open = 0
    skipped_no_entry_quote = 0
    incomplete_no_exit_quote = 0

    previous_exit_time = None

    trade_number = 0

    for _, feature_row in features.iterrows():
        bucket_start = feature_row[
            "received_at_utc"
        ]

        signal = feature_row[
            SIGNAL_COLUMN
        ]

        direction = classify_signal(
            signal=signal,
            lower_threshold=lower_threshold,
            upper_threshold=upper_threshold,
        )

        if direction == "FLAT":
            continue

        qualifying_signals += 1

        if direction == "LONG":
            qualifying_long_signals += 1
        else:
            qualifying_short_signals += 1

        # ---------------------------------------------------------------------
        # CAUSAL FEATURE TIMING
        #
        # A feature timestamp t summarizes [t, t+1s).
        # Therefore the earliest valid decision is t+1s.
        # ---------------------------------------------------------------------

        decision_time = (
            bucket_start
            + pd.Timedelta(
                seconds=1
            )
        )

        # ---------------------------------------------------------------------
        # ONLY ONE POSITION MAY BE OPEN
        # ---------------------------------------------------------------------

        if (
            previous_exit_time is not None
            and decision_time < previous_exit_time
        ):
            ignored_while_position_open += 1
            continue

        # ---------------------------------------------------------------------
        # ADDITIONAL MODELED LATENCY
        # ---------------------------------------------------------------------

        target_entry_time = (
            decision_time
            + latency
        )

        entry_quote = first_quote_at_or_after(
            book=book,
            quote_times=quote_times,
            target_time=target_entry_time,
        )

        if entry_quote is None:
            skipped_no_entry_quote += 1

            # Since the book is time sorted, no later signal can find
            # a quote either.
            break

        actual_entry_time = entry_quote[
            "received_at_utc"
        ]

        entry_bid = float(
            entry_quote[
                "bid_price"
            ]
        )

        entry_ask = float(
            entry_quote[
                "ask_price"
            ]
        )

        target_exit_time = (
            actual_entry_time
            + holding_period
        )

        exit_quote = first_quote_at_or_after(
            book=book,
            quote_times=quote_times,
            target_time=target_exit_time,
        )

        trade_number += 1

        if exit_quote is None:
            incomplete_no_exit_quote += 1

            rows.append(
                {
                    "session_id":
                        session_id,

                    "label":
                        label,

                    "trade_number":
                        trade_number,

                    "status":
                        "INCOMPLETE_NO_EXIT",

                    "bucket_start_utc":
                        bucket_start,

                    "decision_time_utc":
                        decision_time,

                    "signal":
                        signal,

                    "direction":
                        direction,

                    "lower_threshold":
                        lower_threshold,

                    "upper_threshold":
                        upper_threshold,

                    "modeled_latency_ms":
                        parameters[
                            "reference_latency_ms"
                        ],

                    "target_entry_time_utc":
                        target_entry_time,

                    "actual_entry_time_utc":
                        actual_entry_time,

                    "decision_to_entry_ms":
                        (
                            actual_entry_time
                            - decision_time
                        ).total_seconds()
                        * 1000,

                    "entry_quote_wait_ms":
                        (
                            actual_entry_time
                            - target_entry_time
                        ).total_seconds()
                        * 1000,

                    "entry_bid":
                        entry_bid,

                    "entry_ask":
                        entry_ask,

                    "entry_spread":
                        entry_ask
                        - entry_bid,

                    "entry_update_id":
                        entry_quote.get(
                            "update_id",
                            np.nan,
                        ),

                    "target_exit_time_utc":
                        target_exit_time,

                    "actual_exit_time_utc":
                        pd.NaT,

                    "exit_quote_wait_ms":
                        np.nan,

                    "exit_bid":
                        np.nan,

                    "exit_ask":
                        np.nan,

                    "exit_spread":
                        np.nan,

                    "exit_update_id":
                        np.nan,

                    "holding_time_actual_seconds":
                        np.nan,

                    "gross_return_bps":
                        np.nan,
                }
            )

            # Position remains open through the end of the session.
            break

        actual_exit_time = exit_quote[
            "received_at_utc"
        ]

        exit_bid = float(
            exit_quote[
                "bid_price"
            ]
        )

        exit_ask = float(
            exit_quote[
                "ask_price"
            ]
        )

        return_bps = gross_return_bps(
            direction=direction,
            entry_bid=entry_bid,
            entry_ask=entry_ask,
            exit_bid=exit_bid,
            exit_ask=exit_ask,
        )

        rows.append(
            {
                "session_id":
                    session_id,

                "label":
                    label,

                "trade_number":
                    trade_number,

                "status":
                    "COMPLETED",

                "bucket_start_utc":
                    bucket_start,

                "decision_time_utc":
                    decision_time,

                "signal":
                    float(signal),

                "direction":
                    direction,

                "lower_threshold":
                    lower_threshold,

                "upper_threshold":
                    upper_threshold,

                "modeled_latency_ms":
                    parameters[
                        "reference_latency_ms"
                    ],

                "target_entry_time_utc":
                    target_entry_time,

                "actual_entry_time_utc":
                    actual_entry_time,

                "decision_to_entry_ms":
                    (
                        actual_entry_time
                        - decision_time
                    ).total_seconds()
                    * 1000,

                "entry_quote_wait_ms":
                    (
                        actual_entry_time
                        - target_entry_time
                    ).total_seconds()
                    * 1000,

                "entry_bid":
                    entry_bid,

                "entry_ask":
                    entry_ask,

                "entry_spread":
                    entry_ask
                    - entry_bid,

                "entry_update_id":
                    entry_quote.get(
                        "update_id",
                        np.nan,
                    ),

                "target_exit_time_utc":
                    target_exit_time,

                "actual_exit_time_utc":
                    actual_exit_time,

                "exit_quote_wait_ms":
                    (
                        actual_exit_time
                        - target_exit_time
                    ).total_seconds()
                    * 1000,

                "exit_bid":
                    exit_bid,

                "exit_ask":
                    exit_ask,

                "exit_spread":
                    exit_ask
                    - exit_bid,

                "exit_update_id":
                    exit_quote.get(
                        "update_id",
                        np.nan,
                    ),

                "holding_time_actual_seconds":
                    (
                        actual_exit_time
                        - actual_entry_time
                    ).total_seconds(),

                "gross_return_bps":
                    return_bps,
            }
        )

        previous_exit_time = (
            actual_exit_time
        )

    trades = pd.DataFrame(
        rows
    )

    completed = (
        trades[
            trades["status"] == "COMPLETED"
        ].copy()
        if len(trades)
        else pd.DataFrame()
    )

    if len(completed):
        long_completed = completed[
            completed["direction"] == "LONG"
        ]

        short_completed = completed[
            completed["direction"] == "SHORT"
        ]

        returns = completed[
            "gross_return_bps"
        ]

        mean_return = float(
            returns.mean()
        )

        median_return = float(
            returns.median()
        )

        positive_rate = float(
            (
                returns > 0
            ).mean()
        )

        cumulative_return = float(
            returns.sum()
        )

        minimum_return = float(
            returns.min()
        )

        maximum_return = float(
            returns.max()
        )

        break_even_cost_per_side = (
            mean_return
            / 2.0
        )

        mean_entry_quote_wait = float(
            completed[
                "entry_quote_wait_ms"
            ].mean()
        )

        p95_entry_quote_wait = float(
            completed[
                "entry_quote_wait_ms"
            ].quantile(
                0.95
            )
        )

        maximum_entry_quote_wait = float(
            completed[
                "entry_quote_wait_ms"
            ].max()
        )

        mean_exit_quote_wait = float(
            completed[
                "exit_quote_wait_ms"
            ].mean()
        )

        p95_exit_quote_wait = float(
            completed[
                "exit_quote_wait_ms"
            ].quantile(
                0.95
            )
        )

        maximum_exit_quote_wait = float(
            completed[
                "exit_quote_wait_ms"
            ].max()
        )

        mean_actual_holding = float(
            completed[
                "holding_time_actual_seconds"
            ].mean()
        )

        long_mean_return = (
            float(
                long_completed[
                    "gross_return_bps"
                ].mean()
            )
            if len(long_completed)
            else np.nan
        )

        short_mean_return = (
            float(
                short_completed[
                    "gross_return_bps"
                ].mean()
            )
            if len(short_completed)
            else np.nan
        )

    else:
        long_completed = pd.DataFrame()
        short_completed = pd.DataFrame()

        mean_return = np.nan
        median_return = np.nan
        positive_rate = np.nan
        cumulative_return = np.nan
        minimum_return = np.nan
        maximum_return = np.nan
        break_even_cost_per_side = np.nan

        mean_entry_quote_wait = np.nan
        p95_entry_quote_wait = np.nan
        maximum_entry_quote_wait = np.nan

        mean_exit_quote_wait = np.nan
        p95_exit_quote_wait = np.nan
        maximum_exit_quote_wait = np.nan

        mean_actual_holding = np.nan

        long_mean_return = np.nan
        short_mean_return = np.nan

    summary = {
        "session_id":
            session_id,

        "label":
            label,

        "feature_observations":
            len(features),

        "book_updates":
            len(book),

        "qualifying_signals":
            qualifying_signals,

        "qualifying_long_signals":
            qualifying_long_signals,

        "qualifying_short_signals":
            qualifying_short_signals,

        "ignored_while_position_open":
            ignored_while_position_open,

        "skipped_no_entry_quote":
            skipped_no_entry_quote,

        "incomplete_no_exit_quote":
            incomplete_no_exit_quote,

        "completed_trades":
            len(completed),

        "completed_long_trades":
            len(long_completed),

        "completed_short_trades":
            len(short_completed),

        "mean_gross_return_bps":
            mean_return,

        "median_gross_return_bps":
            median_return,

        "positive_trade_rate":
            positive_rate,

        "cumulative_gross_return_bps":
            cumulative_return,

        "minimum_trade_return_bps":
            minimum_return,

        "maximum_trade_return_bps":
            maximum_return,

        "break_even_additional_cost_per_side_bps":
            break_even_cost_per_side,

        "long_mean_gross_return_bps":
            long_mean_return,

        "short_mean_gross_return_bps":
            short_mean_return,

        "mean_entry_quote_wait_ms":
            mean_entry_quote_wait,

        "p95_entry_quote_wait_ms":
            p95_entry_quote_wait,

        "max_entry_quote_wait_ms":
            maximum_entry_quote_wait,

        "mean_exit_quote_wait_ms":
            mean_exit_quote_wait,

        "p95_exit_quote_wait_ms":
            p95_exit_quote_wait,

        "max_exit_quote_wait_ms":
            maximum_exit_quote_wait,

        "mean_actual_holding_seconds":
            mean_actual_holding,
    }

    return trades, summary


# =============================================================================
# CAUSALITY / MECHANICAL VALIDATION
# =============================================================================

def validate_completed_trades(
    trades
):
    completed = trades[
        trades["status"] == "COMPLETED"
    ].copy()

    if len(completed) == 0:
        raise RuntimeError(
            "No completed development trades were generated."
        )

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

    checks = {}

    checks[
        "decision_equals_bucket_plus_1s"
    ] = bool(
        (
            completed[
                "decision_time_utc"
            ]
            ==
            (
                completed[
                    "bucket_start_utc"
                ]
                + pd.Timedelta(
                    seconds=1
                )
            )
        ).all()
    )

    checks[
        "target_entry_not_before_decision"
    ] = bool(
        (
            completed[
                "target_entry_time_utc"
            ]
            >= completed[
                "decision_time_utc"
            ]
        ).all()
    )

    checks[
        "actual_entry_not_before_target"
    ] = bool(
        (
            completed[
                "actual_entry_time_utc"
            ]
            >= completed[
                "target_entry_time_utc"
            ]
        ).all()
    )

    checks[
        "target_exit_not_before_entry"
    ] = bool(
        (
            completed[
                "target_exit_time_utc"
            ]
            >= completed[
                "actual_entry_time_utc"
            ]
        ).all()
    )

    checks[
        "actual_exit_not_before_target"
    ] = bool(
        (
            completed[
                "actual_exit_time_utc"
            ]
            >= completed[
                "target_exit_time_utc"
            ]
        ).all()
    )

    checks[
        "all_decision_to_entry_at_least_100ms"
    ] = bool(
        (
            completed[
                "decision_to_entry_ms"
            ]
            >= REFERENCE_LATENCY_MS
        ).all()
    )

    checks[
        "all_actual_holding_at_least_1s"
    ] = bool(
        (
            completed[
                "holding_time_actual_seconds"
            ]
            >= HOLDING_PERIOD_SECONDS
        ).all()
    )

    # -------------------------------------------------------------------------
    # NO POSITION OVERLAP WITHIN EACH SESSION
    # -------------------------------------------------------------------------

    no_overlap = True

    for _, session_trades in completed.groupby(
        "session_id"
    ):
        session_trades = session_trades.sort_values(
            "actual_entry_time_utc"
        ).reset_index(
            drop=True
        )

        for i in range(
            1,
            len(session_trades),
        ):
            previous_exit = session_trades.loc[
                i - 1,
                "actual_exit_time_utc",
            ]

            current_entry = session_trades.loc[
                i,
                "actual_entry_time_utc",
            ]

            if current_entry < previous_exit:
                no_overlap = False
                break

        if not no_overlap:
            break

    checks[
        "no_overlapping_positions"
    ] = no_overlap

    all_pass = all(
        checks.values()
    )

    return checks, all_pass


# =============================================================================
# MAIN
# =============================================================================

def main():
    verify_frozen_inputs()

    parameters = load_parameters()

    print()
    print("=" * 100)
    print("FROZEN EXECUTION PARAMETERS")
    print("=" * 100)

    print(
        f"Lower threshold:       "
        f"{parameters['lower_threshold']:+.10f}"
    )

    print(
        f"Upper threshold:       "
        f"{parameters['upper_threshold']:+.10f}"
    )

    print(
        f"Signal:                "
        f"{parameters['signal_column']}"
    )

    print(
        f"Reference latency:     "
        f"{parameters['reference_latency_ms']:.0f} ms"
    )

    print(
        f"Holding period:        "
        f"{parameters['holding_period_seconds']:.1f} s"
    )

    print()
    print(
        "IMPORTANT: DEVELOPMENT SESSIONS ONLY"
    )

    all_trade_frames = []
    session_summaries = []

    print()
    print("=" * 100)
    print("DEVELOPMENT EXECUTION SIMULATION")
    print("=" * 100)

    for session in DEVELOPMENT_SESSIONS:
        session_id = session[
            "session_id"
        ]

        label = session[
            "label"
        ]

        print()
        print(
            f"Simulating {label}: "
            f"{session_id}"
        )

        trades, summary = simulate_session(
            session_id=session_id,
            label=label,
            parameters=parameters,
        )

        if len(trades):
            all_trade_frames.append(
                trades
            )

        session_summaries.append(
            summary
        )

        print(
            f"  Qualifying signals:       "
            f"{summary['qualifying_signals']}"
        )

        print(
            f"  LONG signals:             "
            f"{summary['qualifying_long_signals']}"
        )

        print(
            f"  SHORT signals:            "
            f"{summary['qualifying_short_signals']}"
        )

        print(
            f"  Ignored while open:       "
            f"{summary['ignored_while_position_open']}"
        )

        print(
            f"  No-entry skips:           "
            f"{summary['skipped_no_entry_quote']}"
        )

        print(
            f"  Incomplete trades:        "
            f"{summary['incomplete_no_exit_quote']}"
        )

        print(
            f"  Completed trades:         "
            f"{summary['completed_trades']}"
        )

        print(
            f"  Mean gross return:        "
            f"{summary['mean_gross_return_bps']:+.4f} bps"
        )

        print(
            f"  Positive-trade rate:      "
            f"{summary['positive_trade_rate']:.4f}"
        )

        print(
            f"  Break-even cost / side:   "
            f"{summary['break_even_additional_cost_per_side_bps']:+.4f} bps"
        )

    if not all_trade_frames:
        raise RuntimeError(
            "No development trades were generated."
        )

    all_trades = pd.concat(
        all_trade_frames,
        ignore_index=True,
    )

    summary_df = pd.DataFrame(
        session_summaries
    )

    # =========================================================================
    # MECHANICAL / CAUSAL VALIDATION
    # =========================================================================

    checks, all_pass = validate_completed_trades(
        all_trades
    )

    print()
    print("=" * 100)
    print("CAUSALITY AND TIMESTAMP VALIDATION")
    print("=" * 100)

    for check_name, passed in checks.items():
        print(
            f"{check_name:<45} "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()
    print(
        "Overall mechanical status: "
        f"{'PASS' if all_pass else 'FAIL'}"
    )

    if not all_pass:
        raise RuntimeError(
            "\nOne or more execution causality checks failed.\n"
            "Do NOT proceed to holdout execution."
        )

    # =========================================================================
    # EQUAL-WEIGHT DEVELOPMENT SUMMARY
    # =========================================================================

    valid_session_means = (
        summary_df[
            "mean_gross_return_bps"
        ]
        .dropna()
    )

    equal_weight_mean = float(
        valid_session_means.mean()
    )

    equal_weight_median = float(
        valid_session_means.median()
    )

    positive_sessions = int(
        (
            valid_session_means > 0
        ).sum()
    )

    print()
    print("=" * 100)
    print("DEVELOPMENT SESSION SUMMARY")
    print("=" * 100)

    display_columns = [
        "label",
        "qualifying_signals",
        "completed_trades",
        "completed_long_trades",
        "completed_short_trades",
        "mean_gross_return_bps",
        "median_gross_return_bps",
        "positive_trade_rate",
        "break_even_additional_cost_per_side_bps",
        "mean_entry_quote_wait_ms",
        "p95_entry_quote_wait_ms",
        "mean_exit_quote_wait_ms",
    ]

    display_df = summary_df[
        display_columns
    ].copy()

    numeric_columns = display_df.select_dtypes(
        include=[
            np.number
        ]
    ).columns

    display_df[
        numeric_columns
    ] = display_df[
        numeric_columns
    ].round(
        4
    )

    print(
        display_df.to_string(
            index=False
        )
    )

    print()
    print(
        f"Equal-weight mean session return:   "
        f"{equal_weight_mean:+.4f} bps/trade"
    )

    print(
        f"Equal-weight median session return: "
        f"{equal_weight_median:+.4f} bps/trade"
    )

    print(
        f"Positive development sessions:      "
        f"{positive_sessions} / "
        f"{len(valid_session_means)}"
    )

    # =========================================================================
    # MANUAL AUDIT SAMPLE
    # =========================================================================

    completed = all_trades[
        all_trades[
            "status"
        ]
        == "COMPLETED"
    ].copy()

    print()
    print("=" * 100)
    print("FIRST 12 COMPLETED TRADES — MANUAL TIMING AUDIT")
    print("=" * 100)

    audit_columns = [
        "label",
        "trade_number",
        "bucket_start_utc",
        "decision_time_utc",
        "signal",
        "direction",
        "target_entry_time_utc",
        "actual_entry_time_utc",
        "decision_to_entry_ms",
        "entry_quote_wait_ms",
        "entry_bid",
        "entry_ask",
        "target_exit_time_utc",
        "actual_exit_time_utc",
        "exit_bid",
        "exit_ask",
        "gross_return_bps",
    ]

    audit = completed[
        audit_columns
    ].head(
        12
    ).copy()

    for column in [
        "signal",
        "decision_to_entry_ms",
        "entry_quote_wait_ms",
        "entry_bid",
        "entry_ask",
        "exit_bid",
        "exit_ask",
        "gross_return_bps",
    ]:
        audit[column] = pd.to_numeric(
            audit[column],
            errors="coerce",
        ).round(
            6
        )

    print(
        audit.to_string(
            index=False
        )
    )

    # =========================================================================
    # SAVE OUTPUT
    # =========================================================================

    TRADES_OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_trades.to_csv(
        TRADES_OUTPUT_FILE,
        index=False,
    )

    summary_df.to_csv(
        SUMMARY_OUTPUT_FILE,
        index=False,
    )

    print()
    print("=" * 100)
    print("OUTPUT")
    print("=" * 100)

    print(
        "Development trades:"
    )

    print(
        TRADES_OUTPUT_FILE
    )

    print()

    print(
        "Development summary:"
    )

    print(
        SUMMARY_OUTPUT_FILE
    )

    print()
    print(
        "NO HOLDOUT SESSION WAS LOADED "
        "OR EVALUATED BY THIS SCRIPT."
    )

    print()
    print(
        "Do not proceed to holdout execution until "
        "the causality audit has been reviewed."
    )


if __name__ == "__main__":
    main()