from pathlib import Path
from datetime import datetime, timezone
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

SESSION_OUTPUT_FILE = (
    PROCESSED_DIR
    / "statistical_validation_session_results.csv"
)

SUMMARY_OUTPUT_FILE = (
    PROCESSED_DIR
    / "statistical_validation_summary.csv"
)


# =============================================================================
# FROZEN ROBUSTNESS SESSIONS
# =============================================================================

ROBUSTNESS_SESSIONS = [
    {
        "session_id": "20260824_135129",
        "label": "afternoon_1",
        "conservative_distinct_period": True,
    },
    {
        "session_id": "20260825_084855",
        "label": "morning_1",
        "conservative_distinct_period": True,
    },
    {
        "session_id": "20260826_085550",
        "label": "morning_2",
        "conservative_distinct_period": True,
    },
    {
        "session_id": "20260826_144545",
        "label": "evening_1",
        "conservative_distinct_period": True,
    },
    {
        "session_id": "20260826_151328",
        "label": "late_afternoon_1",
        "conservative_distinct_period": False,
    },
]


# =============================================================================
# FROZEN ANALYSIS SETTINGS
# =============================================================================

PRIMARY_SIGNAL = "median_book_imbalance"

TARGET_1S = "future_return_1s_bps"
TARGET_5S = "future_return_5s_bps"

HAC_LAGS_1S = 5
HAC_LAGS_5S = 10

NONOVERLAP_HAC_LAGS = 1

ACTIVITY_THRESHOLD = 25

BOOTSTRAP_REPETITIONS = 1000
BOOTSTRAP_BLOCK_LENGTH = 30
BOOTSTRAP_RANDOM_SEED = 42


# =============================================================================
# HELPERS
# =============================================================================

def parse_session_start_utc(session_id):
    """
    Parse session ID:

        YYYYMMDD_HHMMSS

    Session IDs are generated in UTC.
    """

    parsed = datetime.strptime(
        session_id,
        "%Y%m%d_%H%M%S",
    )

    return parsed.replace(
        tzinfo=timezone.utc
    )


def load_session(session_id):
    """
    Load one processed one-second feature dataset.
    """

    feature_file = (
        PROCESSED_DIR
        / f"btcusdt_features_{session_id}.csv"
    )

    if not feature_file.exists():
        raise FileNotFoundError(
            f"Missing feature file:\n"
            f"{feature_file}"
        )

    return pd.read_csv(
        feature_file
    )


def prepare_regression_data(
    df,
    signal_col,
    target_col,
    minimum_trades=None,
):
    """
    Prepare valid observations for regression.

    No signal transformation or winsorization is applied.
    """

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
    """
    OLS:

        future return
            =
        alpha
            +
        beta * book imbalance
            +
        error

    Standard errors are HAC / Newey-West.
    """

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

    y = data[
        target_col
    ].astype(float)

    x = sm.add_constant(
        data[
            [signal_col]
        ].astype(float),
        has_constant="add",
    )

    model = sm.OLS(
        y,
        x,
    ).fit(
        cov_type="HAC",
        cov_kwds={
            "maxlags": maxlags,
            "use_correction": True,
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
            int(model.nobs),

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
# NON-OVERLAPPING +5 SECOND SENSITIVITY CHECK
# =============================================================================

def nonoverlapping_5s_regression(df):
    """
    The ordinary +5 second target overlaps heavily:

        t -> t+5
        t+1 -> t+6
        t+2 -> t+7
        ...

    For this sensitivity analysis we retain every fifth
    eligible observation:

        t
        t+5
        t+10
        ...

    This substantially reduces mechanical overlap.
    """

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
            "alpha": float("nan"),
            "beta": float("nan"),
            "beta_se": float("nan"),
            "beta_t": float("nan"),
            "beta_p": float("nan"),
            "beta_ci_low": float("nan"),
            "beta_ci_high": float("nan"),
            "r_squared": float("nan"),
        }

    y = data[
        TARGET_5S
    ].astype(float)

    x = sm.add_constant(
        data[
            [PRIMARY_SIGNAL]
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
            int(model.nobs),

        "alpha":
            float(
                model.params[
                    "const"
                ]
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

        "r_squared":
            float(
                model.rsquared
            ),
    }


# =============================================================================
# MOVING-BLOCK BOOTSTRAP
# =============================================================================

def ols_slope(
    x,
    y,
):
    """
    Closed-form OLS slope.

    Used inside the bootstrap for computational efficiency.
    """

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
            x - x_mean
        ) ** 2
    )

    if denominator <= 0:
        return float("nan")

    numerator = np.sum(
        (
            x - x_mean
        )
        *
        (
            y - y_mean
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
    """
    Moving-block bootstrap for the +1 second book-imbalance slope.

    Blocks preserve short-range temporal dependence.

    Frozen settings:

        block length = 30 seconds
        repetitions  = 1000
    """

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

    n = len(
        data
    )

    block_length = min(
        BOOTSTRAP_BLOCK_LENGTH,
        n,
    )

    if n < 30:
        return {
            "observations": n,
            "point_beta": float("nan"),
            "bootstrap_mean_beta": float("nan"),
            "bootstrap_median_beta": float("nan"),
            "bootstrap_ci_low": float("nan"),
            "bootstrap_ci_high": float("nan"),
            "positive_bootstrap_rate": float("nan"),
            "bootstrap_slopes": np.array([]),
        }

    rng = np.random.default_rng(
        seed
    )

    point_beta = ols_slope(
        x,
        y,
    )

    maximum_start = (
        n
        - block_length
    )

    number_of_blocks = math.ceil(
        n
        / block_length
    )

    bootstrap_slopes = []

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
            block_indices = np.arange(
                start,
                start + block_length,
            )

            indices.extend(
                block_indices.tolist()
            )

        indices = np.asarray(
            indices[:n]
        )

        bootstrap_beta = ols_slope(
            x[
                indices
            ],
            y[
                indices
            ],
        )

        if not np.isnan(
            bootstrap_beta
        ):
            bootstrap_slopes.append(
                bootstrap_beta
            )

    bootstrap_slopes = np.asarray(
        bootstrap_slopes,
        dtype=float,
    )

    if len(
        bootstrap_slopes
    ) == 0:
        return {
            "observations": n,
            "point_beta": point_beta,
            "bootstrap_mean_beta": float("nan"),
            "bootstrap_median_beta": float("nan"),
            "bootstrap_ci_low": float("nan"),
            "bootstrap_ci_high": float("nan"),
            "positive_bootstrap_rate": float("nan"),
            "bootstrap_slopes": np.array([]),
        }

    ci_low = np.quantile(
        bootstrap_slopes,
        0.025,
    )

    ci_high = np.quantile(
        bootstrap_slopes,
        0.975,
    )

    positive_rate = np.mean(
        bootstrap_slopes
        > 0
    )

    return {
        "observations":
            n,

        "point_beta":
            point_beta,

        "bootstrap_mean_beta":
            float(
                np.mean(
                    bootstrap_slopes
                )
            ),

        "bootstrap_median_beta":
            float(
                np.median(
                    bootstrap_slopes
                )
            ),

        "bootstrap_ci_low":
            float(
                ci_low
            ),

        "bootstrap_ci_high":
            float(
                ci_high
            ),

        "positive_bootstrap_rate":
            float(
                positive_rate
            ),

        "bootstrap_slopes":
            bootstrap_slopes,
    }


# =============================================================================
# SESSION ANALYSIS
# =============================================================================

def analyze_one_session(
    session,
    session_index,
):
    """
    Run every frozen statistical check for one session.
    """

    session_id = (
        session[
            "session_id"
        ]
    )

    label = (
        session[
            "label"
        ]
    )

    df = load_session(
        session_id
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

    regression_5s_nonoverlap = (
        nonoverlapping_5s_regression(
            df
        )
    )

    bootstrap = (
        moving_block_bootstrap(
            df=df,
            seed=(
                BOOTSTRAP_RANDOM_SEED
                + session_index
            ),
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

        "conservative_distinct_period":
            session[
                "conservative_distinct_period"
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

        "n_5s":
            regression_5s[
                "observations"
            ],

        "beta_5s":
            regression_5s[
                "beta"
            ],

        "hac_se_5s":
            regression_5s[
                "beta_se"
            ],

        "hac_t_5s":
            regression_5s[
                "beta_t"
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

        "r_squared_5s":
            regression_5s[
                "r_squared"
            ],

        # ---------------------------------------------------------
        # NON-OVERLAPPING +5 SECOND CHECK
        # ---------------------------------------------------------

        "n_5s_nonoverlap":
            regression_5s_nonoverlap[
                "observations"
            ],

        "beta_5s_nonoverlap":
            regression_5s_nonoverlap[
                "beta"
            ],

        "hac_se_5s_nonoverlap":
            regression_5s_nonoverlap[
                "beta_se"
            ],

        "hac_p_5s_nonoverlap":
            regression_5s_nonoverlap[
                "beta_p"
            ],

        "hac_ci_low_5s_nonoverlap":
            regression_5s_nonoverlap[
                "beta_ci_low"
            ],

        "hac_ci_high_5s_nonoverlap":
            regression_5s_nonoverlap[
                "beta_ci_high"
            ],

        # ---------------------------------------------------------
        # >=25 TRADES / SECOND
        # ---------------------------------------------------------

        "n_1s_ge25":
            regression_1s_ge25[
                "observations"
            ],

        "beta_1s_ge25":
            regression_1s_ge25[
                "beta"
            ],

        "hac_se_1s_ge25":
            regression_1s_ge25[
                "beta_se"
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
        # BLOCK BOOTSTRAP
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
                "positive_bootstrap_rate"
            ],

        "_bootstrap_slopes":
            bootstrap[
                "bootstrap_slopes"
            ],
    }


# =============================================================================
# CROSS-SESSION SUMMARIES
# =============================================================================

def sign_consistency_test(
    values,
):
    """
    Exact one-sided sign test.

    Null:
        P(positive coefficient) = 0.5

    Alternative:
        P(positive coefficient) > 0.5
    """

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

    total = len(
        values
    )

    if total == 0:
        return {
            "positive": 0,
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

        "total":
            total,

        "p_value":
            float(
                result.pvalue
            ),
    }


def meta_bootstrap(
    session_results,
):
    """
    Combine session-level moving-block bootstrap slopes.

    Each session receives equal weight.

    This is NOT a pooled second-level bootstrap.
    """

    bootstrap_arrays = []

    for result in session_results:

        values = result[
            "_bootstrap_slopes"
        ]

        if (
            isinstance(
                values,
                np.ndarray,
            )
            and len(values) > 0
        ):
            bootstrap_arrays.append(
                values
            )

    if len(
        bootstrap_arrays
    ) == 0:
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
        in bootstrap_arrays
    )

    stacked = np.vstack(
        [
            x[:minimum_length]
            for x
            in bootstrap_arrays
        ]
    )

    equal_weight_means = np.mean(
        stacked,
        axis=0,
    )

    return {
        "sessions":
            len(
                bootstrap_arrays
            ),

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


def print_session_table(
    results_df,
):
    """
    Main HAC results.
    """

    columns = [
        "label",
        "beta_1s",
        "hac_se_1s",
        "hac_t_1s",
        "hac_p_1s",
        "hac_ci_low_1s",
        "hac_ci_high_1s",
        "r_squared_1s",
    ]

    output = (
        results_df[
            columns
        ].copy()
    )

    numeric = (
        columns[1:]
    )

    output[
        numeric
    ] = (
        output[
            numeric
        ].round(4)
    )

    print(
        output.to_string(
            index=False
        )
    )


def print_5s_table(
    results_df,
):
    """
    Overlapping and non-overlapping +5s comparison.
    """

    columns = [
        "label",
        "beta_5s",
        "hac_p_5s",
        "beta_5s_nonoverlap",
        "hac_p_5s_nonoverlap",
        "n_5s_nonoverlap",
    ]

    output = (
        results_df[
            columns
        ].copy()
    )

    for col in [
        "beta_5s",
        "hac_p_5s",
        "beta_5s_nonoverlap",
        "hac_p_5s_nonoverlap",
    ]:
        output[
            col
        ] = (
            output[
                col
            ].round(4)
        )

    print(
        output.to_string(
            index=False
        )
    )


def print_activity_table(
    results_df,
):
    """
    >=25 trades/second sensitivity analysis.
    """

    columns = [
        "label",
        "n_1s_ge25",
        "beta_1s_ge25",
        "hac_se_1s_ge25",
        "hac_p_1s_ge25",
        "hac_ci_low_1s_ge25",
        "hac_ci_high_1s_ge25",
    ]

    output = (
        results_df[
            columns
        ].copy()
    )

    for col in (
        columns[2:]
    ):
        output[
            col
        ] = (
            output[
                col
            ].round(4)
        )

    print(
        output.to_string(
            index=False
        )
    )


def print_bootstrap_table(
    results_df,
):
    """
    Moving-block bootstrap results.
    """

    columns = [
        "label",
        "bootstrap_point_beta",
        "bootstrap_mean_beta",
        "bootstrap_ci_low",
        "bootstrap_ci_high",
        "bootstrap_positive_rate",
    ]

    output = (
        results_df[
            columns
        ].copy()
    )

    for col in (
        columns[1:]
    ):
        output[
            col
        ] = (
            output[
                col
            ].round(4)
        )

    print(
        output.to_string(
            index=False
        )
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 96)
    print(
        "BTCUSDT BOOK-IMBALANCE "
        "STATISTICAL VALIDATION"
    )
    print("=" * 96)

    print()
    print(
        "Frozen primary signal: "
        f"{PRIMARY_SIGNAL}"
    )

    print(
        "Frozen targets: "
        "+1s and +5s future mid-price returns"
    )

    print(
        f"HAC lags: "
        f"+1s={HAC_LAGS_1S}, "
        f"+5s={HAC_LAGS_5S}"
    )

    print(
        f"Activity sensitivity: "
        f">={ACTIVITY_THRESHOLD} "
        f"trades/second"
    )

    print(
        f"Moving-block bootstrap: "
        f"{BOOTSTRAP_REPETITIONS} repetitions, "
        f"{BOOTSTRAP_BLOCK_LENGTH}-second blocks"
    )

    print()

    session_results = []

    for index, session in enumerate(
        ROBUSTNESS_SESSIONS
    ):

        print(
            f"Analyzing "
            f"{session['label']}: "
            f"{session['session_id']}"
        )

        result = analyze_one_session(
            session=session,
            session_index=index,
        )

        session_results.append(
            result
        )

    # -------------------------------------------------------------------------
    # DATAFRAME WITHOUT LARGE BOOTSTRAP ARRAYS
    # -------------------------------------------------------------------------

    clean_rows = []

    for result in session_results:

        row = {
            key: value
            for key, value
            in result.items()
            if key
            != "_bootstrap_slopes"
        }

        clean_rows.append(
            row
        )

    results_df = pd.DataFrame(
        clean_rows
    )

    results_df.to_csv(
        SESSION_OUTPUT_FILE,
        index=False,
    )

    # -------------------------------------------------------------------------
    # +1 SECOND HAC
    # -------------------------------------------------------------------------

    print()
    print("=" * 96)
    print(
        "+1 SECOND HAC / NEWEY-WEST REGRESSIONS"
    )
    print("=" * 96)

    print_session_table(
        results_df
    )

    # -------------------------------------------------------------------------
    # +5 SECOND SENSITIVITY
    # -------------------------------------------------------------------------

    print()
    print("=" * 96)
    print(
        "+5 SECOND OVERLAPPING VS "
        "NON-OVERLAPPING SENSITIVITY"
    )
    print("=" * 96)

    print_5s_table(
        results_df
    )

    # -------------------------------------------------------------------------
    # HIGH-ACTIVITY CONDITION
    # -------------------------------------------------------------------------

    print()
    print("=" * 96)
    print(
        "+1 SECOND HAC WITH "
        ">=25 TRADES/SECOND"
    )
    print("=" * 96)

    print_activity_table(
        results_df
    )

    # -------------------------------------------------------------------------
    # BLOCK BOOTSTRAP
    # -------------------------------------------------------------------------

    print()
    print("=" * 96)
    print(
        "+1 SECOND MOVING-BLOCK BOOTSTRAP"
    )
    print("=" * 96)

    print_bootstrap_table(
        results_df
    )

    # -------------------------------------------------------------------------
    # SIGN CONSISTENCY
    # -------------------------------------------------------------------------

    all_sign_test = sign_consistency_test(
        results_df[
            "beta_1s"
        ]
    )

    conservative_df = (
        results_df[
            results_df[
                "conservative_distinct_period"
            ]
        ].copy()
    )

    conservative_sign_test = (
        sign_consistency_test(
            conservative_df[
                "beta_1s"
            ]
        )
    )

    print()
    print("=" * 96)
    print(
        "SESSION-LEVEL SIGN CONSISTENCY"
    )
    print("=" * 96)

    print(
        "All valid windows:"
    )

    print(
        f"  Positive beta: "
        f"{all_sign_test['positive']} / "
        f"{all_sign_test['total']}"
    )

    print(
        f"  Exact one-sided sign-test p-value: "
        f"{all_sign_test['p_value']:.6f}"
    )

    print()

    print(
        "Conservative time-separated set:"
    )

    print(
        f"  Positive beta: "
        f"{conservative_sign_test['positive']} / "
        f"{conservative_sign_test['total']}"
    )

    print(
        f"  Exact one-sided sign-test p-value: "
        f"{conservative_sign_test['p_value']:.6f}"
    )

    # -------------------------------------------------------------------------
    # EQUAL-WEIGHT SESSION SUMMARY
    # -------------------------------------------------------------------------

    beta_values = (
        results_df[
            "beta_1s"
        ]
        .dropna()
    )

    conservative_betas = (
        conservative_df[
            "beta_1s"
        ]
        .dropna()
    )

    print()
    print("=" * 96)
    print(
        "EQUAL-WEIGHT SESSION-LEVEL "
        "+1 SECOND BETA SUMMARY"
    )
    print("=" * 96)

    print(
        f"All-window mean beta:       "
        f"{beta_values.mean():+.4f} bps"
    )

    print(
        f"All-window median beta:     "
        f"{beta_values.median():+.4f} bps"
    )

    print(
        f"All-window minimum beta:    "
        f"{beta_values.min():+.4f} bps"
    )

    print(
        f"All-window maximum beta:    "
        f"{beta_values.max():+.4f} bps"
    )

    print()

    print(
        f"Conservative mean beta:     "
        f"{conservative_betas.mean():+.4f} bps"
    )

    print(
        f"Conservative median beta:   "
        f"{conservative_betas.median():+.4f} bps"
    )

    # -------------------------------------------------------------------------
    # META BLOCK BOOTSTRAP
    # -------------------------------------------------------------------------

    all_meta_bootstrap = (
        meta_bootstrap(
            session_results
        )
    )

    conservative_results = [
        result
        for result
        in session_results
        if result[
            "conservative_distinct_period"
        ]
    ]

    conservative_meta_bootstrap = (
        meta_bootstrap(
            conservative_results
        )
    )

    print()
    print("=" * 96)
    print(
        "EQUAL-WEIGHT CROSS-SESSION "
        "BLOCK-BOOTSTRAP SUMMARY"
    )
    print("=" * 96)

    print(
        "All five valid windows:"
    )

    print(
        f"  Sessions:               "
        f"{all_meta_bootstrap['sessions']}"
    )

    print(
        f"  Bootstrap mean beta:    "
        f"{all_meta_bootstrap['mean']:+.4f}"
    )

    print(
        f"  Bootstrap median beta:  "
        f"{all_meta_bootstrap['median']:+.4f}"
    )

    print(
        f"  95% interval:           "
        f"[{all_meta_bootstrap['ci_low']:+.4f}, "
        f"{all_meta_bootstrap['ci_high']:+.4f}]"
    )

    print(
        f"  Positive rate:          "
        f"{all_meta_bootstrap['positive_rate']:.4f}"
    )

    print()

    print(
        "Conservative four-period set:"
    )

    print(
        f"  Sessions:               "
        f"{conservative_meta_bootstrap['sessions']}"
    )

    print(
        f"  Bootstrap mean beta:    "
        f"{conservative_meta_bootstrap['mean']:+.4f}"
    )

    print(
        f"  Bootstrap median beta:  "
        f"{conservative_meta_bootstrap['median']:+.4f}"
    )

    print(
        f"  95% interval:           "
        f"[{conservative_meta_bootstrap['ci_low']:+.4f}, "
        f"{conservative_meta_bootstrap['ci_high']:+.4f}]"
    )

    print(
        f"  Positive rate:          "
        f"{conservative_meta_bootstrap['positive_rate']:.4f}"
    )

    # -------------------------------------------------------------------------
    # SAVE SUMMARY
    # -------------------------------------------------------------------------

    summary_rows = [
        {
            "sample":
                "all_valid_windows",

            "sessions":
                len(
                    beta_values
                ),

            "mean_beta_1s":
                beta_values.mean(),

            "median_beta_1s":
                beta_values.median(),

            "positive_sessions":
                all_sign_test[
                    "positive"
                ],

            "sign_test_p_value":
                all_sign_test[
                    "p_value"
                ],

            "meta_bootstrap_mean":
                all_meta_bootstrap[
                    "mean"
                ],

            "meta_bootstrap_ci_low":
                all_meta_bootstrap[
                    "ci_low"
                ],

            "meta_bootstrap_ci_high":
                all_meta_bootstrap[
                    "ci_high"
                ],

            "meta_bootstrap_positive_rate":
                all_meta_bootstrap[
                    "positive_rate"
                ],
        },
        {
            "sample":
                "conservative_time_separated",

            "sessions":
                len(
                    conservative_betas
                ),

            "mean_beta_1s":
                conservative_betas.mean(),

            "median_beta_1s":
                conservative_betas.median(),

            "positive_sessions":
                conservative_sign_test[
                    "positive"
                ],

            "sign_test_p_value":
                conservative_sign_test[
                    "p_value"
                ],

            "meta_bootstrap_mean":
                conservative_meta_bootstrap[
                    "mean"
                ],

            "meta_bootstrap_ci_low":
                conservative_meta_bootstrap[
                    "ci_low"
                ],

            "meta_bootstrap_ci_high":
                conservative_meta_bootstrap[
                    "ci_high"
                ],

            "meta_bootstrap_positive_rate":
                conservative_meta_bootstrap[
                    "positive_rate"
                ],
        },
    ]

    summary_df = pd.DataFrame(
        summary_rows
    )

    summary_df.to_csv(
        SUMMARY_OUTPUT_FILE,
        index=False,
    )

    # -------------------------------------------------------------------------
    # OUTPUT
    # -------------------------------------------------------------------------

    print()
    print("=" * 96)
    print("OUTPUT")
    print("=" * 96)

    print(
        "Session results saved to:"
    )

    print(
        SESSION_OUTPUT_FILE
    )

    print()

    print(
        "Cross-session summary saved to:"
    )

    print(
        SUMMARY_OUTPUT_FILE
    )

    # -------------------------------------------------------------------------
    # INTERPRETATION WARNING
    # -------------------------------------------------------------------------

    print()
    print("=" * 96)
    print("IMPORTANT")
    print("=" * 96)

    print(
        "This script evaluates a signal definition "
        "that was frozen before this inferential stage."
    )

    print()

    print(
        "HAC standard errors address short-range "
        "serial dependence within each session."
    )

    print()

    print(
        "The non-overlapping +5 second analysis "
        "reduces mechanical return overlap."
    )

    print()

    print(
        "The moving-block bootstrap preserves "
        "local temporal dependence within sessions."
    )

    print()

    print(
        "Sessions are equal-weighted rather than "
        "pooling all one-second observations."
    )

    print()

    print(
        "The conservative analysis excludes the "
        "late_afternoon_1 window from the independent-"
        "period count because it began only about "
        "28 minutes after evening_1."
    )

    print()

    print(
        "Even statistically persistent predictability "
        "is NOT evidence of executable alpha."
    )

    print()

    print(
        "Fees, bid-ask execution, latency, slippage, "
        "inventory risk, and out-of-sample validation "
        "have not yet been incorporated."
    )


if __name__ == "__main__":
    main()