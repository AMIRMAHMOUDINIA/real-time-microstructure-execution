from __future__ import annotations

import argparse
import asyncio
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

try:
    from src.data.stream_integrity import (
        StreamHealth,
        exponential_backoff,
    )
except ModuleNotFoundError:
    from stream_integrity import (
        StreamHealth,
        exponential_backoff,
    )


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

POLL_SECONDS = 1.0
DEFAULT_STALE_SECONDS = 5.0
BACKOFF_BASE_SECONDS = 0.5
BACKOFF_MAX_SECONDS = 8.0


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Collect resilient BTCUSDT live market data."
    )
    parser.add_argument(
        "--seconds",
        type=int,
        default=600,
    )
    parser.add_argument(
        "--stale-seconds",
        type=float,
        default=DEFAULT_STALE_SECONDS,
    )
    return parser.parse_args()


async def _wait_or_stop(stop_event, seconds):
    if seconds <= 0:
        return
    try:
        await asyncio.wait_for(
            stop_event.wait(),
            timeout=seconds,
        )
    except TimeoutError:
        pass


async def _run_stream(
    *,
    name,
    uri,
    stop_event,
    health,
    on_message,
    stale_seconds,
    poll_seconds=POLL_SECONDS,
    connect_factory=None,
    backoff_base=BACKOFF_BASE_SECONDS,
    backoff_max=BACKOFF_MAX_SECONDS,
):
    connector = connect if connect_factory is None else connect_factory
    attempt = 0

    while not stop_event.is_set():
        try:
            async with connector(uri) as websocket:
                health.record_connection()
                attempt = 0
                last_activity = time.monotonic()

                print(
                    f"{name} connected "
                    f"(connection {health.connections})."
                )

                while not stop_event.is_set():
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=poll_seconds,
                        )
                    except TimeoutError:
                        health.record_timeout()

                        if (
                            time.monotonic() - last_activity
                            >= stale_seconds
                        ):
                            health.stale_reconnects += 1
                            print(
                                f"{name} stale; reconnecting."
                            )
                            break

                        continue

                    received_at = datetime.now(timezone.utc)
                    last_activity = time.monotonic()
                    health.record_raw(received_at)

                    on_message(message, received_at)

                if stop_event.is_set():
                    break

        except (
            OSError,
            TimeoutError,
            WebSocketException,
        ) as exc:
            health.connection_errors += 1
            print(
                f"{name} error: "
                f"{type(exc).__name__}: {exc}"
            )

        if stop_event.is_set():
            break

        health.retry_attempts += 1

        delay = exponential_backoff(
            attempt,
            base_seconds=backoff_base,
            max_seconds=backoff_max,
        )
        attempt += 1

        print(
            f"{name} retry in {delay:.2f}s."
        )

        await _wait_or_stop(
            stop_event,
            delay,
        )

    return health


def _process_book(message, writer, health, received_at):
    try:
        data = json.loads(message)
        update_id = int(data["u"])
        bid_price = float(data["b"])
        bid_quantity = float(data["B"])
        ask_price = float(data["a"])
        ask_quantity = float(data["A"])
        symbol = str(data["s"])
    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        health.malformed_messages += 1
        return False

    if health.observe_sequence(update_id) != "accepted":
        return False

    mid_price = (bid_price + ask_price) / 2
    spread = ask_price - bid_price

    total_quantity = bid_quantity + ask_quantity

    imbalance = (
        (bid_quantity - ask_quantity) / total_quantity
        if total_quantity > 0
        else 0.0
    )

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
    return True


def _process_trade(message, writer, health, received_at):
    try:
        data = json.loads(message)
        trade_id = int(data["t"])
        price = float(data["p"])
        quantity = float(data["q"])
        buyer_is_maker = bool(data["m"])
        symbol = str(data["s"])

        event_time = datetime.fromtimestamp(
            data["E"] / 1000,
            tz=timezone.utc,
        )
        trade_time = datetime.fromtimestamp(
            data["T"] / 1000,
            tz=timezone.utc,
        )
    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
    ):
        health.malformed_messages += 1
        return False

    if health.observe_sequence(trade_id) != "accepted":
        return False

    aggressor_side = (
        "SELL"
        if buyer_is_maker
        else "BUY"
    )

    writer.writerow([
        received_at.isoformat(),
        event_time.isoformat(),
        trade_time.isoformat(),
        trade_id,
        symbol,
        price,
        quantity,
        price * quantity,
        buyer_is_maker,
        aggressor_side,
    ])
    return True


async def collect_book(stop_event, path, stale_seconds):
    health = StreamHealth("book")

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

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

        def handler(message, received_at):
            _process_book(
                message,
                writer,
                health,
                received_at,
            )

        await _run_stream(
            name="Book",
            uri=BOOK_URI,
            stop_event=stop_event,
            health=health,
            on_message=handler,
            stale_seconds=stale_seconds,
        )

        file.flush()

    return health


async def collect_trades(stop_event, path, stale_seconds):
    health = StreamHealth("trades")

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

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

        def handler(message, received_at):
            _process_trade(
                message,
                writer,
                health,
                received_at,
            )

        await _run_stream(
            name="Trade",
            uri=TRADE_URI,
            stop_event=stop_event,
            health=health,
            on_message=handler,
            stale_seconds=stale_seconds,
        )

        file.flush()

    return health


async def stop_after_delay(stop_event, seconds):
    await asyncio.sleep(seconds)
    stop_event.set()


async def main():
    args = parse_arguments()

    if args.seconds <= 0:
        raise ValueError(
            "Session duration must be positive."
        )

    if args.stale_seconds <= 0:
        raise ValueError(
            "Stale threshold must be positive."
        )

    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%d_%H%M%S")

    book_file = OUTPUT_DIR / f"btcusdt_book_{run_id}.csv"
    trade_file = OUTPUT_DIR / f"btcusdt_trades_{run_id}.csv"
    health_file = OUTPUT_DIR / f"btcusdt_health_{run_id}.json"

    print(
        f"Starting {args.seconds}-second BTCUSDT session."
    )
    print(f"Session ID: {run_id}")

    stop_event = asyncio.Event()

    book_task = asyncio.create_task(
        collect_book(
            stop_event,
            book_file,
            args.stale_seconds,
        )
    )

    trade_task = asyncio.create_task(
        collect_trades(
            stop_event,
            trade_file,
            args.stale_seconds,
        )
    )

    timer_task = asyncio.create_task(
        stop_after_delay(
            stop_event,
            args.seconds,
        )
    )

    book_health, trade_health, _ = await asyncio.gather(
        book_task,
        trade_task,
        timer_task,
    )

    finished = datetime.now(timezone.utc)

    report = {
        "session_id": run_id,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "requested_duration_seconds": args.seconds,
        "stale_seconds": args.stale_seconds,
        "book": book_health.to_dict(),
        "trades": trade_health.to_dict(),
    }

    health_file.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print()
    print("SESSION COMPLETE")
    print(
        f"Book accepted:  "
        f"{book_health.accepted_messages}"
    )
    print(
        f"Book reconnects:"
        f" {book_health.reconnects}"
    )
    print(
        f"Trade accepted: "
        f"{trade_health.accepted_messages}"
    )
    print(
        f"Trade reconnects:"
        f" {trade_health.reconnects}"
    )
    print(f"Health file: {health_file}")


if __name__ == "__main__":
    asyncio.run(main())
