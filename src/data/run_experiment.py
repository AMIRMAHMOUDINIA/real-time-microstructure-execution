import argparse
import csv
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path.cwd()

SCRIPT_DIR = (
    PROJECT_ROOT
    / "src"
    / "data"
)

RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
)

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

MANIFEST_FILE = (
    PROJECT_ROOT
    / "data"
    / "experiment_manifest.csv"
)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Run a complete BTCUSDT "
            "microstructure experiment."
        )
    )

    parser.add_argument(
        "--seconds",
        type=int,
        default=600,
        help=(
            "Live collection duration "
            "in seconds."
        ),
    )

    parser.add_argument(
        "--label",
        type=str,
        default="unlabelled",
        help=(
            "Human-readable session label, "
            "for example morning or evening."
        ),
    )

    return parser.parse_args()


def run_script(
    script_name,
    extra_arguments=None,
):
    script_path = (
        SCRIPT_DIR
        / script_name
    )

    command = [
        sys.executable,
        str(script_path),
    ]

    if extra_arguments:
        command.extend(
            extra_arguments
        )

    print()
    print("=" * 80)
    print(
        f"RUNNING: {script_name}"
    )
    print("=" * 80)
    print()

    subprocess.run(
        command,
        check=True,
        cwd=PROJECT_ROOT,
    )


def find_latest_complete_session():
    book_files = list(
        RAW_DIR.glob(
            "btcusdt_book_*.csv"
        )
    )

    trade_files = list(
        RAW_DIR.glob(
            "btcusdt_trades_*.csv"
        )
    )

    book_sessions = {
        file.stem.replace(
            "btcusdt_book_",
            "",
        ): file
        for file in book_files
    }

    trade_sessions = {
        file.stem.replace(
            "btcusdt_trades_",
            "",
        ): file
        for file in trade_files
    }

    common_sessions = (
        set(book_sessions)
        & set(trade_sessions)
    )

    if not common_sessions:
        raise FileNotFoundError(
            "No complete book/trade "
            "session pair was found."
        )

    session_id = max(
        common_sessions
    )

    return (
        session_id,
        book_sessions[session_id],
        trade_sessions[session_id],
    )


def find_feature_file(
    session_id,
):
    feature_file = (
        PROCESSED_DIR
        / (
            f"btcusdt_features_"
            f"{session_id}.csv"
        )
    )

    if feature_file.exists():
        return feature_file

    return None


def append_manifest(
    session_id,
    label,
    requested_seconds,
    book_file,
    trade_file,
    feature_file,
):
    MANIFEST_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_exists = (
        MANIFEST_FILE.exists()
    )

    completed_at = datetime.now(
        timezone.utc
    ).isoformat()

    with MANIFEST_FILE.open(
        mode="a",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.writer(
            csv_file
        )

        if not file_exists:
            writer.writerow([
                "completed_at_utc",
                "session_id",
                "label",
                "requested_seconds",
                "book_file",
                "trade_file",
                "feature_file",
            ])

        writer.writerow([
            completed_at,
            session_id,
            label,
            requested_seconds,
            str(book_file),
            str(trade_file),
            (
                str(feature_file)
                if feature_file
                else ""
            ),
        ])


def main():
    args = parse_arguments()

    if args.seconds <= 0:
        raise ValueError(
            "Duration must be positive."
        )

    print()
    print("#" * 80)
    print(
        "BTCUSDT MICROSTRUCTURE "
        "EXPERIMENT"
    )
    print("#" * 80)

    print(
        f"Label:             "
        f"{args.label}"
    )

    print(
        f"Requested duration:"
        f" {args.seconds} seconds"
    )

    print()

    run_script(
        "collect_live_session.py",
        [
            "--seconds",
            str(args.seconds),
        ],
    )

    (
        session_id,
        book_file,
        trade_file,
    ) = find_latest_complete_session()

    print()
    print(
        f"Detected session ID: "
        f"{session_id}"
    )

    run_script(
        "analyze_live_session.py"
    )

    run_script(
        "build_session_features.py"
    )

    run_script(
        "analyze_signal_buckets.py"
    )

    feature_file = (
        find_feature_file(
            session_id
        )
    )

    append_manifest(
        session_id=session_id,
        label=args.label,
        requested_seconds=args.seconds,
        book_file=book_file,
        trade_file=trade_file,
        feature_file=feature_file,
    )

    print()
    print("#" * 80)
    print(
        "EXPERIMENT COMPLETE"
    )
    print("#" * 80)

    print(
        f"Session ID:     "
        f"{session_id}"
    )

    print(
        f"Label:          "
        f"{args.label}"
    )

    print(
        f"Book file:      "
        f"{book_file}"
    )

    print(
        f"Trade file:     "
        f"{trade_file}"
    )

    print(
        f"Feature file:   "
        f"{feature_file}"
    )

    print(
        f"Manifest:       "
        f"{MANIFEST_FILE}"
    )


if __name__ == "__main__":
    main()