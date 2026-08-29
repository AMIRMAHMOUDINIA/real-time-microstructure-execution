from pathlib import Path

import pandas as pd


PROCESSED_DIR = Path("data/processed")


def find_latest_feature_file():
    files = list(
        PROCESSED_DIR.glob("btcusdt_features_*.csv")
    )

    if not files:
        raise FileNotFoundError(
            "No processed BTCUSDT feature files found."
        )

    return max(
        files,
        key=lambda file: file.stat().st_mtime,
    )


def load_features(file_path):
    df = pd.read_csv(
        file_path,
        parse_dates=["received_at_utc"],
    )

    return df


def create_quantile_buckets(
    df,
    signal_column,
    number_of_buckets=5,
):
    data = df.copy()

    data = data.dropna(
        subset=[signal_column]
    )

    data["bucket"] = pd.qcut(
        data[signal_column],
        q=number_of_buckets,
        labels=False,
        duplicates="drop",
    )

    data["bucket"] = (
        data["bucket"] + 1
    )

    return data


def summarize_buckets(
    df,
    signal_column,
    return_column,
    title,
):
    valid = df.dropna(
        subset=[
            signal_column,
            return_column,
        ]
    ).copy()

    valid = create_quantile_buckets(
        valid,
        signal_column,
    )

    valid["positive_return"] = (
        valid[return_column] > 0
    )

    summary = valid.groupby(
        "bucket"
    ).agg(
        observations=(
            signal_column,
            "count",
        ),
        mean_signal=(
            signal_column,
            "mean",
        ),
        median_signal=(
            signal_column,
            "median",
        ),
        mean_future_return_bps=(
            return_column,
            "mean",
        ),
        median_future_return_bps=(
            return_column,
            "median",
        ),
        return_std_bps=(
            return_column,
            "std",
        ),
        positive_return_rate=(
            "positive_return",
            "mean",
        ),
    )

    print()
    print("=" * 92)
    print(title)
    print("=" * 92)

    print(
        summary.to_string(
            float_format=lambda x: f"{x:.4f}"
        )
    )

    if len(summary) >= 2:
        lowest = summary.iloc[0]
        highest = summary.iloc[-1]

        difference = (
            highest["mean_future_return_bps"]
            - lowest["mean_future_return_bps"]
        )

        print()
        print(
            "Top-minus-bottom mean-return "
            f"difference: {difference:+.4f} bps"
        )

    return summary


def activity_filtered_analysis(
    df,
    minimum_trades,
):
    filtered = df[
        df["trades"] >= minimum_trades
    ].copy()

    print()
    print("#" * 92)
    print(
        f"ACTIVITY FILTER: AT LEAST "
        f"{minimum_trades} TRADES PER SECOND"
    )
    print("#" * 92)

    print(
        f"Remaining observations: "
        f"{len(filtered)} / {len(df)}"
    )

    if len(filtered) < 25:
        print(
            "Too few observations for useful "
            "bucket analysis."
        )

        return

    summarize_buckets(
        filtered,
        "median_book_imbalance",
        "future_return_1s_bps",
        (
            f"BOOK IMBALANCE QUINTILES "
            f"→ +1 SECOND RETURN "
            f"(TRADES >= {minimum_trades})"
        ),
    )

    summarize_buckets(
        filtered,
        "trade_flow_imbalance",
        "future_return_1s_bps",
        (
            f"TRADE-FLOW QUINTILES "
            f"→ +1 SECOND RETURN "
            f"(TRADES >= {minimum_trades})"
        ),
    )


def print_basic_information(df):
    print("=" * 92)
    print("SIGNAL BUCKET ANALYSIS")
    print("=" * 92)

    print(
        f"Observations:             "
        f"{len(df)}"
    )

    print(
        f"Seconds with zero trades: "
        f"{(df['trades'] == 0).sum()}"
    )

    print(
        f"Seconds with >= 5 trades: "
        f"{(df['trades'] >= 5).sum()}"
    )

    print(
        f"Seconds with >= 10 trades:"
        f" {(df['trades'] >= 10).sum()}"
    )

    print(
        f"Seconds with >= 25 trades:"
        f" {(df['trades'] >= 25).sum()}"
    )


def main():
    feature_file = (
        find_latest_feature_file()
    )

    print(
        f"Reading feature dataset: "
        f"{feature_file}"
    )

    df = load_features(
        feature_file
    )

    print_basic_information(
        df
    )

    summarize_buckets(
        df,
        "median_book_imbalance",
        "future_return_1s_bps",
        (
            "BOOK IMBALANCE QUINTILES "
            "→ +1 SECOND RETURN"
        ),
    )

    summarize_buckets(
        df,
        "median_book_imbalance",
        "future_return_5s_bps",
        (
            "BOOK IMBALANCE QUINTILES "
            "→ +5 SECOND RETURN"
        ),
    )

    trades_only = df[
        df["trades"] > 0
    ].copy()

    summarize_buckets(
        trades_only,
        "trade_flow_imbalance",
        "future_return_1s_bps",
        (
            "TRADE-FLOW IMBALANCE QUINTILES "
            "→ +1 SECOND RETURN"
        ),
    )

    summarize_buckets(
        trades_only,
        "trade_flow_imbalance",
        "future_return_5s_bps",
        (
            "TRADE-FLOW IMBALANCE QUINTILES "
            "→ +5 SECOND RETURN"
        ),
    )

    activity_filtered_analysis(
        df,
        minimum_trades=5,
    )

    activity_filtered_analysis(
        df,
        minimum_trades=10,
    )

    activity_filtered_analysis(
        df,
        minimum_trades=25,
    )

    print()
    print("=" * 92)
    print("IMPORTANT")
    print("=" * 92)

    print(
        "These results come from one "
        "market session."
    )

    print(
        "They are exploratory diagnostics, "
        "not evidence of executable alpha."
    )

    print(
        "The next robustness step is to "
        "repeat the analysis across multiple "
        "independent sessions."
    )


if __name__ == "__main__":
    main()