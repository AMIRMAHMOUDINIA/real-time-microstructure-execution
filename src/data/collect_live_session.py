import argparse
import asyncio
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from websockets.asyncio.client import connect


BOOK_URI = (
    "wss://data-stream.binance.vision/ws/"
    "btcusdt@bookTicker"
)

TRADE_URI = (
    "wss://data-stream.binance.vision/ws/"
    "btcusdt@trade"
)

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Collect BTCUSDT live book and trade data."
        )
    )

    parser.add_argument(
        "--seconds",
        type=int,
        default=600,
        help="Collection duration in seconds.",
    )

    return parser.parse_args()


async def collect_book(
    stop_event,
    book_file,
):
    book_count = 0

    with book_file.open(
        mode="w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.writer(csv_file)

        writer.writerow([
            "received_at_utc",
            "update_id",
            "symbol",
            "bid_price",
            "bid_quantity",
            "ask_price",
            "ask_quantity",
            "mid_price",
            "spread",
            "imbalance",
        ])

        async with connect(BOOK_URI) as websocket:
            print("Book stream connected.")

            while not stop_event.is_set():
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=1.0,
                    )

                except asyncio.TimeoutError:
                    continue

                received_at = datetime.now(
                    timezone.utc
                )

                data = json.loads(message)

                bid_price = float(data["b"])
                bid_quantity = float(data["B"])

                ask_price = float(data["a"])
                ask_quantity = float(data["A"])

                mid_price = (
                    bid_price + ask_price
                ) / 2

                spread = (
                    ask_price - bid_price
                )

                total_quantity = (
                    bid_quantity
                    + ask_quantity
                )

                if total_quantity > 0:
                    imbalance = (
                        bid_quantity
                        - ask_quantity
                    ) / total_quantity

                else:
                    imbalance = 0.0

                writer.writerow([
                    received_at.isoformat(),
                    int(data["u"]),
                    data["s"],
                    bid_price,
                    bid_quantity,
                    ask_price,
                    ask_quantity,
                    mid_price,
                    spread,
                    imbalance,
                ])

                book_count += 1

    return book_count


async def collect_trades(
    stop_event,
    trade_file,
):
    trade_count = 0

    with trade_file.open(
        mode="w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.writer(csv_file)

        writer.writerow([
            "received_at_utc",
            "event_time_utc",
            "trade_time_utc",
            "trade_id",
            "symbol",
            "price",
            "quantity",
            "quote_value",
            "buyer_is_maker",
            "aggressor_side",
        ])

        async with connect(TRADE_URI) as websocket:
            print("Trade stream connected.")

            while not stop_event.is_set():
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=1.0,
                    )

                except asyncio.TimeoutError:
                    continue

                received_at = datetime.now(
                    timezone.utc
                )

                data = json.loads(message)

                price = float(data["p"])
                quantity = float(data["q"])

                buyer_is_maker = bool(
                    data["m"]
                )

                if buyer_is_maker:
                    aggressor_side = "SELL"
                else:
                    aggressor_side = "BUY"

                event_time = datetime.fromtimestamp(
                    data["E"] / 1000,
                    tz=timezone.utc,
                )

                trade_time = datetime.fromtimestamp(
                    data["T"] / 1000,
                    tz=timezone.utc,
                )

                writer.writerow([
                    received_at.isoformat(),
                    event_time.isoformat(),
                    trade_time.isoformat(),
                    int(data["t"]),
                    data["s"],
                    price,
                    quantity,
                    price * quantity,
                    buyer_is_maker,
                    aggressor_side,
                ])

                trade_count += 1

    return trade_count


async def stop_after_delay(
    stop_event,
    session_seconds,
):
    await asyncio.sleep(
        session_seconds
    )

    stop_event.set()


async def main():
    args = parse_arguments()

    session_seconds = args.seconds

    if session_seconds <= 0:
        raise ValueError(
            "Session duration must be positive."
        )

    run_id = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%d_%H%M%S"
    )

    book_file = (
        OUTPUT_DIR
        / f"btcusdt_book_{run_id}.csv"
    )

    trade_file = (
        OUTPUT_DIR
        / f"btcusdt_trades_{run_id}.csv"
    )

    print(
        f"Starting {session_seconds}-second "
        f"BTCUSDT live session..."
    )

    print(
        f"Session ID:   {run_id}"
    )

    print(
        f"Book output:  {book_file}"
    )

    print(
        f"Trade output: {trade_file}"
    )

    print()

    stop_event = asyncio.Event()

    book_task = asyncio.create_task(
        collect_book(
            stop_event,
            book_file,
        )
    )

    trade_task = asyncio.create_task(
        collect_trades(
            stop_event,
            trade_file,
        )
    )

    timer_task = asyncio.create_task(
        stop_after_delay(
            stop_event,
            session_seconds,
        )
    )

    (
        book_count,
        trade_count,
        _,
    ) = await asyncio.gather(
        book_task,
        trade_task,
        timer_task,
    )

    print()
    print("=" * 60)
    print("SESSION COMPLETE")
    print("=" * 60)

    print(
        f"Session ID:        {run_id}"
    )

    print(
        f"Duration:          "
        f"{session_seconds} seconds"
    )

    print(
        f"Book updates:      "
        f"{book_count}"
    )

    print(
        f"Trades:            "
        f"{trade_count}"
    )

    print(
        f"Book file:         "
        f"{book_file}"
    )

    print(
        f"Trade file:        "
        f"{trade_file}"
    )


if __name__ == "__main__":
    asyncio.run(main())