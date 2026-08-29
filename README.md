# Real-Time Microstructure Execution Research

Execution-aware BTCUSDT market-microstructure research testing whether **Level-1 order-book imbalance predicts 1-second price moves and survives causal bid/ask execution, latency, and transaction-cost stress**.

**Research design:** live data → signal development → frozen statistical protocol → five unseen holdouts → frozen execution protocol → one-shot execution evaluation → robustness diagnostics.

## Key Results

| Metric | Holdout result |
| --- | ---: |
| Positive holdout sessions | **5 / 5** |
| Completed trades | 662 |
| Equal-weight gross return at 100 ms | **+0.1733 bps/trade** |
| Development-to-holdout retention | **98.2%** |
| Break-even additional cost | **0.0867 bps/side** |

At **0.05 bps additional cost per side**, mean performance remained positive. At **0.10 bps per side**, it became negative.

The result supports a replicated short-horizon microstructure relationship under a causal spread-aware execution model, but the economic margin is narrow. **This is validation evidence, not production-ready alpha.**

[Full research record](RESEARCH_SUMMARY.md) · [Validation protocol](VALIDATION_PROTOCOL.md) · [Execution protocol](EXECUTION_PROTOCOL.md)

---

## Research Architecture

    Binance WebSocket data
            ↓
    Raw Level-1 book + trades
            ↓
    One-second feature construction
            ↓
    Exploratory signal analysis
            ↓
    Frozen statistical protocol
            ↓
    Five unseen statistical holdouts
            ↓
    Frozen execution protocol
            ↓
    Development-only threshold calibration
            ↓
    Causal bid/ask execution simulator
            ↓
    Frozen execution evaluator
            ↓
    Five unseen execution holdouts
            ↓
    Latency + cost sensitivity
            ↓
    Tail-risk diagnostics
            ↓
    Dependence-aware stability analysis

---

## Signal

The primary signal is Level-1 order-book imbalance:

$$
I_t =
\frac{Q_t^{bid} - Q_t^{ask}}
     {Q_t^{bid} + Q_t^{ask}}
$$

where $Q_t^{bid}$ and $Q_t^{ask}$ are the quantities available at the best bid and ask.

One-second observations are aggregated using **median book imbalance**.

The primary prediction horizon is **1 second**.

Development-only thresholds were frozen as:

    SHORT  if imbalance <= -0.8112458586
    LONG   if imbalance >= +0.8195917760
    FLAT   otherwise

---

## Causal Execution Model

A feature timestamp $t$ summarizes information observed during:

$$
[t,t+1)
$$

The strategy therefore cannot act at $t$. The earliest decision occurs at:

$$
t+1
$$

The primary specification adds **100 ms modeled latency** and then selects the **first locally received Level-1 quote at or after the target timestamp**.

No quote observed before the target timestamp is eligible.

For LONG trades:

    Entry: ask
    Exit:  bid

For SHORT trades:

    Entry: bid
    Exit:  ask

The bid/ask spread is therefore incorporated directly through execution prices.

The nominal holding period is **1 second from actual entry**.

Only one position may be open at a time. Signals generated while a position is active are ignored.

---

## One-Shot Execution Holdout

The execution protocol, thresholds, simulator, and evaluator were frozen before the execution model was exposed to the five holdout sessions.

At the primary **100 ms latency**:

| Session | Mean gross return |
| --- | ---: |
| Holdout 1 | +0.1104 bps/trade |
| Holdout 2 | +0.2149 |
| Holdout 3 | +0.2409 |
| Holdout 4 | +0.2545 |
| Holdout 5 | +0.0459 |

All five sessions remained positive.

Equal-weight holdout result:

$$
\boxed{+0.1733\text{ bps/trade}}
$$

Development result:

$$
+0.1766\text{ bps/trade}
$$

Execution-stage retention:

$$
98.2\%
$$

---

## Latency Sensitivity

The latency grid was fixed before holdout execution.

| Latency | Equal-weight gross return |
| --- | ---: |
| 0 ms | +0.1804 bps |
| 50 ms | +0.1731 |
| **100 ms** | **+0.1733** |
| 250 ms | +0.1644 |
| 500 ms | +0.1327 |
| 1000 ms | +0.1011 |

Performance generally declined as latency increased, while all five holdout sessions remained positive throughout the tested grid.

---

## Transaction-Cost Frontier

At the primary 100 ms latency:

| Additional cost per side | Equal-weight mean net return |
| --- | ---: |
| 0.00 bps | +0.1733 bps/trade |
| 0.05 bps | +0.0733 |
| 0.10 bps | -0.0267 |
| 0.25 bps | -0.3267 |
| 0.50 bps | -0.8267 |
| 1.00 bps | -1.8267 |
| 2.00 bps | -3.8267 |
| 5.00 bps | -9.8267 |

Estimated continuous break-even additional cost:

$$
0.0867\text{ bps/side}
$$

This is the principal economic limitation of the strategy.

The predictive relationship survives spread-aware execution, but the remaining monetizable margin is small.

---

## Return Distribution

At the 100 ms reference latency, the holdout evaluation contained:

    Completed trades: 662
    Positive trades:  201 (30.36%)
    Negative trades:  454 (68.58%)
    Zero trades:        7 (1.06%)

Pooled gross-return statistics:

| Statistic | Result |
| --- | ---: |
| Mean | +0.189754 bps |
| Median | -0.001253 bps |
| Standard deviation | 0.552915 bps |
| Minimum | -3.686000 bps |
| Maximum | +4.137445 bps |

Mean winning trade:

$$
+0.717591\text{ bps}
$$

Mean losing trade:

$$
-0.041010\text{ bps}
$$

The strategy therefore does not depend on a high hit rate. Many outcomes are very small losses or near-zero changes, while fewer favorable moves are substantially larger.

---

## Tail Dependence

Gross PnL is materially right-skewed:

| Largest trades | Share of total gross PnL |
| --- | ---: |
| Top 1% | 16.4% |
| Top 5% | 51.3% |
| Top 10% | 78.4% |

Removing the largest observations still left positive pooled expectancy:

| Trades removed | Remaining mean |
| --- | ---: |
| Top 1% | +0.1603 bps |
| Top 5% | +0.0974 bps |
| Top 10% | +0.0457 bps |

After removing the best 5% of trades separately within each holdout session, all five session means remained positive.

The result is therefore tail-dependent, but not explained solely by a handful of extreme observations.

---

## Long / Short Robustness

Both trading directions contributed positively:

| Direction | Trades | Mean gross return |
| --- | ---: | ---: |
| LONG | 315 | +0.2039 bps |
| SHORT | 347 | +0.1769 bps |

All ten session-direction combinations were positive:

    5 holdout sessions × LONG
    5 holdout sessions × SHORT

The result was therefore not produced only by one directional market regime.

---

## Leave-One-Session-Out Stability

Removing each holdout session in turn produced:

| Removed session | Remaining equal-weight mean |
| --- | ---: |
| Holdout 1 | +0.1891 bps |
| Holdout 2 | +0.1629 bps |
| Holdout 3 | +0.1564 bps |
| Holdout 4 | +0.1530 bps |
| Holdout 5 | +0.2052 bps |

The minimum leave-one-session-out result was:

$$
+0.1530\text{ bps/trade}
$$

The aggregate execution result was therefore not dependent on a single holdout window.

---

## Dependence-Aware Stability

A post-hoc uncertainty diagnostic used:

    30-second time blocks
    5,000 bootstrap repetitions
    hierarchical session resampling
    random seed = 42

At zero additional cost, the hierarchical bootstrap produced:

$$
\text{mean}=+0.17335\text{ bps}
$$

with a 95% interval of:

$$
\left[+0.09147,\,+0.25315\right]
$$

At an additional cost of 0.05 bps per side:

$$
\text{mean}=+0.07335\text{ bps}
$$

with a 95% interval of:

$$
\left[-0.00853,\,+0.15315\right]
$$

At an additional cost of 0.10 bps per side:

$$
\text{mean}=-0.02665\text{ bps}
$$

with a 95% interval of:

$$
\left[-0.10853,\,+0.05315\right]
$$

The underlying spread-aware signal appears more robust than its economically tradable margin.

---

## Research Integrity

The project maintains strict separation between:

    development
    validation
    execution confirmation
    post-hoc diagnostics

The five holdout sessions were not used to choose:

- signal definition
- imbalance thresholds
- holding period
- latency grid
- execution side
- transaction-cost grid
- stop-loss rules
- take-profit rules
- directional filters

Important protocols, scripts, parameters, and result files were SHA256 fingerprinted before later research stages.

The current holdout sessions are therefore considered **consumed confirmatory data**.

Any future strategy optimization requires new independent validation data.

---

## Reproducibility Checkpoints

### Statistical protocol

    6d2ed10e1e18b04e873cebee8033191fc8710866eedd3d574e4b547aabc491da

### Execution protocol

    ef534c27856907e45ac871db8d4d499ddb338ffe114169f3ea2ee796f8265d6e

### Frozen execution parameters

    1fc3aa7cd92408161c41c067d4329d2f93953361637fbd143b03f2c0a1e2298b

### Frozen execution engine

    7a24cbe27a2f7e92e2d935ed22cb7de7f764f457a1e96f1f868fc1266ce39e23

### Holdout execution evaluator

    807170b22848fc9de12c2598a000e6fcb12d71fa90d925419c7884557f947644

### Frozen 100 ms holdout trades

    b5b76ddeddedcaac55d01ecf23e0a5ee6fa610085695604a3660fdec5e713b33

### Tail diagnostic script

    85b214512847993409040455f9cbc41b67a4899ba41c88be4df1b9ade2b60a82

### Stability diagnostic script

    39a8afb2340e77810cf5d29d1da2ccb644c0eb2c7df02b29232f805f0385aebc

The detailed methodology, numerical results, and research boundaries are documented in `RESEARCH_SUMMARY.md`.

---

## Repository Structure

    .
    ├── README.md
    ├── RESEARCH_SUMMARY.md
    ├── VALIDATION_PROTOCOL.md
    ├── EXECUTION_PROTOCOL.md
    ├── requirements.txt
    │
    ├── src/
    │   └── data/
    │       ├── live_bookticker.py
    │       ├── collect_live_session.py
    │       ├── validate_bookticker.py
    │       ├── analyze_live_session.py
    │       ├── build_session_features.py
    │       ├── analyze_signal_buckets.py
    │       ├── analyze_cross_sessions.py
    │       ├── statistical_validation.py
    │       ├── holdout_validation.py
    │       ├── calibrate_execution_thresholds.py
    │       ├── simulate_execution_development.py
    │       ├── evaluate_execution_development.py
    │       ├── evaluate_execution_holdout.py
    │       ├── analyze_execution_tail_risk.py
    │       └── analyze_execution_stability.py
    │
    └── data/
        ├── raw/
        └── processed/

Raw WebSocket captures and large generated trade-level outputs are intentionally excluded from the public repository.

Compact validation tables and frozen research outputs are retained where useful for inspection and reproducibility.

---

## Technical Stack

- Python
- pandas
- NumPy
- SciPy
- statsmodels
- asyncio
- WebSockets
- Binance live market data
- local receipt-time processing
- HAC inference
- moving/block bootstrap
- hierarchical bootstrap
- SHA256 reproducibility checkpoints

---

## What This Project Demonstrates

The main contribution is the research process rather than the absolute simulated return.

The repository demonstrates:

- asynchronous live market-data acquisition
- Level-1 market-microstructure feature engineering
- trade-flow reconstruction
- careful timestamp semantics
- look-ahead prevention
- exploratory-versus-confirmatory separation
- pre-registration
- unseen holdout testing
- HAC inference
- dependence-aware resampling
- bid/ask-aware execution
- execution-latency modeling
- transaction-cost sensitivity
- return-distribution diagnostics
- long/short decomposition
- failure-boundary identification
- reproducible research checkpoints

---

## Limitations

This project is **not a production trading system**.

The confirmatory sample consists of only five approximately ten-minute holdout windows.

The study therefore does not establish robustness across:

- months or years
- different volatility regimes
- weekends versus weekdays
- major macroeconomic announcements
- liquidation events
- structural exchange changes
- different cryptocurrency instruments
- different trading venues

The execution model also excludes several elements of real production trading:

- actual order submission
- exchange acknowledgements
- measured network round-trip latency
- venue-specific real fee schedules
- partial fills
- market impact
- queue position
- rejected orders
- infrastructure outages
- capital constraints
- portfolio-level risk

Aggressive bid/ask execution removes the need to assume passive queue position, but it does not eliminate implementation uncertainty.

The correct interpretation is therefore:

> **validated microstructure research with execution-aware evidence, not verified deployable alpha.**

---

## Phase II

The frozen confirmatory strategy will not be tuned using the existing holdout sessions.

Future work should be treated as separate extensions.

### Prospective Forward Monitoring

Run the frozen strategy over substantially more independent market windows without recalibrating the signal.

The objective is to study stability across:

- time of day
- weekdays
- volatility regimes
- trending markets
- range-bound markets
- high-activity events
- quieter liquidity conditions

### Live Paper Execution

Operate the same causal execution logic prospectively while recording:

- signal timestamp
- decision timestamp
- target-entry timestamp
- actual observable entry quote
- target-exit timestamp
- actual observable exit quote
- quote waiting time
- modeled PnL
- skipped or incomplete executions

### Inventory and Risk

Introduce bounded inventory and explicit exposure controls, for example:

$$
position \in \{-1,0,+1\}
$$

This should be treated as a new engineering/research extension rather than retroactively modifying the completed holdout result.

### Regime Research

With newly collected development data, investigate whether signal performance varies with observable market state such as:

- spread
- short-horizon volatility
- trade intensity
- order-book update intensity
- liquidity imbalance
- short-term momentum

Any new conditional strategy requires a fresh development/validation cycle.

---

## Research Status

    Statistical signal validation       PASS
    Unseen statistical holdout          PASS
    Causal execution validation         PASS
    Unseen execution holdout            PASS
    Latency robustness                  POSITIVE, DECAYING
    Tail robustness                     POSITIVE, RIGHT-SKEWED
    Cost robustness                     LIMITED
    Production profitability            NOT ESTABLISHED
    Long-horizon regime robustness      NOT ESTABLISHED
    Real-money execution                NOT TESTED

---

## Full Research Record

For the complete methodology, frozen protocols, statistical results, execution analysis, diagnostic results, limitations, and reproducibility record, see:

**`RESEARCH_SUMMARY.md`**
