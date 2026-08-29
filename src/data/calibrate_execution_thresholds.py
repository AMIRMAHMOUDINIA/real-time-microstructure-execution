from pathlib import Path
from datetime import datetime, timezone
import hashlib

import pandas as pd


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

EXECUTION_PROTOCOL_FILE = PROJECT_ROOT / "EXECUTION_PROTOCOL.md"

OUTPUT_FILE = PROCESSED_DIR / "execution_parameters.csv"


# =============================================================================
# FROZEN EXECUTION PROTOCOL
# =============================================================================

EXPECTED_EXECUTION_PROTOCOL_SHA256 = (
    "ef534c27856907e45ac871db8d4d499ddb338ffe114169f3ea2ee796f8265d6e"
)


# =============================================================================
# DEVELOPMENT SAMPLE ONLY
# =============================================================================

DEVELOPMENT_SESSIONS = [
    "20260824_135129",
    "20260825_084855",
    "20260826_085550",
    "20260826_144545",
    "20260826_151328",
]

SIGNAL_COLUMN = "median_book_imbalance"

LOWER_QUANTILE = 0.20
UPPER_QUANTILE = 0.80


# =============================================================================
# HELPERS
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


def verify_execution_protocol():
    if not EXECUTION_PROTOCOL_FILE.exists():
        raise FileNotFoundError(
            f"Missing execution protocol:\n{EXECUTION_PROTOCOL_FILE}"
        )

    actual_hash = sha256_file(
        EXECUTION_PROTOCOL_FILE
    )

    print("=" * 90)
    print("EXECUTION PROTOCOL INTEGRITY CHECK")
    print("=" * 90)

    print(
        f"Expected SHA256: {EXPECTED_EXECUTION_PROTOCOL_SHA256}"
    )

    print(
        f"Actual SHA256:   {actual_hash}"
    )

    if actual_hash != EXPECTED_EXECUTION_PROTOCOL_SHA256:
        raise RuntimeError(
            "\nEXECUTION_PROTOCOL.md has changed.\n"
            "Threshold calibration aborted."
        )

    print(
        "Protocol status:  VERIFIED — UNCHANGED"
    )

    return actual_hash


def load_development_signal():
    frames = []

    print()
    print("=" * 90)
    print("LOADING DEVELOPMENT SESSIONS ONLY")
    print("=" * 90)

    for session_id in DEVELOPMENT_SESSIONS:
        file_path = (
            PROCESSED_DIR
            / f"btcusdt_features_{session_id}.csv"
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"Missing development feature file:\n{file_path}"
            )

        df = pd.read_csv(
            file_path
        )

        if SIGNAL_COLUMN not in df.columns:
            raise KeyError(
                f"{SIGNAL_COLUMN} not found in:\n{file_path}"
            )

        signal = pd.to_numeric(
            df[SIGNAL_COLUMN],
            errors="coerce",
        ).dropna()

        print(
            f"{session_id}: "
            f"{len(signal)} valid signal observations"
        )

        frame = pd.DataFrame(
            {
                "session_id": session_id,
                SIGNAL_COLUMN: signal.to_numpy(),
            }
        )

        frames.append(
            frame
        )

    pooled = pd.concat(
        frames,
        ignore_index=True,
    )

    return pooled


# =============================================================================
# MAIN
# =============================================================================

def main():
    protocol_hash = verify_execution_protocol()

    pooled = load_development_signal()

    print()
    print("=" * 90)
    print("DEVELOPMENT-ONLY THRESHOLD CALIBRATION")
    print("=" * 90)

    print(
        f"Development sessions:     {len(DEVELOPMENT_SESSIONS)}"
    )

    print(
        f"Total valid observations: {len(pooled)}"
    )

    lower_threshold = float(
        pooled[SIGNAL_COLUMN].quantile(
            LOWER_QUANTILE
        )
    )

    upper_threshold = float(
        pooled[SIGNAL_COLUMN].quantile(
            UPPER_QUANTILE
        )
    )

    print()
    print(
        f"20th percentile threshold: {lower_threshold:+.10f}"
    )

    print(
        f"80th percentile threshold: {upper_threshold:+.10f}"
    )

    short_count = int(
        (
            pooled[SIGNAL_COLUMN]
            <= lower_threshold
        ).sum()
    )

    long_count = int(
        (
            pooled[SIGNAL_COLUMN]
            >= upper_threshold
        ).sum()
    )

    neutral_count = int(
        len(pooled)
        - short_count
        - long_count
    )

    print()
    print(
        f"Development SHORT states:  {short_count}"
    )

    print(
        f"Development LONG states:   {long_count}"
    )

    print(
        f"Development FLAT states:   {neutral_count}"
    )

    frozen_at = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    output = pd.DataFrame(
        [
            {
                "parameter": "lower_threshold",
                "value": lower_threshold,
                "description": (
                    "20th percentile of pooled development "
                    "median_book_imbalance"
                ),
                "source": "development_only",
                "frozen_at_utc": frozen_at,
                "execution_protocol_sha256": protocol_hash,
            },
            {
                "parameter": "upper_threshold",
                "value": upper_threshold,
                "description": (
                    "80th percentile of pooled development "
                    "median_book_imbalance"
                ),
                "source": "development_only",
                "frozen_at_utc": frozen_at,
                "execution_protocol_sha256": protocol_hash,
            },
            {
                "parameter": "signal_column",
                "value": SIGNAL_COLUMN,
                "description": (
                    "Frozen primary execution signal"
                ),
                "source": "execution_protocol",
                "frozen_at_utc": frozen_at,
                "execution_protocol_sha256": protocol_hash,
            },
            {
                "parameter": "holding_period_seconds",
                "value": 1.0,
                "description": (
                    "Frozen nominal holding period"
                ),
                "source": "execution_protocol",
                "frozen_at_utc": frozen_at,
                "execution_protocol_sha256": protocol_hash,
            },
            {
                "parameter": "reference_latency_ms",
                "value": 100.0,
                "description": (
                    "Frozen reference modeled additional latency"
                ),
                "source": "execution_protocol",
                "frozen_at_utc": frozen_at,
                "execution_protocol_sha256": protocol_hash,
            },
        ]
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("=" * 90)
    print("OUTPUT")
    print("=" * 90)

    print(
        f"Execution parameters saved to:\n{OUTPUT_FILE}"
    )

    print()
    print(
        "IMPORTANT: no holdout session was loaded "
        "or used during calibration."
    )


if __name__ == "__main__":
    main()