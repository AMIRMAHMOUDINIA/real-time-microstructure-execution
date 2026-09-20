# Data Availability

This repository is designed to make the research process, validation logic, execution assumptions, and reported results inspectable while keeping the full historical market-data archive and large generated trade-level files out of version control.

It includes one complete raw holdout session as a compact end-to-end reproducibility example. It should therefore be interpreted as a **reproducibility-focused research record with one complete public raw-data reproduction path**, not as a complete archival release of every historical input used in the study.

## Publicly Available

The repository includes:

- source code for live data collection, feature construction, statistical validation, execution simulation, and diagnostics
- frozen statistical and execution protocols
- frozen execution parameters
- the public experiment manifest
- compact statistical validation summaries
- compact execution-development and holdout summaries
- latency-sensitivity results
- transaction-cost sensitivity results
- tail-risk and directional diagnostics
- stability/bootstrap summaries
- publication-quality figures
- SHA256 integrity checkpoints for important protocols, scripts, parameters, and outputs
- one complete approximately 10-minute raw holdout session for end-to-end reproduction

The public raw reproduction sample is:

`examples/holdout_20260829_091754/`

It contains deterministic gzip-compressed copies of the original BTCUSDT Level-1 book-ticker and trade captures for holdout session `20260829_091754`, together with a reproduction script and documentation.

Using those files, the repository rebuilds the one-second feature dataset and reruns the existing causal execution simulator under the frozen 100 ms reference-latency configuration.

The reproduced result is:

- 599 one-second feature observations
- 157 qualifying signals
- 78 completed trades
- 41 long trades
- 37 short trades
- mean simulated gross return: `+0.0458951523 bps/trade`
- break-even additional cost: `0.0229475761 bps/side`

The reproduction script also verifies the repository's mechanical causality checks and fails if the expected reference result is not recovered.

The public experiment manifest records the historical session identifiers, collection timestamps, labels, requested durations, and expected relative paths of the corresponding raw, trade, and feature files.

## Intentionally Excluded

With the exception of the single public reproduction session described above, the following historical files are not included in the public repository:

- raw Binance WebSocket book-ticker captures
- raw trade captures
- per-session feature datasets
- large generated trade-level execution files
- the local experiment manifest containing local research state

These files are excluded primarily because they are generated research data and would substantially increase repository size.

Their absence means that the **entire historical experiment** cannot be reconstructed from a fresh clone alone.

## What Can Be Reproduced From a Fresh Clone

Using only the public repository, a reviewer can:

- inspect the complete research methodology
- inspect the frozen validation and execution protocols
- inspect the exact execution parameters
- inspect the reported session-level and aggregate validation results
- inspect the development-versus-holdout comparisons
- reproduce the published latency-sensitivity figure from the retained summary CSV
- reproduce the published transaction-cost frontier figure from the retained summary CSV
- inspect the tail-risk and stability diagnostics
- verify the integrity of retained public artifacts using the published SHA256 checkpoints
- rebuild one complete holdout session from raw book and trade captures
- regenerate its one-second feature dataset
- rerun the causal execution simulation using the frozen execution parameters
- verify the reproduced trade counts, direction counts, mean gross return, break-even cost, and mechanical causality checks

For the public sample, run from the repository root:

    python -m pip install -e .
    python examples/holdout_20260829_091754/reproduce_sample.py

## What Cannot Be Reproduced From a Fresh Clone

Because the remaining historical raw market-data files are excluded, a reviewer cannot independently:

- reconstruct every original raw WebSocket session
- rebuild every historical per-second feature dataset
- rerun the full multi-session statistical-validation pipeline from all original raw captures
- regenerate the complete historical trade-level execution output
- independently reproduce the entire development-and-holdout experiment from raw market data

The data-collection scripts can be used to collect **new** live market data, but new observations will not reproduce the historical sessions used in the frozen validation study.

## Integrity Checkpoints

SHA256 fingerprints are used to document important frozen research artifacts and establish whether retained files have changed after a research stage was locked.

These hashes provide **integrity and audit checkpoints**. They do not substitute for historical raw data that is not included in the repository and should not be interpreted as proof that the complete multi-session experiment is fully reproducible from a fresh clone.

The included public holdout sample provides a separate and stronger check: one actual historical raw session can be taken through feature construction and causal execution to reproduce its frozen reference result.

## Interpretation

The repository supports inspection of the research design, validation discipline, execution assumptions, robustness analyses, and reported outputs.

It now also supports **end-to-end raw-data reproduction for one complete unseen holdout session**.

The strongest appropriate description is therefore that the project provides a **transparent, audit-oriented research record with one complete public holdout reproduction path and partial reproducibility of the broader multi-session study**.

This does not establish production profitability, long-horizon regime robustness, or real-money execution performance.
