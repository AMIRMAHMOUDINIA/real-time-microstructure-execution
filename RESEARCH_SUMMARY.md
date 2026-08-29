# Real-Time Microstructure Execution Research

## Research Summary

### Project Objective

This project investigates whether a simple Level-1 order-book imbalance signal contains short-horizon predictive information and, more importantly, whether that information survives realistic execution constraints.

The research was deliberately separated into distinct stages:

**signal discovery → statistical validation → frozen execution design → unseen execution validation → robustness diagnostics**

The objective was not to maximize backtest performance. The objective was to determine whether a pre-specified microstructure relationship could survive increasingly realistic tests without modifying the signal after observing holdout results.

The instrument studied was **BTCUSDT** using live Binance market data.

---

# 1. Research Question

The primary research question was:

> Does Level-1 order-book imbalance predict very short-horizon mid-price changes, and can that predictive relationship survive causal aggressive bid/ask execution with realistic latency and transaction-cost stress?

The primary signal was:

\[
I_t =
\frac{Q^{bid}_t-Q^{ask}_t}
     {Q^{bid}_t+Q^{ask}_t}
\]

where:

- \(Q^{bid}_t\) is best-bid quantity;
- \(Q^{ask}_t\) is best-ask quantity.

The primary one-second feature was the **median book imbalance** observed during each one-second interval.

The primary prediction horizon was:

\[
t+1 \text{ second}
\]

A five-second horizon was retained as a secondary statistical diagnostic.

---

# 2. Live Data Architecture

Two real-time Binance WebSocket streams were collected.

## Level-1 Book

BTCUSDT `bookTicker`

Recorded information included:

- local UTC receipt timestamp;
- exchange update ID;
- best bid;
- best bid quantity;
- best ask;
- best ask quantity;
- mid-price;
- spread;
- Level-1 imbalance.

## Trades

BTCUSDT `trade`

Recorded information included:

- local receipt timestamp;
- exchange event timestamp;
- exchange trade timestamp;
- trade ID;
- price;
- quantity;
- quote notional;
- buyer-is-maker flag;
- inferred aggressor side.

A buyer-is-maker trade was interpreted as a **seller-aggressed SELL**.

Local `received_at_utc` was later used as the execution clock because it represents when information became observable by the research process.

---

# 3. One-Second Feature Construction

Raw observations were aggregated into one-second intervals.

Book features included:

- last mid-price;
- mean spread;
- median spread;
- mean book imbalance;
- median book imbalance;
- number of book updates;
- mean bid quantity;
- mean ask quantity.

Trade features included:

- trade count;
- total traded quantity;
- buy quantity;
- sell quantity;
- total notional;
- buy notional;
- sell notional;
- mean trade size;
- trade-flow imbalance.

Forward mid-price returns were constructed at:

\[
+1s
\]

and

\[
+5s
\]

No-trade seconds were explicitly represented rather than removed from the one-second feature grid.

---

# 4. Exploratory Development Stage

Five development windows were used for exploratory research:

- afternoon_1
- morning_1
- morning_2
- evening_1
- late_afternoon_1

Each valid session contained approximately ten minutes of live data.

Exploratory signal-bucket analysis showed that extreme Level-1 book imbalance was associated with subsequent mid-price movement in the expected direction.

For the primary one-second horizon, the unrestricted high-minus-low imbalance-bucket spread was positive in all five development sessions.

The equal-weight development spread was approximately:

\[
+0.4243 \text{ bps}
\]

For the five-second horizon:

\[
+1.3115 \text{ bps}
\]

At the high-activity threshold of at least 25 trades per second, the one-second spread was approximately:

\[
+0.4984 \text{ bps}
\]

These results were exploratory and were **not treated as out-of-sample evidence**.

---

# 5. Statistical Validation Protocol

Before inspecting new validation sessions, a formal statistical protocol was frozen.

Protocol SHA256:

    6d2ed10e1e18b04e873cebee8033191fc8710866eedd3d574e4b547aabc491da

The pre-specified settings included:

- primary signal: `median_book_imbalance`;
- secondary signal: trade-flow imbalance;
- primary horizon: +1 second;
- secondary horizon: +5 seconds;
- activity filters: unrestricted, >=5, >=10, >=25 trades/second;
- primary high-activity specification: >=25 trades/second;
- imbalance quantiles: five buckets;
- primary regression: OLS with HAC standard errors;
- +1 second HAC lag: 5;
- +5 second HAC lag: 10;
- non-overlapping +5 second diagnostic;
- 30-second moving-block bootstrap;
- 1,000 bootstrap repetitions;
- random seed: 42;
- five completely new 600-second holdout sessions;
- no tuning using holdout results.

---

# 6. Statistical Holdout Validation

Five new sessions were collected only after the statistical protocol was frozen:

    holdout_1   20260826_202754
    holdout_2   20260827_083158
    holdout_3   20260827_195947
    holdout_4   20260828_153334
    holdout_5   20260829_091754

All five produced a positive one-second book-imbalance bucket spread.

## +1 Second Bucket Spread

| Session | High-minus-low spread |
|---|---:|
| holdout_1 | +0.2521 bps |
| holdout_2 | +0.3874 bps |
| holdout_3 | +0.3572 bps |
| holdout_4 | +0.4207 bps |
| holdout_5 | +0.0712 bps |

Equal-weight mean:

\[
+0.2977 \text{ bps}
\]

Median:

\[
+0.3572 \text{ bps}
\]

All five sessions were positive.

The exact one-sided sign-test probability for five positive outcomes was:

\[
p=0.03125
\]

The five-second bucket-spread result was also positive in all five holdout sessions, with an equal-weight mean of approximately:

\[
+0.8805 \text{ bps}
\]

At the pre-specified high-activity filter of at least 25 trades per second, the one-second high-minus-low spread remained positive in all five sessions.

Equal-weight high-activity result:

\[
+0.4131 \text{ bps}
\]

---

# 7. HAC Regression Validation

The primary one-second median-book-imbalance regression coefficient was positive in every holdout session.

| Session | Beta | HAC SE | Approx. p-value |
|---|---:|---:|---:|
| holdout_1 | +0.1217 | 0.0182 | <0.001 |
| holdout_2 | +0.2344 | 0.0378 | <0.001 |
| holdout_3 | +0.2164 | 0.0331 | <0.001 |
| holdout_4 | +0.2038 | 0.0472 | <0.001 |
| holdout_5 | +0.0353 | 0.0092 | 0.0001 |

All five coefficients had the expected positive sign.

Equal-weight development coefficient:

\[
+0.2273
\]

Equal-weight holdout coefficient:

\[
+0.1623
\]

Approximate holdout retention:

\[
\frac{0.1623}{0.2273}
\approx 71.4\%
\]

The signal therefore weakened out of sample, as expected, but did not disappear.

---

# 8. Statistical Holdout Conclusion

The statistical stage supported the conclusion that Level-1 book imbalance contained reproducible short-horizon directional information.

The primary relationship:

- had the expected sign in all five unseen sessions;
- survived HAC inference;
- remained positive under high-activity filtering;
- remained positive at the secondary five-second horizon;
- showed expected out-of-sample shrinkage rather than collapse.

However, statistical predictability is not equivalent to executable alpha.

The next research question therefore became:

> Can the validated signal survive the bid/ask spread, causal timing, modeled execution latency, and additional trading-cost stress?

This required a separate frozen execution protocol.

---

# 9. Frozen Execution Protocol

Before testing execution economics, a dedicated execution protocol was frozen.

Execution protocol SHA256:

    ef534c27856907e45ac871db8d4d499ddb338ffe114169f3ea2ee796f8265d6e

The execution experiment fixed:

- primary signal: `median_book_imbalance`;
- primary horizon: one second;
- development-only threshold calibration;
- causal decision timing;
- local receipt timestamps as the execution clock;
- aggressive bid/ask execution;
- one-second holding period from actual entry;
- one open position at a time;
- no immediate reversal;
- no stop loss;
- no take profit;
- a pre-specified latency grid;
- a pre-specified additional-cost grid;
- equal session weighting for the primary endpoint;
- no tuning using execution holdout results.

---

# 10. Development-Only Threshold Calibration

Execution thresholds were calibrated using only the five development sessions.

The development feature sample contained:

    3,000 valid one-second observations

The pooled 20th percentile of median book imbalance was:

\[
-0.8112458586
\]

The pooled 80th percentile was:

\[
+0.8195917760
\]

The frozen trading rule became:

    SHORT  if median_book_imbalance <= -0.8112458586
    LONG   if median_book_imbalance >= +0.8195917760
    FLAT   otherwise

The calibration produced:

    600 SHORT observations
    600 LONG observations
    1,800 FLAT observations

Execution-parameter SHA256:

    1fc3aa7cd92408161c41c067d4329d2f93953361637fbd143b03f2c0a1e2298b

These thresholds were never recalibrated using the holdout execution sample.

---

# 11. Causal Signal Timing

A one-second feature timestamp \(t\) summarizes information observed during:

\[
[t,t+1)
\]

Information from that interval is therefore not fully available at time \(t\).

The earliest valid decision time is:

\[
t+1
\]

For modeled execution latency \(L\), target entry becomes:

\[
t+1+L
\]

The simulator uses the first valid raw Level-1 quote whose local `received_at_utc` is at or after the target timestamp.

A quote observed before the target timestamp is never eligible.

This convention prevents look-ahead execution.

---

# 12. Aggressive Bid/Ask Execution Model

The confirmatory model uses aggressive Level-1 prices.

## Long Position

Entry:

    best ask

Exit:

    best bid

## Short Position

Entry:

    best bid

Exit:

    best ask

The observed bid/ask spread is therefore incorporated naturally through transaction prices.

No separate spread penalty is deducted.

The nominal holding period is:

\[
1.0 \text{ second}
\]

measured from the actual entry timestamp.

The target exit timestamp is:

\[
actual\ entry + 1s
\]

The simulator again selects the first quote observed at or after the target exit timestamp.

Only one normalized unit position may be open at a time.

Signals arriving while a position is active are ignored.

There is:

- no overlapping exposure;
- no pyramiding;
- no stop-loss optimization;
- no take-profit optimization;
- no immediate reversal rule;
- no passive queue-position assumption.

---

# 13. Execution Latency Grid

The execution protocol pre-specified the following latency assumptions:

    0 ms
    50 ms
    100 ms
    250 ms
    500 ms
    1000 ms

The primary reference latency was:

\[
100 \text{ ms}
\]

The simulator does not assume that a quote exists exactly at the target timestamp.

Instead, it waits for the first valid locally received quote at or after the target.

Therefore actual decision-to-entry latency generally equals:

\[
modeled\ latency + quote\ waiting\ time
\]

This additional quote-wait delay is retained rather than removed.

---

# 14. Additional Cost Grid

The execution protocol also pre-specified additional costs per side:

    0.00 bps
    0.05 bps
    0.10 bps
    0.25 bps
    0.50 bps
    1.00 bps
    2.00 bps
    5.00 bps

For an additional per-side cost \(c\):

\[
net\ return =
gross\ return - 2c
\]

The bid/ask spread itself is already incorporated through aggressive entry and exit prices.

Therefore this grid represents friction beyond observed spread crossing.

The continuous break-even additional cost per side is:

\[
\frac{mean\ gross\ return}{2}
\]

---

# 15. Execution Engine Validation

Before running holdout execution, the simulator was tested only on development data.

A pandas timestamp-unit issue was identified during development testing.

The original implementation compared timestamp integer representations with inconsistent internal units.

This produced impossible quote-search behavior and zero completed trades.

The issue was identified before any meaningful execution result was observed.

The implementation was corrected to use timestamp-aware `DatetimeIndex.searchsorted()` directly.

No signal rule, threshold, holding period, execution convention, or research hypothesis was changed.

After correction, the execution engine passed all automated causal checks.

The checks verified that:

- decision time equals the end of the feature bucket;
- target entry occurs at or after the decision time plus modeled latency;
- actual entry occurs at or after target entry;
- target exit occurs one second after actual entry;
- actual exit occurs at or after target exit;
- actual decision-to-entry delay respects the modeled latency;
- actual holding time is at least one second;
- positions never overlap.

Execution engine SHA256:

    7a24cbe27a2f7e92e2d935ed22cb7de7f764f457a1e96f1f868fc1266ce39e23

The development execution engine was then frozen.

---

# 16. Development Execution Results

At the primary 100 ms reference latency:

| Session | Completed trades | Mean gross return |
|---|---:|---:|
| afternoon_1 | 180 | +0.2222 bps |
| morning_1 | 112 | +0.1387 bps |
| morning_2 | 153 | +0.1955 bps |
| evening_1 | 150 | +0.1022 bps |
| late_afternoon_1 | 153 | +0.2242 bps |

All five development sessions were positive.

Equal-weight development mean:

\[
+0.1766 \text{ bps/trade}
\]

Approximate equal-weight break-even additional cost:

\[
+0.0883 \text{ bps/side}
\]

The median trade return was slightly negative in every development session.

This indicated that the positive mean was not produced by a high winning percentage, but by an asymmetric return distribution.

The development execution stage was frozen before holdout execution was evaluated.

---

# 17. Development Latency Sensitivity

Development equal-weight results were:

| Latency | Mean gross return |
|---|---:|
| 0 ms | +0.2071 bps |
| 50 ms | +0.1937 bps |
| 100 ms | +0.1766 bps |
| 250 ms | +0.1683 bps |
| 500 ms | +0.1384 bps |
| 1000 ms | +0.1060 bps |

The general pattern was decreasing performance as latency increased.

At 1000 ms, four of five development sessions remained positive.

The development result therefore showed latency sensitivity before holdout execution was examined.

---

# 18. Development Cost Frontier

At the primary 100 ms latency:

| Additional cost per side | Equal-weight mean net return |
|---|---:|
| 0.00 bps | +0.1766 bps |
| 0.05 bps | +0.0766 bps |
| 0.10 bps | -0.0234 bps |
| 0.25 bps | -0.3234 bps |
| 0.50 bps | -0.8234 bps |
| 1.00 bps | -1.8234 bps |
| 2.00 bps | -3.8234 bps |
| 5.00 bps | -9.8234 bps |

The development evidence therefore already suggested that execution economics were fragile to additional cost.

---

# 19. Frozen Holdout Execution Evaluator

The holdout evaluator was fingerprinted before its first run.

Holdout evaluator SHA256:

    807170b22848fc9de12c2598a000e6fcb12d71fa90d925419c7884557f947644

Before executing, the evaluator verified the frozen hashes of:

- the execution protocol;
- the execution parameters;
- the execution engine;
- the development evaluator;
- development session-by-latency results;
- development latency results;
- development cost results.

No execution parameter was changed after the holdout evaluator was frozen.

The five holdout sessions were then evaluated in a single confirmatory execution run.

---

# 20. One-Shot Holdout Execution Results

At the primary 100 ms latency:

| Session | Completed trades | Mean gross return | Break-even cost/side |
|---|---:|---:|---:|
| holdout_1 | 133 | +0.1104 bps | +0.0552 bps |
| holdout_2 | 137 | +0.2149 bps | +0.1074 bps |
| holdout_3 | 147 | +0.2409 bps | +0.1205 bps |
| holdout_4 | 167 | +0.2545 bps | +0.1273 bps |
| holdout_5 | 78 | +0.0459 bps | +0.0229 bps |

All five holdout sessions were positive.

Equal-weight holdout mean:

\[
\boxed{+0.1733 \text{ bps/trade}}
\]

Equal-weight median session mean:

\[
+0.2149 \text{ bps/trade}
\]

Equal-weight break-even additional cost:

\[
\boxed{+0.0867 \text{ bps/side}}
\]

Execution Level-2 status:

    PASS

The frozen holdout reference-trade file contained:

    662 completed trades

Holdout trade file SHA256:

    b5b76ddeddedcaac55d01ecf23e0a5ee6fa610085695604a3660fdec5e713b33

---

# 21. Development-to-Holdout Retention

At the primary 100 ms latency:

Development:

\[
+0.1766 \text{ bps/trade}
\]

Holdout:

\[
+0.1733 \text{ bps/trade}
\]

Therefore:

\[
\frac{0.1733}{0.1766}
\approx 98.2\%
\]

The execution-stage effect showed very little degradation between development and the five unseen holdout windows.

This close retention is encouraging, but it must be interpreted in the context of a limited observation period.

---

# 22. Holdout Latency Sensitivity

Holdout equal-weight results were:

| Latency | Completed trades | Mean gross return | Positive sessions |
|---|---:|---:|---:|
| 0 ms | 663 | +0.1804 bps | 5/5 |
| 50 ms | 662 | +0.1731 bps | 5/5 |
| 100 ms | 662 | +0.1733 bps | 5/5 |
| 250 ms | 658 | +0.1644 bps | 5/5 |
| 500 ms | 652 | +0.1327 bps | 5/5 |
| 1000 ms | 502 | +0.1011 bps | 5/5 |

Performance generally declined as latency increased.

From 0 ms to 1000 ms, the equal-weight mean fell by approximately:

\[
44\%
\]

All five holdout sessions nevertheless remained positive throughout the complete pre-specified latency grid.

---

# 23. Holdout Transaction-Cost Frontier

At the primary 100 ms latency:

| Additional cost per side | Equal-weight mean net return | Positive sessions |
|---|---:|---:|
| 0.00 bps | +0.1733 bps | 5/5 |
| 0.05 bps | +0.0733 bps | 4/5 |
| 0.10 bps | -0.0267 bps | 3/5 |
| 0.25 bps | -0.3267 bps | 0/5 |
| 0.50 bps | -0.8267 bps | 0/5 |
| 1.00 bps | -1.8267 bps | 0/5 |
| 2.00 bps | -3.8267 bps | 0/5 |
| 5.00 bps | -9.8267 bps | 0/5 |

The largest pre-specified grid cost with a positive equal-weight mean was:

\[
0.05 \text{ bps/side}
\]

The continuous break-even estimate was approximately:

\[
0.0867 \text{ bps/side}
\]

This is the principal economic limitation of the strategy.

The predictive relationship appears considerably stronger than the remaining monetizable margin after aggressive execution.

---

# 24. Return Distribution

At the primary 100 ms execution specification, the frozen holdout trade file contained:

    662 completed trades

Pooled gross-return statistics were:

| Statistic | Result |
|---|---:|
| Mean | +0.189754 bps |
| Median | -0.001253 bps |
| Standard deviation | 0.552915 bps |
| Minimum | -3.686000 bps |
| Maximum | +4.137445 bps |
| Total gross return | +125.617152 bps |

Trade outcomes were:

| Outcome | Trades | Share |
|---|---:|---:|
| Positive | 201 | 30.36% |
| Negative | 454 | 68.58% |
| Exactly zero | 7 | 1.06% |

Mean winning trade:

\[
+0.717591 \text{ bps}
\]

Mean losing trade:

\[
-0.041010 \text{ bps}
\]

The approximate magnitude ratio was therefore:

\[
\frac{0.717591}{0.041010}
\approx 17.5
\]

The strategy does not rely on a high hit rate.

Its positive expectation is generated by relatively infrequent favorable price moves whose magnitude is much larger than that of the typical losing trade.

The negative median trade is consistent with many observations paying approximately one spread-crossing outcome while larger directional moves generate the positive mean.

---

# 25. Return Quantiles

The pooled 100 ms holdout return distribution had the following quantiles:

| Quantile | Gross return |
|---|---:|
| 1% | -1.007885 bps |
| 5% | -0.001288 bps |
| 10% | -0.001288 bps |
| 25% | -0.001276 bps |
| 50% | -0.001253 bps |
| 75% | +0.179342 bps |
| 90% | +0.814673 bps |
| 95% | +1.225440 bps |
| 99% | +2.063753 bps |

The distribution is strongly right-skewed.

---

# 26. Tail Concentration

The contribution of the largest trades to total gross PnL was:

| Largest trades | Share of total gross PnL |
|---|---:|
| Top 1% | 16.42% |
| Top 5% | 51.32% |
| Top 10% | 78.37% |

The result is therefore materially dependent on the upper tail.

However, removing those largest observations did not immediately eliminate positive expectancy.

| Removed observations | Remaining pooled mean |
|---|---:|
| Top 1% | +0.160298 bps |
| Top 5% | +0.097364 bps |
| Top 10% | +0.045656 bps |

The positive result is therefore tail-dependent, but it is not explained exclusively by a handful of extreme trades.

---

# 27. Positive-PnL Concentration

Among positive trades:

    41 trades explained 50% of positive PnL
    92 trades explained 80% of positive PnL
    123 trades explained 90% of positive PnL

This confirms that relatively large favorable moves play a major role in strategy economics.

Any production implementation would therefore be sensitive to execution failure during those comparatively infrequent high-value events.

---

# 28. Session Robustness After Removing Extreme Winners

The best 5% of trades were removed independently from each holdout session.

| Session | Original mean | Mean without top 5% | Remains positive |
|---|---:|---:|---:|
| holdout_1 | +0.110366 | +0.038492 | Yes |
| holdout_2 | +0.214899 | +0.135002 | Yes |
| holdout_3 | +0.240904 | +0.146382 | Yes |
| holdout_4 | +0.254518 | +0.131312 | Yes |
| holdout_5 | +0.045895 | +0.004369 | Yes |

Every holdout session remained positive after this trimming procedure.

Holdout 5 became marginal, but did not become negative.

---

# 29. Long vs Short Performance

Both trading directions contributed positively.

| Direction | Trades | Mean return | Median return | Total return | Positive rate |
|---|---:|---:|---:|---:|---:|
| LONG | 315 | +0.203866 bps | -0.001253 bps | +64.217896 bps | 28.57% |
| SHORT | 347 | +0.176943 bps | -0.001253 bps | +61.399255 bps | 31.99% |

Both sides therefore contributed materially to the aggregate result.

---

# 30. Session-by-Direction Robustness

All ten session-direction combinations had positive mean gross returns.

| Session | Direction | Trades | Mean return |
|---|---|---:|---:|
| holdout_1 | LONG | 69 | +0.091551 bps |
| holdout_1 | SHORT | 64 | +0.130652 bps |
| holdout_2 | LONG | 83 | +0.305197 bps |
| holdout_2 | SHORT | 54 | +0.076107 bps |
| holdout_3 | LONG | 79 | +0.246186 bps |
| holdout_3 | SHORT | 68 | +0.234768 bps |
| holdout_4 | LONG | 43 | +0.274044 bps |
| holdout_4 | SHORT | 124 | +0.247747 bps |
| holdout_5 | LONG | 41 | +0.032607 bps |
| holdout_5 | SHORT | 37 | +0.060620 bps |

This is particularly relevant for holdout_4, which occurred during a strongly declining market window.

The aggregate execution result was not generated solely by short exposure during that bearish regime.

---

# 31. Leave-One-Session-Out Stability

The five reference-session means were:

| Session | Mean gross return |
|---|---:|
| holdout_1 | +0.110366 bps |
| holdout_2 | +0.214899 bps |
| holdout_3 | +0.240904 bps |
| holdout_4 | +0.254518 bps |
| holdout_5 | +0.045895 bps |

Removing one session at a time produced:

| Removed session | Remaining equal-weight mean |
|---|---:|
| holdout_1 | +0.189054 bps |
| holdout_2 | +0.162921 bps |
| holdout_3 | +0.156420 bps |
| holdout_4 | +0.153016 bps |
| holdout_5 | +0.205172 bps |

The minimum leave-one-session-out result was:

\[
+0.153016 \text{ bps/trade}
\]

The positive result was therefore not dependent on a single holdout session.

---

# 32. Execution Stability Diagnostic

A post-hoc uncertainty diagnostic was performed after the confirmatory execution result had been frozen.

The diagnostic settings were:

    block length = 30 seconds
    bootstrap repetitions = 5,000
    random seed = 42

Two procedures were evaluated:

1. fixed-session 30-second block bootstrap;
2. hierarchical session plus 30-second block bootstrap.

The hierarchical procedure was treated as the more conservative diagnostic because it resampled both observed market windows and within-session blocks.

This analysis did not change any trading rule or execution parameter.

---

# 33. Gross Bootstrap Stability

For zero additional cost, the hierarchical bootstrap produced:

\[
mean = +0.173349 \text{ bps}
\]

Median:

\[
+0.173235 \text{ bps}
\]

95% interval:

\[
\boxed{[+0.091472,\,+0.253147]}
\]

Bootstrap probability of a positive mean:

\[
1.0000
\]

Within the five observed holdout windows, the gross spread-aware execution result therefore remained positive under hierarchical resampling.

---

# 34. Stability at 0.05 bps per Side

At an additional cost of:

\[
0.05 \text{ bps/side}
\]

the hierarchical bootstrap produced:

\[
mean = +0.073349 \text{ bps}
\]

95% interval:

\[
[-0.008528,\,+0.153147]
\]

Probability of positive mean:

\[
0.9596
\]

The point estimate remained positive, but the two-sided 95% interval crossed zero.

This cost level should therefore be described as:

> positive on average and promising within the observed sample, but not statistically secure under the conservative hierarchical uncertainty diagnostic.

---

# 35. Stability at 0.10 bps per Side

At an additional cost of:

\[
0.10 \text{ bps/side}
\]

the hierarchical bootstrap produced:

\[
mean = -0.026651 \text{ bps}
\]

95% interval:

\[
[-0.108528,\,+0.053147]
\]

Probability of positive mean:

\[
0.2686
\]

The economic edge was therefore no longer supported at this cost level.

---

# 36. Main Research Finding

The completed confirmatory research supports the following statement:

> A pre-specified Level-1 book-imbalance signal replicated across five unseen market windows and retained positive average returns under causal aggressive bid/ask execution with 100 ms modeled latency. The equal-weight holdout execution result was approximately +0.173 bps/trade and closely matched the development result of approximately +0.177 bps/trade. The effect remained positive across all five holdout sessions, both trading directions, the complete latency grid, leave-one-session-out analysis, tail-removal diagnostics, and hierarchical block resampling. However, economic viability was highly transaction-cost sensitive, with an estimated additional break-even cost of only approximately 0.087 bps per side.

This is evidence of an execution-aware short-horizon microstructure relationship.

It is not evidence of production-ready alpha.

---

# 37. What the Project Demonstrates

The completed research cycle was:

    live market-data acquisition
            ↓
    feature engineering
            ↓
    exploratory signal analysis
            ↓
    dependence-aware statistical inference
            ↓
    frozen statistical protocol
            ↓
    unseen statistical holdout
            ↓
    frozen execution protocol
            ↓
    development-only threshold calibration
            ↓
    causal bid/ask simulator
            ↓
    development execution validation
            ↓
    frozen holdout evaluator
            ↓
    one-shot unseen execution holdout
            ↓
    latency analysis
            ↓
    cost frontier
            ↓
    tail diagnostics
            ↓
    dependence-aware execution stability

The primary methodological principle was that favorable holdout results were not used to modify the original confirmatory strategy.

---

# 38. What the Project Does Not Establish

The study does not establish production-ready profitability.

The confirmatory sample contains only five approximately ten-minute market windows.

Therefore the current evidence does not establish stability across:

- months;
- years;
- different volatility regimes;
- weekends and weekdays;
- macroeconomic announcements;
- liquidation events;
- structural exchange changes;
- alternative cryptocurrency instruments;
- alternative exchanges.

The execution model also does not include:

- actual order submission;
- exchange acknowledgements;
- measured network round-trip latency;
- real order-routing infrastructure;
- market impact;
- partial fills;
- order rejection;
- venue-specific real fee schedules;
- passive queue-position mechanics;
- exchange or infrastructure failure;
- capital constraints;
- portfolio-level risk management.

Aggressive execution avoids the need to assume passive queue position, but it does not remove real implementation uncertainty.

---

# 39. Bootstrap Interpretation Boundary

The hierarchical bootstrap is conditional on the observed dataset.

It should not be interpreted as proof that future expected returns lie inside the reported interval.

Only five holdout sessions were observed.

The bootstrap can resample:

- the observed sessions;
- the observed 30-second blocks.

It cannot create market regimes that were never present in the sample.

Longer prospective testing is therefore necessary.

---

# 40. Research Integrity Boundary

The five current holdout sessions are now considered consumed confirmatory data.

They must not be used to optimize:

- imbalance thresholds;
- holding periods;
- signal combinations;
- activity filters;
- execution latency;
- transaction-cost assumptions;
- direction-specific rules;
- stop-loss rules;
- take-profit rules;
- position sizing;
- inventory rules.

If those sessions are used for future model development, they must be explicitly reclassified as development data.

Any resulting strategy would require a new independent holdout dataset.

The current confirmatory result remains frozen.

---

# 41. Current Research Status

    Live data collection                         COMPLETE
    Feature engineering                          COMPLETE
    Exploratory signal analysis                  COMPLETE
    Statistical protocol                         FROZEN
    Statistical holdout validation               PASS

    Execution protocol                           FROZEN
    Execution thresholds                         FROZEN
    Causal execution engine                      VALIDATED
    Development execution                        COMPLETE
    Development latency analysis                 COMPLETE
    Development cost analysis                    COMPLETE
    Holdout execution evaluator                  FROZEN
    One-shot execution holdout                   PASS

    Holdout latency analysis                     COMPLETE
    Holdout cost frontier                        COMPLETE
    Tail-concentration analysis                  COMPLETE
    Long/short diagnostics                       COMPLETE
    Leave-one-session-out analysis               COMPLETE
    Hierarchical bootstrap stability             COMPLETE

    Production profitability                     NOT ESTABLISHED
    Long-horizon regime robustness               NOT ESTABLISHED
    Real-money execution                         NOT TESTED

---

# 42. Reproducibility Checkpoints

## Statistical Validation Protocol

    6d2ed10e1e18b04e873cebee8033191fc8710866eedd3d574e4b547aabc491da

## Execution Protocol

    ef534c27856907e45ac871db8d4d499ddb338ffe114169f3ea2ee796f8265d6e

## Execution Parameters

    1fc3aa7cd92408161c41c067d4329d2f93953361637fbd143b03f2c0a1e2298b

## Execution Engine

    7a24cbe27a2f7e92e2d935ed22cb7de7f764f457a1e96f1f868fc1266ce39e23

## Development Execution Evaluator

    a1e7335beb0890a2f7bffc8f94ba0b0147f8f0d7d5b7fb9382aaebec9f08c053

## Holdout Execution Evaluator

    807170b22848fc9de12c2598a000e6fcb12d71fa90d925419c7884557f947644

## Frozen Holdout Reference Trades

    b5b76ddeddedcaac55d01ecf23e0a5ee6fa610085695604a3660fdec5e713b33

## Tail Diagnostic Script

    85b214512847993409040455f9cbc41b67a4899ba41c88be4df1b9ade2b60a82

## Stability Diagnostic Script

    39a8afb2340e77810cf5d29d1da2ccb644c0eb2c7df02b29232f805f0385aebc

## Stability Bootstrap Results

    fd405d86f175da76ba530bf20df98593b837dcdcb6dde60c37da0756c338d220

## Stability Session Results

    7264a981574ec3f031b91d71ac1cf9f20a34eac613e601bb54edc664dade54f9

---

# 43. Phase II — Future Work

The completed confirmatory strategy should not be tuned using the current holdout sessions.

Future work should be clearly separated from the completed research cycle.

## Prospective Forward Monitoring

Collect substantially more independent live sessions while keeping the current signal frozen.

The objective is to evaluate performance across:

- different times of day;
- different weekdays;
- high-volatility regimes;
- low-volatility regimes;
- trending markets;
- range-bound markets;
- major market events;
- changing liquidity conditions.

## Live Paper Execution

Operate the same causal execution logic prospectively and record:

- signal timestamp;
- decision timestamp;
- target entry;
- observable entry quote;
- target exit;
- observable exit quote;
- quote waiting delay;
- modeled gross return;
- modeled net return;
- skipped executions;
- incomplete executions.

## Inventory and Risk

Introduce bounded inventory mechanics such as:

\[
position \in \{-1,0,+1\}
\]

and study:

- exposure duration;
- inventory risk;
- turnover;
- risk-adjusted returns;
- loss clustering;
- session drawdowns.

This should be treated as a new engineering and research extension rather than a modification of the completed confirmatory experiment.

## Regime Research

With new development data, investigate whether the frozen signal behaves differently as a function of:

- spread;
- short-horizon volatility;
- book-update intensity;
- trade activity;
- directional momentum;
- liquidity imbalance.

Any new conditional model must receive its own development and independent holdout cycle.

---

# 44. Portfolio Interpretation

The strongest aspect of this project is not the magnitude of the simulated return.

The strongest aspect is the research process.

The project demonstrates:

- direct collection of live market data;
- asynchronous WebSocket handling;
- Level-1 microstructure feature engineering;
- trade-flow reconstruction;
- careful receipt-time semantics;
- prevention of look-ahead bias;
- development-versus-holdout separation;
- protocol freezing;
- file hashing;
- HAC inference;
- dependence-aware bootstrap analysis;
- genuine unseen-session testing;
- bid/ask-aware execution;
- latency modeling;
- transaction-cost stress;
- return-distribution analysis;
- tail-concentration analysis;
- long/short decomposition;
- explicit failure-boundary reporting;
- reproducible quantitative research.

The result is intentionally presented with both its strengths and its limitations.

That is the intended research standard for this repository.
