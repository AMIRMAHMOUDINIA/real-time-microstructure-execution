import asyncio
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from websockets.asyncio.client import connect


URI = "wss://data-stream.binance.vision/ws/btcusdt@bookTicker"

MAX_MESSAGES = 500

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = OUTPUT_DIR / f"btcusdt_bookticker_{run_timestamp}.csv"


async def listen_to_book_ticker():
    print("Connecting to BTCUSDT book ticker...")
    print(f"Saving data to: {OUTPUT_FILE}")
    print()

    with OUTPUT_FILE.open(
        mode="w",
        newline="",
        encoding="utf-8"
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

        async with connect(URI) as websocket:
            print("Connected.\n")

            message_count = 0

            async for message in websocket:
                received_at = datetime.now(timezone.utc)

                data = json.loads(message)

                update_id = int(data["u"])
                symbol = data["s"]

                bid_price = float(data["b"])
                bid_quantity = float(data["B"])

                ask_price = float(data["a"])
                ask_quantity = float(data["A"])

                mid_price = (bid_price + ask_price) / 2
                spread = ask_price - bid_price

                total_quantity = bid_quantity + ask_quantity

                if total_quantity > 0:
                    imbalance = (
                        bid_quantity - ask_quantity
                    ) / total_quantity
                else:
                    imbalance = 0.0

                writer.writerow([
                    received_at.isoformat(),
                    update_id,
                    symbol,
                    bid_price,
                    bid_quantity,
                    ask_price,
                    ask_quantity,
                    mid_price,
                    spread,
                    imbalance,
                ])

                message_count += 1

                if message_count <= 10 or message_count % 100 == 0:
                    print(
                        f"{message_count:>4} | "
                        f"Bid {bid_price:.2f} | "
                        f"Ask {ask_price:.2f} | "
                        f"Spread {spread:.4f} | "
                        f"Imbalance {imbalance:+.4f}"
                    )

                if message_count >= MAX_MESSAGES:
                    break

    print()
    print(f"Finished collecting {message_count} updates.")
    print(f"Dataset saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(listen_to_book_ticker())