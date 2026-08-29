from pathlib import Path
from datetime import datetime, timezone
import hashlib
import math

import numpy as np
import pandas as pd
import statsmodels.api as sm

from scipy.stats import binomtest


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

PROTOCOL_FILE = (
    PROJECT_ROOT
    / "VALIDATION_PROTOCOL.md"
)

SESSION_OUTPUT_FILE = (
    PROCESSED_DIR
    / "holdout_validation_session_results.csv"
)

SUMMARY_OUTPUT_FILE = (
    PROCESSED_DIR
    / "holdout_validation_summary.csv"
)

COMPARISON_OUTPUT_FILE = (
    PROCESSED_DIR
    / "development_vs_holdout_comparison.csv"
)


# =============================================================================
# FROZEN PROTOCOL FINGERPRINT
# =============================================================================

EXPECTED_PROTOCOL_SHA256 = (
    "6d2ed10e1e18b04e873cebee8033191fc8710866eedd3d574e4b547aabc491da"
)


# =============================================================================
# EXPLORATORY DEVELOPMENT SAMPLE
# =============================================================================

DEVELOPMENT_SESSIONS = [
    {
        "session_id": "20260824_135129",
        "label": "afternoon_1",
        "distinct_period": True,
    },
    {
        "session_id": "20260825_084855",
        "label": "morning_1",
        "distinct_period": True,
    },
    {
        "session_id": "20260826_085550",
        "label": "morning_2",
        "distinct_period": True,
    },
    {
        "session_id": "20260826_144545",
        "label": "evening_1",
        "distinct_period": True,
    },
    {
        "session_id": "20260826_151328",
        "label": "late_afternoon_1",
        "distinct_period": False,
    },
]


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
# FROZEN ANALYSIS SETTINGS
# =============================================================================

PRIMARY_SIGNAL = "median_book_imbalance"

TARGET_1S = "future_return_1s_bps"
TARGET_5S = "future_return_5s_bps"

QUANTILE_COUNT = 5

HAC_LAGS_1S = 5
HAC_LAGS_5S = 10

NONOVERLAP_HAC_LAGS = 1

ACTIVITY_THRESHOLD = 25

BOOTSTRAP_REPETITIONS = 1000
BOOTSTRAP_BLOCK_LENGTH = 30
BOOTSTRAP_RANDOM_SEED = 42


# =============================================================================
# PROTOCOL INTEGRITY
# =============================================================================

def sha256_file(file_path):
    """
    Calculate SHA-256 fingerprint of a file.
    """

    sha = hashlib.sha256()

    with open(
        file_path,
        "rb",
    ) as handle:

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


def verify_protocol():
    """
    Abort if the frozen protocol file has changed.
    """

    if not PROTOCOL_FILE.exists():

        raise FileNotFoundError(
            f"Protocol file not found:\n"
            f"{PROTOCOL_FILE}"
        )

    actual_hash = sha256_file(
        PROTOCOL_FILE
    )

    print("=" * 100)
    print("FROZEN PROTOCOL INTEGRITY CHECK")
    print("=" * 100)

    print(
        f"Expected SHA256: "
        f"{EXPECTED_PROTOCOL_SHA256}"
    )

    print(
        f"Actual SHA256:   "
        f"{actual_hash}"
    )

    if (
        actual_hash
        != EXPECTED_PROTOCOL_SHA256
    ):

        raise RuntimeError(
            "\nVALIDATION_PROTOCOL.md has changed.\n"
            "Holdout evaluation aborted."
        )

    print(
        "Protocol status:  VERIFIED — UNCHANGED"
    )


# =============================================================================
# TIME HELPERS
# =============================================================================

def parse_session_start_utc(
    session_id,
):

    parsed = datetime.strptime(
        session_id,
        "%Y%m%d_%H%M%S",
    )

    return parsed.replace(
        tzinfo=timezone.utc
    )


# =============================================================================
# DATA LOADING
# =============================================================================

def load_session(
    session_id,
):

    file_path = (
        PROCESSED_DIR
        / f"btcusdt_features_{session_id}.csv"
    )

    if not file_path.exists():

        raise FileNotFoundError(
            f"Missing feature file:\n"
            f"{file_path}"
        )

    df = pd.read_csv(
        file_path
    )

    return df


# =============================================================================
# BASIC HELPERS
# =============================================================================

def prepare_regression_data(
    df,
    signal_col,
    target_col,
    minimum_trades=None,
):

    data = df.copy()

    if minimum_trades is not None:

        data = data[
            data["trades"]
            >= minimum_trades
        ].copy()

    data = data.dropna(
        subset=[
            signal_col,
            target_col,
        ]
    ).copy()

    return data


def mid_price_move_bps(
    df,
):

    prices = (
        df["mid_price"]
        .dropna()
    )

    if len(prices) < 2:

        return float("nan")

    return (
        (
            prices.iloc[-1]
            / prices.iloc[0]
        )
        - 1.0
    ) * 10_000


# =============================================================================
# FROZEN QUANTILE ANALYSIS
# =============================================================================

def bucket_spread(
    df,
    signal_col,
    target_col,
    minimum_trades=None,
):

    data = df.copy()

    if minimum_trades is not None:

        data = data[
            data["trades"]
            >= minimum_trades
        ].copy()

    data = data.dropna(
        subset=[
            signal_col,
            target_col,
        ]
    ).copy()

    if len(data) < 10:

        return {
            "observations": len(data),
            "buckets": 0,
            "low_return": float("nan"),
            "high_return": float("nan"),
            "spread": float("nan"),
        }

    try:

        data[
            "bucket"
        ] = pd.qcut(
            data[
                signal_col
            ],
            q=QUANTILE_COUNT,
            labels=False,
            duplicates="drop",
        )

        data[
            "bucket"
        ] = (
            data[
                "bucket"
            ]
            + 1
        )

    except ValueError:

        return {
            "observations": len(data),
            "buckets": 0,
            "low_return": float("nan"),
            "high_return": float("nan"),
            "spread": float("nan"),
        }

    data = data.dropna(
        subset=[
            "bucket"
        ]
    )

    actual_buckets = int(
        data[
            "bucket"
        ].nunique()
    )

    if actual_buckets < 2:

        return {
            "observations": len(data),
            "buckets": actual_buckets,
            "low_return": float("nan"),
            "high_return": float("nan"),
            "spread": float("nan"),
        }

    summary = (
        data.groupby(
            "bucket"
        )
        .agg(
            mean_future_return_bps=(
                target_col,
                "mean",
            )
        )
    )

    low_return = float(
        summary.iloc[0][
            "mean_future_return_bps"
        ]
    )

    high_return = float(
        summary.iloc[-1][
            "mean_future_return_bps"
        ]
    )

    return {
        "observations":
            len(data),

        "buckets":
            actual_buckets,

        "low_return":
            low_return,

        "high_return":
            high_return,

        "spread":
            high_return
            - low_return,
    }


# =============================================================================
# HAC / NEWEY-WEST REGRESSION
# =============================================================================

def hac_regression(
    df,
    signal_col,
    target_col,
    maxlags,
    minimum_trades=None,
):

    data = prepare_regression_data(
        df=df,
        signal_col=signal_col,
        target_col=target_col,
        minimum_trades=minimum_trades,
    )

    if len(data) < 20:

        return {
            "observations": len(data),
            "alpha": float("nan"),
            "beta": float("nan"),
            "beta_se": float("nan"),
            "beta_t": float("nan"),
            "beta_p": float("nan"),
            "beta_ci_low": float("nan"),
            "beta_ci_high": float("nan"),
            "r_squared": float("nan"),
        }

    y = (
        data[
            target_col
        ]
        .astype(float)
    )

    x = sm.add_constant(
        data[
            [
                signal_col
            ]
        ].astype(float),
        has_constant="add",
    )

    model = sm.OLS(
        y,
        x,
    ).fit(
        cov_type="HAC",
        cov_kwds={
            "maxlags":
                maxlags,

            "use_correction":
                True,
        },
    )

    confidence_interval = (
        model.conf_int()
        .loc[
            signal_col
        ]
    )

    return {
        "observations":
            int(
                model.nobs
            ),

        "alpha":
            float(
                model.params[
                    "const"
                ]
            ),

        "beta":
            float(
                model.params[
                    signal_col
                ]
            ),

        "beta_se":
            float(
                model.bse[
                    signal_col
                ]
            ),

        "beta_t":
            float(
                model.tvalues[
                    signal_col
                ]
            ),

        "beta_p":
            float(
                model.pvalues[
                    signal_col
                ]
            ),

        "beta_ci_low":
            float(
                confidence_interval.iloc[0]
            ),

        "beta_ci_high":
            float(
                confidence_interval.iloc[1]
            ),

        "r_squared":
            float(
                model.rsquared
            ),
    }


# =============================================================================
# NON-OVERLAPPING +5 SECOND SENSITIVITY
# =============================================================================

def nonoverlapping_5s_regression(
    df,
):

    data = prepare_regression_data(
        df=df,
        signal_col=PRIMARY_SIGNAL,
        target_col=TARGET_5S,
    )

    data = (
        data.iloc[::5]
        .copy()
    )

    if len(data) < 20:

        return {
            "observations": len(data),
            "beta": float("nan"),
            "beta_se": float("nan"),
            "beta_t": float("nan"),
            "beta_p": float("nan"),
            "beta_ci_low": float("nan"),
            "beta_ci_high": float("nan"),
        }

    y = (
        data[
            TARGET_5S
        ]
        .astype(float)
    )

    x = sm.add_constant(
        data[
            [
                PRIMARY_SIGNAL
            ]
        ].astype(float),
        has_constant="add",
    )

    model = sm.OLS(
        y,
        x,
    ).fit(
        cov_type="HAC",
        cov_kwds={
            "maxlags":
                NONOVERLAP_HAC_LAGS,

            "use_correction":
                True,
        },
    )

    confidence_interval = (
        model.conf_int()
        .loc[
            PRIMARY_SIGNAL
        ]
    )

    return {
        "observations":
            int(
                model.nobs
            ),

        "beta":
            float(
                model.params[
                    PRIMARY_SIGNAL
                ]
            ),

        "beta_se":
            float(
                model.bse[
                    PRIMARY_SIGNAL
                ]
            ),

        "beta_t":
            float(
                model.tvalues[
                    PRIMARY_SIGNAL
                ]
            ),

        "beta_p":
            float(
                model.pvalues[
                    PRIMARY_SIGNAL
                ]
            ),

        "beta_ci_low":
            float(
                confidence_interval.iloc[0]
            ),

        "beta_ci_high":
            float(
                confidence_interval.iloc[1]
            ),
    }


# =============================================================================
# MOVING-BLOCK BOOTSTRAP
# =============================================================================

def ols_slope(
    x,
    y,
):

    x = np.asarray(
        x,
        dtype=float,
    )

    y = np.asarray(
        y,
        dtype=float,
    )

    x_mean = np.mean(
        x
    )

    y_mean = np.mean(
        y
    )

    denominator = np.sum(
        (
            x
            - x_mean
        ) ** 2
    )

    if denominator <= 0:

        return float("nan")

    numerator = np.sum(
        (
            x
            - x_mean
        )
        *
        (
            y
            - y_mean
        )
    )

    return (
        numerator
        / denominator
    )


def moving_block_bootstrap(
    df,
    seed,
):

    data = prepare_regression_data(
        df=df,
        signal_col=PRIMARY_SIGNAL,
        target_col=TARGET_1S,
    )

    x = (
        data[
            PRIMARY_SIGNAL
        ]
        .to_numpy(
            dtype=float
        )
    )

    y = (
        data[
            TARGET_1S
        ]
        .to_numpy(
            dtype=float
        )
    )

    n = len(data)

    if n < 30:

        return {
            "observations": n,
            "point_beta": float("nan"),
            "bootstrap_mean_beta": float("nan"),
            "bootstrap_ci_low": float("nan"),
            "bootstrap_ci_high": float("nan"),
            "positive_rate": float("nan"),
            "slopes": np.array([]),
        }

    block_length = min(
        BOOTSTRAP_BLOCK_LENGTH,
        n,
    )

    maximum_start = (
        n
        - block_length
    )

    number_of_blocks = (
        math.ceil(
            n
            / block_length
        )
    )

    rng = np.random.default_rng(
        seed
    )

    point_beta = ols_slope(
        x,
        y,
    )

    slopes = []

    for _ in range(
        BOOTSTRAP_REPETITIONS
    ):

        starts = rng.integers(
            low=0,
            high=maximum_start + 1,
            size=number_of_blocks,
        )

        indices = []

        for start in starts:

            block = np.arange(
                start,
                start + block_length,
            )

            indices.extend(
                block.tolist()
            )

        indices = np.asarray(
            indices[:n]
        )

        beta = ols_slope(
            x[
                indices
            ],
            y[
                indices
            ],
        )

        if not np.isnan(beta):

            slopes.append(
                beta
            )

    slopes = np.asarray(
        slopes,
        dtype=float,
    )

    if len(slopes) == 0:

        return {
            "observations": n,
            "point_beta": point_beta,
            "bootstrap_mean_beta": float("nan"),
            "bootstrap_ci_low": float("nan"),
            "bootstrap_ci_high": float("nan"),
            "positive_rate": float("nan"),
            "slopes": np.array([]),
        }

    return {
        "observations":
            n,

        "point_beta":
            point_beta,

        "bootstrap_mean_beta":
            float(
                np.mean(
                    slopes
                )
            ),

        "bootstrap_ci_low":
            float(
                np.quantile(
                    slopes,
                    0.025,
                )
            ),

        "bootstrap_ci_high":
            float(
                np.quantile(
                    slopes,
                    0.975,
                )
            ),

        "positive_rate":
            float(
                np.mean(
                    slopes > 0
                )
            ),

        "slopes":
            slopes,
    }


# =============================================================================
# SESSION ANALYSIS
# =============================================================================

def analyze_session(
    session_id,
    label,
    seed,
):

    df = load_session(
        session_id
    )

    qspread_1s = (
        bucket_spread(
            df,
            PRIMARY_SIGNAL,
            TARGET_1S,
        )
    )

    qspread_5s = (
        bucket_spread(
            df,
            PRIMARY_SIGNAL,
            TARGET_5S,
        )
    )

    qspread_1s_ge25 = (
        bucket_spread(
            df,
            PRIMARY_SIGNAL,
            TARGET_1S,
            minimum_trades=(
                ACTIVITY_THRESHOLD
            ),
        )
    )

    regression_1s = (
        hac_regression(
            df=df,
            signal_col=PRIMARY_SIGNAL,
            target_col=TARGET_1S,
            maxlags=HAC_LAGS_1S,
        )
    )

    regression_5s = (
        hac_regression(
            df=df,
            signal_col=PRIMARY_SIGNAL,
            target_col=TARGET_5S,
            maxlags=HAC_LAGS_5S,
        )
    )

    regression_1s_ge25 = (
        hac_regression(
            df=df,
            signal_col=PRIMARY_SIGNAL,
            target_col=TARGET_1S,
            maxlags=HAC_LAGS_1S,
            minimum_trades=(
                ACTIVITY_THRESHOLD
            ),
        )
    )

    nonoverlap_5s = (
        nonoverlapping_5s_regression(
            df
        )
    )

    bootstrap = (
        moving_block_bootstrap(
            df=df,
            seed=seed,
        )
    )

    return {
        "session_id":
            session_id,

        "label":
            label,

        "session_start_utc":
            parse_session_start_utc(
                session_id
            ).isoformat(),

        "observations":
            len(df),

        "mid_price_move_bps":
            mid_price_move_bps(
                df
            ),

        "zero_trade_seconds":
            int(
                (
                    df["trades"]
                    == 0
                ).sum()
            ),

        "seconds_ge25_trades":
            int(
                (
                    df["trades"]
                    >= ACTIVITY_THRESHOLD
                ).sum()
            ),

        # ---------------------------------------------------------
        # FROZEN BUCKET RESULTS
        # ---------------------------------------------------------

        "book_qspread_1s_bps":
            qspread_1s[
                "spread"
            ],

        "book_qspread_5s_bps":
            qspread_5s[
                "spread"
            ],

        "book_qspread_1s_ge25_bps":
            qspread_1s_ge25[
                "spread"
            ],

        "book_qspread_1s_ge25_n":
            qspread_1s_ge25[
                "observations"
            ],

        # ---------------------------------------------------------
        # +1 SECOND HAC
        # ---------------------------------------------------------

        "n_1s":
            regression_1s[
                "observations"
            ],

        "beta_1s":
            regression_1s[
                "beta"
            ],

        "hac_se_1s":
            regression_1s[
                "beta_se"
            ],

        "hac_t_1s":
            regression_1s[
                "beta_t"
            ],

        "hac_p_1s":
            regression_1s[
                "beta_p"
            ],

        "hac_ci_low_1s":
            regression_1s[
                "beta_ci_low"
            ],

        "hac_ci_high_1s":
            regression_1s[
                "beta_ci_high"
            ],

        "r_squared_1s":
            regression_1s[
                "r_squared"
            ],

        # ---------------------------------------------------------
        # +5 SECOND HAC
        # ---------------------------------------------------------

        "beta_5s":
            regression_5s[
                "beta"
            ],

        "hac_p_5s":
            regression_5s[
                "beta_p"
            ],

        "hac_ci_low_5s":
            regression_5s[
                "beta_ci_low"
            ],

        "hac_ci_high_5s":
            regression_5s[
                "beta_ci_high"
            ],

        # ---------------------------------------------------------
        # NON-OVERLAPPING +5 SECOND
        # ---------------------------------------------------------

        "n_5s_nonoverlap":
            nonoverlap_5s[
                "observations"
            ],

        "beta_5s_nonoverlap":
            nonoverlap_5s[
                "beta"
            ],

        "hac_p_5s_nonoverlap":
            nonoverlap_5s[
                "beta_p"
            ],

        "hac_ci_low_5s_nonoverlap":
            nonoverlap_5s[
                "beta_ci_low"
            ],

        "hac_ci_high_5s_nonoverlap":
            nonoverlap_5s[
                "beta_ci_high"
            ],

        # ---------------------------------------------------------
        # >=25 TRADES / SECOND HAC
        # ---------------------------------------------------------

        "n_1s_ge25":
            regression_1s_ge25[
                "observations"
            ],

        "beta_1s_ge25":
            regression_1s_ge25[
                "beta"
            ],

        "hac_p_1s_ge25":
            regression_1s_ge25[
                "beta_p"
            ],

        "hac_ci_low_1s_ge25":
            regression_1s_ge25[
                "beta_ci_low"
            ],

        "hac_ci_high_1s_ge25":
            regression_1s_ge25[
                "beta_ci_high"
            ],

        # ---------------------------------------------------------
        # MOVING-BLOCK BOOTSTRAP
        # ---------------------------------------------------------

        "bootstrap_point_beta":
            bootstrap[
                "point_beta"
            ],

        "bootstrap_mean_beta":
            bootstrap[
                "bootstrap_mean_beta"
            ],

        "bootstrap_ci_low":
            bootstrap[
                "bootstrap_ci_low"
            ],

        "bootstrap_ci_high":
            bootstrap[
                "bootstrap_ci_high"
            ],

        "bootstrap_positive_rate":
            bootstrap[
                "positive_rate"
            ],

        "_bootstrap_slopes":
            bootstrap[
                "slopes"
            ],
    }


# =============================================================================
# CROSS-SESSION STATISTICS
# =============================================================================

def exact_sign_test(
    values,
):

    values = (
        pd.Series(
            values
        )
        .dropna()
    )

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

    total = int(
        len(values)
    )

    if total == 0:

        return {
            "positive": 0,
            "negative": 0,
            "total": 0,
            "p_value": float("nan"),
        }

    result = binomtest(
        k=positive,
        n=total,
        p=0.5,
        alternative="greater",
    )

    return {
        "positive":
            positive,

        "negative":
            negative,

        "total":
            total,

        "p_value":
            float(
                result.pvalue
            ),
    }


def equal_weight_meta_bootstrap(
    session_results,
):

    arrays = []

    for result in session_results:

        slopes = result[
            "_bootstrap_slopes"
        ]

        if (
            isinstance(
                slopes,
                np.ndarray,
            )
            and len(slopes) > 0
        ):

            arrays.append(
                slopes
            )

    if len(arrays) == 0:

        return {
            "sessions": 0,
            "mean": float("nan"),
            "median": float("nan"),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "positive_rate": float("nan"),
        }

    minimum_length = min(
        len(x)
        for x
        in arrays
    )

    stacked = np.vstack(
        [
            x[
                :minimum_length
            ]
            for x
            in arrays
        ]
    )

    equal_weight_means = np.mean(
        stacked,
        axis=0,
    )

    return {
        "sessions":
            len(arrays),

        "mean":
            float(
                np.mean(
                    equal_weight_means
                )
            ),

        "median":
            float(
                np.median(
                    equal_weight_means
                )
            ),

        "ci_low":
            float(
                np.quantile(
                    equal_weight_means,
                    0.025,
                )
            ),

        "ci_high":
            float(
                np.quantile(
                    equal_weight_means,
                    0.975,
                )
            ),

        "positive_rate":
            float(
                np.mean(
                    equal_weight_means
                    > 0
                )
            ),
    }


# =============================================================================
# DEVELOPMENT SAMPLE FOR EFFECT-SIZE COMPARISON
# =============================================================================

def analyze_development_sample():

    rows = []

    for session in DEVELOPMENT_SESSIONS:

        df = load_session(
            session[
                "session_id"
            ]
        )

        q1 = bucket_spread(
            df,
            PRIMARY_SIGNAL,
            TARGET_1S,
        )

        q5 = bucket_spread(
            df,
            PRIMARY_SIGNAL,
            TARGET_5S,
        )

        q25 = bucket_spread(
            df,
            PRIMARY_SIGNAL,
            TARGET_1S,
            minimum_trades=(
                ACTIVITY_THRESHOLD
            ),
        )

        regression = (
            hac_regression(
                df=df,
                signal_col=PRIMARY_SIGNAL,
                target_col=TARGET_1S,
                maxlags=HAC_LAGS_1S,
            )
        )

        rows.append(
            {
                "label":
                    session[
                        "label"
                    ],

                "distinct_period":
                    session[
                        "distinct_period"
                    ],

                "qspread_1s":
                    q1[
                        "spread"
                    ],

                "qspread_5s":
                    q5[
                        "spread"
                    ],

                "qspread_1s_ge25":
                    q25[
                        "spread"
                    ],

                "beta_1s":
                    regression[
                        "beta"
                    ],
            }
        )

    return pd.DataFrame(
        rows
    )


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def rounded_table(
    df,
    columns,
    decimals=4,
):

    output = (
        df[
            columns
        ].copy()
    )

    for column in columns:

        if (
            column in output.columns
            and pd.api.types.is_numeric_dtype(
                output[
                    column
                ]
            )
        ):

            output[
                column
            ] = (
                output[
                    column
                ]
                .round(
                    decimals
                )
            )

    return output


# =============================================================================
# MAIN
# =============================================================================

def main():

    verify_protocol()

    print()
    print("=" * 100)
    print(
        "BTCUSDT PRE-REGISTERED HOLDOUT VALIDATION"
    )
    print("=" * 100)

    print(
        f"Primary signal:       "
        f"{PRIMARY_SIGNAL}"
    )

    print(
        "Primary horizon:      +1 second"
    )

    print(
        "Secondary horizon:    +5 seconds"
    )

    print(
        f"Quantile count:       "
        f"{QUANTILE_COUNT}"
    )

    print(
        f"HAC lags:             "
        f"+1s={HAC_LAGS_1S}, "
        f"+5s={HAC_LAGS_5S}"
    )

    print(
        f"Activity condition:   "
        f">={ACTIVITY_THRESHOLD} "
        f"trades/second"
    )

    print(
        f"Bootstrap:            "
        f"{BOOTSTRAP_REPETITIONS} reps, "
        f"{BOOTSTRAP_BLOCK_LENGTH}-second blocks"
    )

    # =========================================================================
    # HOLDOUT SESSION ANALYSIS
    # =========================================================================

    holdout_results = []

    print()

    for index, session in enumerate(
        HOLDOUT_SESSIONS
    ):

        print(
            f"Analyzing "
            f"{session['label']}: "
            f"{session['session_id']}"
        )

        result = analyze_session(
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
            seed=(
                BOOTSTRAP_RANDOM_SEED
                + index
            ),
        )

        holdout_results.append(
            result
        )

    clean_rows = []

    for result in holdout_results:

        clean_rows.append(
            {
                key: value
                for key, value
                in result.items()
                if key
                != "_bootstrap_slopes"
            }
        )

    holdout_df = pd.DataFrame(
        clean_rows
    )

    holdout_df.to_csv(
        SESSION_OUTPUT_FILE,
        index=False,
    )

    # =========================================================================
    # SESSION DESCRIPTIVES
    # =========================================================================

    print()
    print("=" * 100)
    print(
        "HOLDOUT MARKET REGIMES"
    )
    print("=" * 100)

    print(
        rounded_table(
            holdout_df,
            [
                "label",
                "observations",
                "mid_price_move_bps",
                "zero_trade_seconds",
                "seconds_ge25_trades",
            ],
        ).to_string(
            index=False
        )
    )

    # =========================================================================
    # FROZEN BUCKET RESULTS
    # =========================================================================

    print()
    print("=" * 100)
    print(
        "FROZEN BOOK-IMBALANCE QUINTILE SPREADS"
    )
    print("=" * 100)

    print(
        rounded_table(
            holdout_df,
            [
                "label",
                "book_qspread_1s_bps",
                "book_qspread_5s_bps",
                "book_qspread_1s_ge25_bps",
                "book_qspread_1s_ge25_n",
            ],
        ).to_string(
            index=False
        )
    )

    # =========================================================================
    # +1 SECOND HAC
    # =========================================================================

    print()
    print("=" * 100)
    print(
        "PRIMARY TEST: +1 SECOND HAC / NEWEY-WEST REGRESSION"
    )
    print("=" * 100)

    print(
        rounded_table(
            holdout_df,
            [
                "label",
                "n_1s",
                "beta_1s",
                "hac_se_1s",
                "hac_t_1s",
                "hac_p_1s",
                "hac_ci_low_1s",
                "hac_ci_high_1s",
                "r_squared_1s",
            ],
        ).to_string(
            index=False
        )
    )

    # =========================================================================
    # +5 SECOND HAC + NON-OVERLAPPING
    # =========================================================================

    print()
    print("=" * 100)
    print(
        "+5 SECOND OVERLAPPING VS NON-OVERLAPPING SENSITIVITY"
    )
    print("=" * 100)

    print(
        rounded_table(
            holdout_df,
            [
                "label",
                "beta_5s",
                "hac_p_5s",
                "beta_5s_nonoverlap",
                "hac_p_5s_nonoverlap",
                "n_5s_nonoverlap",
            ],
        ).to_string(
            index=False
        )
    )

    # =========================================================================
    # >=25 TRADES / SECOND
    # =========================================================================

    print()
    print("=" * 100)
    print(
        "FROZEN HIGH-ACTIVITY CONDITION: +1S WITH >=25 TRADES/SECOND"
    )
    print("=" * 100)

    print(
        rounded_table(
            holdout_df,
            [
                "label",
                "n_1s_ge25",
                "beta_1s_ge25",
                "hac_p_1s_ge25",
                "hac_ci_low_1s_ge25",
                "hac_ci_high_1s_ge25",
            ],
        ).to_string(
            index=False
        )
    )

    # =========================================================================
    # BLOCK BOOTSTRAP
    # =========================================================================

    print()
    print("=" * 100)
    print(
        "FROZEN +1 SECOND MOVING-BLOCK BOOTSTRAP"
    )
    print("=" * 100)

    print(
        rounded_table(
            holdout_df,
            [
                "label",
                "bootstrap_point_beta",
                "bootstrap_mean_beta",
                "bootstrap_ci_low",
                "bootstrap_ci_high",
                "bootstrap_positive_rate",
            ],
        ).to_string(
            index=False
        )
    )

    # =========================================================================
    # SIGN CONSISTENCY
    # =========================================================================

    beta_sign_test = (
        exact_sign_test(
            holdout_df[
                "beta_1s"
            ]
        )
    )

    qspread_sign_test = (
        exact_sign_test(
            holdout_df[
                "book_qspread_1s_bps"
            ]
        )
    )

    print()
    print("=" * 100)
    print(
        "HOLDOUT SESSION-LEVEL SIGN CONSISTENCY"
    )
    print("=" * 100)

    print(
        "Primary +1s regression beta:"
    )

    print(
        f"  Positive sessions: "
        f"{beta_sign_test['positive']} / "
        f"{beta_sign_test['total']}"
    )

    print(
        f"  Negative sessions: "
        f"{beta_sign_test['negative']} / "
        f"{beta_sign_test['total']}"
    )

    print(
        f"  Exact one-sided sign-test p-value: "
        f"{beta_sign_test['p_value']:.6f}"
    )

    print()

    print(
        "+1s quintile spread:"
    )

    print(
        f"  Positive sessions: "
        f"{qspread_sign_test['positive']} / "
        f"{qspread_sign_test['total']}"
    )

    print(
        f"  Negative sessions: "
        f"{qspread_sign_test['negative']} / "
        f"{qspread_sign_test['total']}"
    )

    print(
        f"  Exact one-sided sign-test p-value: "
        f"{qspread_sign_test['p_value']:.6f}"
    )

    # =========================================================================
    # EQUAL-WEIGHT HOLDOUT SUMMARY
    # =========================================================================

    print()
    print("=" * 100)
    print(
        "EQUAL-WEIGHT HOLDOUT EFFECT-SIZE SUMMARY"
    )
    print("=" * 100)

    metrics = [
        (
            "book_qspread_1s_bps",
            "+1s Q-high minus Q-low",
        ),
        (
            "book_qspread_5s_bps",
            "+5s Q-high minus Q-low",
        ),
        (
            "book_qspread_1s_ge25_bps",
            "+1s Q-spread >=25 trades/sec",
        ),
        (
            "beta_1s",
            "+1s regression beta",
        ),
    ]

    for column, label in metrics:

        values = (
            holdout_df[
                column
            ]
            .dropna()
        )

        print()

        print(
            label
        )

        print(
            f"  Sessions:   "
            f"{len(values)}"
        )

        print(
            f"  Mean:       "
            f"{values.mean():+.4f}"
        )

        print(
            f"  Median:     "
            f"{values.median():+.4f}"
        )

        print(
            f"  Minimum:    "
            f"{values.min():+.4f}"
        )

        print(
            f"  Maximum:    "
            f"{values.max():+.4f}"
        )

    # =========================================================================
    # EQUAL-WEIGHT BLOCK BOOTSTRAP
    # =========================================================================

    meta_bootstrap = (
        equal_weight_meta_bootstrap(
            holdout_results
        )
    )

    print()
    print("=" * 100)
    print(
        "EQUAL-WEIGHT HOLDOUT BLOCK-BOOTSTRAP SUMMARY"
    )
    print("=" * 100)

    print(
        f"Sessions:               "
        f"{meta_bootstrap['sessions']}"
    )

    print(
        f"Bootstrap mean beta:    "
        f"{meta_bootstrap['mean']:+.4f}"
    )

    print(
        f"Bootstrap median beta:  "
        f"{meta_bootstrap['median']:+.4f}"
    )

    print(
        f"95% interval:           "
        f"[{meta_bootstrap['ci_low']:+.4f}, "
        f"{meta_bootstrap['ci_high']:+.4f}]"
    )

    print(
        f"Positive rate:          "
        f"{meta_bootstrap['positive_rate']:.4f}"
    )

    # =========================================================================
    # DEVELOPMENT VS HOLDOUT
    # =========================================================================

    development_df = (
        analyze_development_sample()
    )

    development_conservative_df = (
        development_df[
            development_df[
                "distinct_period"
            ]
        ].copy()
    )

    comparison_rows = []

    comparison_metrics = [
        (
            "qspread_1s",
            "book_qspread_1s_bps",
            "+1s Q-spread",
        ),
        (
            "qspread_5s",
            "book_qspread_5s_bps",
            "+5s Q-spread",
        ),
        (
            "qspread_1s_ge25",
            "book_qspread_1s_ge25_bps",
            "+1s Q-spread >=25",
        ),
        (
            "beta_1s",
            "beta_1s",
            "+1s regression beta",
        ),
    ]

    print()
    print("=" * 100)
    print(
        "EXPLORATORY DEVELOPMENT VS PRE-REGISTERED HOLDOUT"
    )
    print("=" * 100)

    for (
        development_column,
        holdout_column,
        metric_name,
    ) in comparison_metrics:

        development_values = (
            development_df[
                development_column
            ]
            .dropna()
        )

        conservative_values = (
            development_conservative_df[
                development_column
            ]
            .dropna()
        )

        holdout_values = (
            holdout_df[
                holdout_column
            ]
            .dropna()
        )

        development_mean = (
            development_values.mean()
        )

        conservative_mean = (
            conservative_values.mean()
        )

        holdout_mean = (
            holdout_values.mean()
        )

        if development_mean != 0:

            holdout_to_development_ratio = (
                holdout_mean
                / development_mean
            )

        else:

            holdout_to_development_ratio = (
                float("nan")
            )

        comparison_rows.append(
            {
                "metric":
                    metric_name,

                "development_all_mean":
                    development_mean,

                "development_conservative_mean":
                    conservative_mean,

                "holdout_mean":
                    holdout_mean,

                "holdout_median":
                    holdout_values.median(),

                "holdout_to_development_ratio":
                    holdout_to_development_ratio,
            }
        )

    comparison_df = pd.DataFrame(
        comparison_rows
    )

    print(
        rounded_table(
            comparison_df,
            [
                "metric",
                "development_all_mean",
                "development_conservative_mean",
                "holdout_mean",
                "holdout_median",
                "holdout_to_development_ratio",
            ],
        ).to_string(
            index=False
        )
    )

    comparison_df.to_csv(
        COMPARISON_OUTPUT_FILE,
        index=False,
    )

    # =========================================================================
    # SAVE SUMMARY
    # =========================================================================

    summary_df = pd.DataFrame(
        [
            {
                "sample":
                    "pre_registered_holdout",

                "sessions":
                    len(
                        holdout_df
                    ),

                "positive_beta_sessions":
                    beta_sign_test[
                        "positive"
                    ],

                "beta_sign_test_p_value":
                    beta_sign_test[
                        "p_value"
                    ],

                "positive_qspread_sessions":
                    qspread_sign_test[
                        "positive"
                    ],

                "qspread_sign_test_p_value":
                    qspread_sign_test[
                        "p_value"
                    ],

                "mean_qspread_1s_bps":
                    holdout_df[
                        "book_qspread_1s_bps"
                    ].mean(),

                "median_qspread_1s_bps":
                    holdout_df[
                        "book_qspread_1s_bps"
                    ].median(),

                "mean_qspread_5s_bps":
                    holdout_df[
                        "book_qspread_5s_bps"
                    ].mean(),

                "mean_qspread_1s_ge25_bps":
                    holdout_df[
                        "book_qspread_1s_ge25_bps"
                    ].mean(),

                "mean_beta_1s":
                    holdout_df[
                        "beta_1s"
                    ].mean(),

                "median_beta_1s":
                    holdout_df[
                        "beta_1s"
                    ].median(),

                "meta_bootstrap_mean_beta":
                    meta_bootstrap[
                        "mean"
                    ],

                "meta_bootstrap_ci_low":
                    meta_bootstrap[
                        "ci_low"
                    ],

                "meta_bootstrap_ci_high":
                    meta_bootstrap[
                        "ci_high"
                    ],

                "meta_bootstrap_positive_rate":
                    meta_bootstrap[
                        "positive_rate"
                    ],
            }
        ]
    )

    summary_df.to_csv(
        SUMMARY_OUTPUT_FILE,
        index=False,
    )

    # =========================================================================
    # OUTPUT
    # =========================================================================

    print()
    print("=" * 100)
    print("OUTPUT")
    print("=" * 100)

    print(
        "Session-level holdout results:"
    )

    print(
        SESSION_OUTPUT_FILE
    )

    print()

    print(
        "Holdout summary:"
    )

    print(
        SUMMARY_OUTPUT_FILE
    )

    print()

    print(
        "Development-vs-holdout comparison:"
    )

    print(
        COMPARISON_OUTPUT_FILE
    )

    # =========================================================================
    # INTERPRETATION GUARDRAIL
    # =========================================================================

    print()
    print("=" * 100)
    print("INTERPRETATION GUARDRAIL")
    print("=" * 100)

    print(
        "These five sessions were collected after the "
        "validation protocol was frozen and SHA-256 fingerprinted."
    )

    print()

    print(
        "No signal definition, prediction horizon, activity threshold, "
        "quantile specification, HAC lag, or bootstrap setting was "
        "changed in response to holdout performance."
    )

    print()

    print(
        "A positive out-of-sample result supports predictive robustness "
        "of the statistical relationship, but does NOT establish "
        "executable alpha."
    )

    print()

    print(
        "The next research stage, if the holdout survives, is economic "
        "validation under spread, fees, latency, slippage, adverse "
        "selection, fill uncertainty, turnover, and inventory risk."
    )


if __name__ == "__main__":
    main()