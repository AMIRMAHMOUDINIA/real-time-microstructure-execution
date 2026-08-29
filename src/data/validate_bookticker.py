from pathlib import Path

import pandas as pd


RAW_DIR = Path("data/raw")


def find_latest_dataset():
    files = list(RAW_DIR.glob("btcusdt_bookticker_*.csv"))

    if not files:
        raise FileNotFoundError(
            "No BTCUSDT book ticker CSV files were found in data/raw."
        )

    return max(files, key=lambda file: file.stat().st_mtime)


def validate_dataset(file_path):
    print(f"Reading dataset: {file_path}")
    print()

    df = pd.read_csv(
        file_path,
        parse_dates=["received_at_utc"]
    )

    print("=" * 70)
    print("BASIC INFORMATION")
    print("=" * 70)

    print(f"Rows:                 {len(df)}")
    print(f"Columns:              {len(df.columns)}")
    print(f"Missing values:       {df.isna().sum().sum()}")
    print(f"Duplicate rows:       {df.duplicated().sum()}")
    print(
        f"Duplicate update IDs: "
        f"{df['update_id'].duplicated().sum()}"
    )

    print()
    print("=" * 70)
    print("TIMESTAMP AND SEQUENCE CHECKS")
    print("=" * 70)

    time_differences = (
        df["received_at_utc"]
        .diff()
        .dt.total_seconds()
    )

    backwards = (time_differences < 0).sum()

    non_increasing_update_ids = (
        df["update_id"]
        .diff()
        .dropna()
        <= 0
    ).sum()

    print(f"Backwards timestamps:        {backwards}")
    print(
        f"Non-increasing update IDs:   "
        f"{non_increasing_update_ids}"
    )

    if len(df) > 1:
        valid_time_differences = time_differences.dropna()

        print(
            f"Median time between updates: "
            f"{valid_time_differences.median() * 1000:.3f} ms"
        )

        print(
            f"90th percentile gap:         "
            f"{valid_time_differences.quantile(0.90) * 1000:.3f} ms"
        )

        print(
            f"99th percentile gap:         "
            f"{valid_time_differences.quantile(0.99) * 1000:.3f} ms"
        )

        print(
            f"Maximum gap:                 "
            f"{valid_time_differences.max() * 1000:.3f} ms"
        )

        total_duration = (
            df["received_at_utc"].iloc[-1]
            - df["received_at_utc"].iloc[0]
        ).total_seconds()

        print(
            f"Collection duration:         "
            f"{total_duration:.3f} seconds"
        )

        if total_duration > 0:
            messages_per_second = (
                len(df) / total_duration
            )

            print(
                f"Average updates per second:  "
                f"{messages_per_second:.2f}"
            )

    print()
    print("=" * 70)
    print("ORDER-BOOK CHECKS")
    print("=" * 70)

    crossed_quotes = (
        df["ask_price"] < df["bid_price"]
    ).sum()

    locked_quotes = (
        df["ask_price"] == df["bid_price"]
    ).sum()

    negative_quantities = (
        (df["bid_quantity"] < 0)
        | (df["ask_quantity"] < 0)
    ).sum()

    invalid_imbalance = (
        (df["imbalance"] < -1)
        | (df["imbalance"] > 1)
    ).sum()

    non_positive_spreads = (
        df["spread"] <= 0
    ).sum()

    print(f"Crossed quotes:              {crossed_quotes}")
    print(f"Locked quotes:               {locked_quotes}")
    print(f"Negative quantities:         {negative_quantities}")
    print(f"Invalid imbalance:           {invalid_imbalance}")
    print(f"Non-positive spreads:        {non_positive_spreads}")

    print()
    print("=" * 70)
    print("SPREAD STATISTICS")
    print("=" * 70)

    spread_stats = df["spread"].describe(
        percentiles=[
            0.50,
            0.90,
            0.95,
            0.99
        ]
    )

    print(spread_stats)

    print()
    print("=" * 70)
    print("IMBALANCE STATISTICS")
    print("=" * 70)

    imbalance_stats = df["imbalance"].describe(
        percentiles=[
            0.10,
            0.25,
            0.50,
            0.75,
            0.90
        ]
    )

    print(imbalance_stats)

    print()
    print("=" * 70)
    print("10 WIDEST OBSERVED SPREADS")
    print("=" * 70)

    widest = df.nlargest(
        10,
        "spread"
    )[
        [
            "received_at_utc",
            "update_id",
            "bid_price",
            "ask_price",
            "bid_quantity",
            "ask_quantity",
            "spread",
            "imbalance",
        ]
    ]

    print(
        widest.to_string(
            index=False
        )
    )

    print()
    print("=" * 70)
    print("10 MOST NEGATIVE IMBALANCE OBSERVATIONS")
    print("=" * 70)

    most_negative = df.nsmallest(
        10,
        "imbalance"
    )[
        [
            "received_at_utc",
            "bid_price",
            "ask_price",
            "bid_quantity",
            "ask_quantity",
            "spread",
            "imbalance",
        ]
    ]

    print(
        most_negative.to_string(
            index=False
        )
    )

    print()
    print("=" * 70)
    print("10 MOST POSITIVE IMBALANCE OBSERVATIONS")
    print("=" * 70)

    most_positive = df.nlargest(
        10,
        "imbalance"
    )[
        [
            "received_at_utc",
            "bid_price",
            "ask_price",
            "bid_quantity",
            "ask_quantity",
            "spread",
            "imbalance",
        ]
    ]

    print(
        most_positive.to_string(
            index=False
        )
    )

    print()
    print("=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    latest_file = find_latest_dataset()
    validate_dataset(latest_file)