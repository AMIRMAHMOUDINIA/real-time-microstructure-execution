# Validation Status

This document summarizes the current validation state of the BTCUSDT Level-1 order-book imbalance research project.

The project demonstrates that the pre-specified signal survived statistical and execution holdout testing under the tested assumptions. It does **not** establish production profitability or real-money deployability.

| Validation stage | Status | Interpretation |
|---|---|---|
| Statistical signal validation | **PASS** | Level-1 order-book imbalance shows a statistically measurable relationship with 1-second forward returns under the pre-specified analysis. |
| Unseen statistical holdout | **PASS** | The statistical relationship remained positive across all five untouched holdout sessions. |
| Causal execution validation | **PASS** | The signal was evaluated using causal bid/ask execution rather than midpoint or look-ahead fills. |
| Unseen execution holdout | **PASS** | At the primary 100 ms latency assumption, all five holdout sessions produced positive mean gross execution returns. |
| Latency robustness | **POSITIVE, DECAYING** | Equal-weight mean return remained positive across the tested 0–1000 ms latency grid, while declining as latency increased. |
| Tail robustness | **POSITIVE, RIGHT-SKEWED** | Performance remained positive after tail diagnostics and session-level trimming, but the trade-return distribution is right-skewed and materially supported by larger positive winners. |
| Cost robustness | **LIMITED** | At 100 ms latency, equal-weight mean return remained positive at 0.05 bps additional cost per side and became negative at 0.10 bps per side. Estimated continuous break-even additional cost is approximately 0.0867 bps per side. |
| Production profitability | **NOT ESTABLISHED** | The current evidence is based on research simulation and is insufficient to claim a production-ready profitable strategy. |
| Long-horizon regime robustness | **NOT ESTABLISHED** | The current holdout covers five independent sessions and does not establish persistence across longer market regimes, months, or structural changes. |
| Real-money execution | **NOT TESTED** | No live-capital execution has been performed. Realized fees, operational latency, order acknowledgement, exchange-side effects, and actual slippage remain untested. |

## Primary Holdout Execution Result

At the pre-specified primary execution setting:

- **Latency:** 100 ms
- **Completed holdout trades:** 662
- **Positive holdout sessions:** 5 / 5
- **Equal-weight mean gross return:** +0.1733 bps/trade
- **Estimated break-even additional cost:** 0.0867 bps/side

These figures should be interpreted as validation evidence under the frozen research protocol, not as evidence of deployable production alpha.

## Main Research Limitation

The principal economic limitation is transaction-cost sensitivity.

The predictive relationship survives causal spread-aware execution and latency stress under the tested assumptions, but the remaining monetizable margin is small. Additional implementation costs above approximately 0.0867 bps per side eliminate the mean simulated edge at the primary 100 ms latency setting.

## Remaining Validation Stages

The main unresolved stages are:

1. Longitudinal validation across substantially longer time periods and multiple market regimes.
2. Live shadow execution comparing simulated fills with observed executable outcomes.
3. Real-money execution under controlled risk limits.
4. Measurement of realized fees, slippage, API/network latency, operational failures, and other production frictions.
5. Evaluation of whether any positive edge remains after these real-world costs.

## Interpretation Boundary

The appropriate conclusion from the current project is:

> The pre-specified Level-1 imbalance signal replicated statistically and remained positive under causal execution, frozen holdout testing, latency stress, and tail diagnostics, but its economic margin is thin and production profitability has not been established.
