# Data Availability

This repository is designed to make the research process, validation logic, and reported results inspectable while keeping large market-data captures and generated trade-level files out of version control.

It should therefore be interpreted as a **reproducibility-focused research record**, not as a complete archival release of every historical input required to regenerate the entire experiment from scratch.

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

The public experiment manifest records the historical session identifiers, collection timestamps, labels, requested durations, and the expected relative paths of the corresponding raw, trade, and feature files.

## Intentionally Excluded

The following files are not included in the public repository:

- raw Binance WebSocket book-ticker captures
- raw trade captures
- per-session feature datasets
- large generated trade-level execution files
- the local experiment manifest containing local research state

These files are excluded primarily because they are generated research data and can substantially increase repository size.

Their absence means that the full historical pipeline cannot be reconstructed from a fresh clone alone.

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

## What Cannot Be Reproduced From a Fresh Clone

Without the excluded historical market-data files, a reviewer cannot independently:

- reconstruct the original raw WebSocket sessions
- rebuild every historical per-second feature dataset
- rerun the full statistical-validation pipeline from the original raw captures
- regenerate the complete historical trade-level execution output
- independently reproduce the entire historical experiment from raw market data

The data-collection scripts can be used to collect **new** live market data, but new observations will not reproduce the historical sessions used in the frozen validation study.

## Integrity Checkpoints

SHA256 fingerprints are used to document important frozen research artifacts and establish whether retained files have changed after a research stage was locked.

These hashes provide **integrity and audit checkpoints**. They do not substitute for raw data that is not included in the repository and should not be interpreted as proof of full end-to-end reproducibility.

## Interpretation

The repository supports inspection of the research design, validation discipline, execution assumptions, robustness analyses, and reported outputs.

The strongest appropriate claim is therefore that the project provides a **transparent and audit-oriented research record with partial reproducibility of retained analyses**, rather than a fully self-contained reproduction package.
