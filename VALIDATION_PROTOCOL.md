# BTCUSDT Real-Time Microstructure Project
## Frozen Holdout Validation Protocol

**Protocol frozen:** 2026-08-26  
**Project:** Real-Time Microstructure & Execution Research  
**Market:** BTCUSDT  
**Data source:** Binance public real-time WebSocket streams  
**Sampling resolution:** 1-second feature aggregation

---

## 1. Purpose

The exploratory stage identified Level-1 order-book imbalance as the primary
candidate signal for short-horizon BTCUSDT mid-price movement.

This document freezes the methodology before any holdout data are collected
or inspected.

The purpose of the next stage is to test whether the previously observed
relationship persists in genuinely unseen market windows.

No methodological changes should be made in response to holdout results.

---

## 2. Exploratory Development Sample

The exploratory robustness sample consists of the following valid sessions:

| Label | Session ID |
|---|---|
| afternoon_1 | 20260824_135129 |
| morning_1 | 20260825_084855 |
| morning_2 | 20260826_085550 |
| evening_1 | 20260826_144545 |
| late_afternoon_1 | 20260826_151328 |

The failed WebSocket collection:

`20260826_150217`

is excluded because the session was incomplete.

The final two valid exploratory windows are temporally close and therefore
must not automatically be interpreted as fully independent market regimes.

These exploratory sessions must NOT be used as holdout observations.

---

## 3. Frozen Primary Signal

The primary signal is:

`median_book_imbalance`

defined from Level-1 bid and ask quantities as:

\[
I_t =
\frac{Q^{bid}_t - Q^{ask}_t}
     {Q^{bid}_t + Q^{ask}_t}
\]

where:

- \(Q^{bid}_t\) = displayed best-bid quantity
- \(Q^{ask}_t\) = displayed best-ask quantity

The signal remains bounded approximately between -1 and +1.

No transformation, winsorization, normalization, clipping, nonlinear
mapping, or alternative order-book definition may be introduced during
holdout validation.

---

## 4. Secondary Signal

The secondary descriptive signal remains:

`trade_flow_imbalance`

defined from aggressive buy and sell volume.

It is retained for comparison but is NOT the primary hypothesis.

The primary holdout hypothesis concerns Level-1 book imbalance.

---

## 5. Frozen Prediction Targets

### Primary horizon

`future_return_1s_bps`

The future mid-price return from the current observation to approximately
one second ahead, expressed in basis points.

### Secondary horizon

`future_return_5s_bps`

The future mid-price return approximately five seconds ahead, expressed in
basis points.

No additional horizons may be selected after viewing holdout results.

---

## 6. Frozen Activity Conditions

The original activity thresholds remain:

- all eligible observations
- at least 5 trades per second
- at least 10 trades per second
- at least 25 trades per second

The primary high-activity sensitivity condition is:

`trades >= 25 per second`

These thresholds must not be changed in response to holdout performance.

---

## 7. Frozen Quantile Analysis

Book imbalance is divided using:

`pandas.qcut(..., q=5, labels=False, duplicates="drop")`

The main descriptive statistic is:

\[
Q_{high} - Q_{low}
\]

where the mean future return in the highest available signal bucket is
subtracted from the mean future return in the lowest available signal bucket.

For book imbalance, all valid one-second observations are eligible.

For unrestricted trade-flow imbalance analysis, seconds with zero trades
are excluded before quantile construction.

No alternative bucket count may be selected during holdout analysis.

---

## 8. Frozen Regression Model

For each session separately:

\[
r_{t+h}
=
\alpha
+
\beta I_t
+
\epsilon_t
\]

where:

- \(I_t\) = median Level-1 book imbalance
- \(r_{t+h}\) = future mid-price return in basis points
- \(h\) = 1 second or 5 seconds

The primary coefficient is:

\[
\beta_{1s}
\]

A positive coefficient means that greater bid-side imbalance is associated
with higher subsequent mid-price returns.

---

## 9. Frozen HAC / Newey-West Settings

For the +1 second regression:

`maxlags = 5`

For the +5 second regression:

`maxlags = 10`

HAC covariance uses the small-sample correction already implemented in the
statistical-validation script.

These settings must remain unchanged during the holdout stage.

---

## 10. Frozen Non-Overlapping +5 Second Sensitivity Check

Because adjacent +5 second future returns overlap mechanically, a secondary
sensitivity analysis retains every fifth eligible observation.

The non-overlapping +5 second regression uses:

`HAC maxlags = 1`

This analysis is secondary to the +1 second primary hypothesis.

---

## 11. Frozen Moving-Block Bootstrap

The moving-block bootstrap settings are:

- block length: 30 seconds
- repetitions: 1,000
- initial random seed: 42
- session-specific seeds: initial seed + session index

The bootstrap is applied to the +1 second book-imbalance slope.

Its purpose is to preserve short-range temporal dependence within each
session.

These values must not be tuned after viewing holdout results.

---

## 12. Holdout Sampling Plan

The next stage requires:

**5 new valid holdout sessions**

Each target session duration is:

**600 seconds**

The holdout sessions should be collected across meaningfully separated
market windows whenever practical.

Preferred design:

- different dates
- different times of day
- different market directions
- different activity conditions

Sessions should not deliberately be selected according to market outcomes.

A failed or incomplete WebSocket collection must be marked invalid before
analytical results are considered.

---

## 13. Holdout Labels

Holdout sessions should use labels such as:

`holdout_1`

`holdout_2`

`holdout_3`

`holdout_4`

`holdout_5`

Time-of-day information should be derived from the UTC session timestamp
rather than inferred from the manually entered label.

---

## 14. Holdout Data Separation

Holdout observations must NOT be used to:

- redefine the primary signal
- change the prediction horizon
- change activity thresholds
- select a new bucket count
- tune HAC lag length
- tune block-bootstrap length
- introduce additional filters
- choose a different target
- choose a new signal after observing performance
- optimize an execution strategy before holdout evaluation is complete

If a methodological change becomes necessary for technical reasons, the
original holdout test must first be reported under the frozen specification.

Any modified methodology must then be treated as a new exploratory stage
requiring another independent holdout sample.

---

## 15. Primary Holdout Questions

The primary holdout evaluation asks:

1. Is the +1 second book-imbalance regression beta positive across new
   sessions?

2. Does the Q-high minus Q-low +1 second book spread remain positive?

3. Does the relationship remain directionally consistent under the frozen
   `>=25 trades/second` condition?

4. Does the moving-block bootstrap continue to support a positive
   relationship?

5. Does the relationship persist across meaningfully separated market
   windows rather than only adjacent samples?

---

## 16. Statistical Interpretation

Session-level results must be reported individually.

Sessions should be equal-weighted when constructing cross-session summaries.

Second-level observations from all sessions must not automatically be pooled
into one large sample and treated as independent.

A session-level sign test may be reported, but independence assumptions must
be stated explicitly.

The holdout result should not be declared successful merely because a
single p-value is below 0.05.

Effect size, sign consistency, uncertainty, temporal separation, and
economic magnitude must be considered together.

---

## 17. Current Exploratory Benchmark

Before holdout collection, the exploratory five-window analysis produced:

### +1 second book-imbalance regression

- positive beta in 5 / 5 valid windows
- all-window mean beta: approximately +0.2273 bps
- conservative four-period mean beta: approximately +0.2147 bps

### Equal-weighted moving-block bootstrap

All five valid windows:

- mean beta: approximately +0.2291 bps
- 95% interval: approximately [+0.1891, +0.2692]

Conservative four-period set:

- mean beta: approximately +0.2167 bps
- 95% interval: approximately [+0.1702, +0.2664]

### Exploratory Q-high minus Q-low result

The +1 second book-imbalance spread was positive in 5 / 5 windows.

These values are exploratory benchmarks only.

They are NOT holdout results.

---

## 18. Economic Validation Is Separate

Statistical predictability does not imply executable profitability.

No claim of executable alpha may be made until the signal is evaluated under
realistic execution assumptions including:

- bid-ask spread
- maker/taker fees
- latency
- slippage
- adverse selection
- fill probability
- inventory exposure
- position limits
- turnover
- implementation delay

Execution modelling begins only after the frozen holdout evaluation.

---

## 19. Interpretation Standard

A defensible result should distinguish among:

1. descriptive association
2. statistically persistent predictability
3. out-of-sample predictive robustness
4. economically executable alpha

The current exploratory work has progressed beyond simple descriptive
correlation but has not yet established levels 3 or 4.

The holdout stage tests level 3.

A later execution simulator will test level 4.

---

## 20. Freeze Declaration

As of the date at the top of this document:

- the primary signal is frozen
- prediction horizons are frozen
- activity thresholds are frozen
- regression specification is frozen
- HAC settings are frozen
- bootstrap settings are frozen
- quantile methodology is frozen

The next unseen observations are designated as holdout data.

No analytical parameter should be modified in response to their results
until the pre-specified holdout evaluation has been completed and reported.