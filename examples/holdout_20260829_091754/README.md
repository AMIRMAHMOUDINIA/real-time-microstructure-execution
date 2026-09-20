# Public Holdout Reproduction Sample

This directory contains one complete BTCUSDT holdout session from the
frozen validation experiment.

## Session

- Session ID: `20260829_091754`
- Holdout label: `holdout_5`
- Approximate duration: 10 minutes
- Raw source: Binance BTCUSDT Level-1 book ticker and trade streams
- Data format: deterministic gzip-compressed CSV copies of the original captures

This session was one of five unseen holdout sessions used in the execution
evaluation. It is included as a compact public example so that the
raw-data-to-feature-to-execution path can be reproduced.

## Frozen execution settings

The script uses the tracked parameters in:

`data/processed/execution_parameters.csv`

Primary settings:

- signal: `median_book_imbalance`
- lower threshold: `-0.8112458586175827`
- upper threshold: `0.8195917760023075`
- modeled additional latency: `100 ms`
- nominal holding period: `1 second`
- LONG execution: entry ask to exit bid
- SHORT execution: entry bid to exit ask

## Expected result

At the frozen 100 ms reference latency:

- qualifying signals: 157
- completed trades: 78
- completed long trades: 41
- completed short trades: 37
- mean simulated gross return: `+0.0458951523 bps/trade`
- break-even additional cost: `0.0229475761 bps/side`

The reproduction script asserts these values and runs the repository's
mechanical causality checks.

## Run

From the repository root:

    python -m pip install -e .
    python examples/holdout_20260829_091754/reproduce_sample.py

## Interpretation

This reproduces one approximately 10-minute unseen holdout session.

It demonstrates that the published feature construction and causal execution
path can be regenerated from a complete raw public sample.

It does not establish production profitability, long-horizon regime
robustness, or real-money execution performance.
