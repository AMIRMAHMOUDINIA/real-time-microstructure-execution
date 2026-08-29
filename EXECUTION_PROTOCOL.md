# EXECUTION VALIDATION PROTOCOL

## BTCUSDT Real-Time Microstructure and Execution Project

Status: PRE-EXECUTION SPECIFICATION

This document defines the execution methodology that will be used to test whether
the previously validated short-horizon Level-1 book-imbalance relationship can
survive realistic trading mechanics.

The predictive signal research has already been completed and frozen.

The execution analysis must not modify the validated predictive signal,
prediction horizon, holdout sample, or statistical results in response to
execution performance.


# 1. RESEARCH QUESTION

The statistical stage established the following question:

> Does median Level-1 order-book imbalance contain information about subsequent
> BTCUSDT mid-price movement?

The execution stage asks a different and more demanding question:

> Can the pre-specified book-imbalance signal be converted into positive trading
> returns after observable bid-ask execution, latency, and additional trading
> costs?

The distinction is fundamental:

Predictive relationship != executable alpha.


# 2. FROZEN PREDICTIVE SIGNAL

Primary signal:

    median_book_imbalance

The definition of the signal must not be changed.

For each one-second bucket:

    imbalance =
        (bid_quantity - ask_quantity)
        /
        (bid_quantity + ask_quantity)

The one-second feature used for execution is:

    median_book_imbalance

No alternative imbalance formula will be introduced during the confirmatory
execution test.


# 3. PRIMARY PREDICTION HORIZON

Primary horizon:

    +1 second

The +5 second horizon remains a secondary statistical diagnostic and is not the
primary execution strategy.

The execution study will therefore use a nominal holding period of:

    1 second


# 4. DEVELOPMENT AND HOLDOUT SEPARATION

Execution research will preserve the existing development / holdout separation.

Development sessions:

    20260824_135129
    20260825_084855
    20260826_085550
    20260826_144545
    20260826_151328

Pre-registered holdout sessions:

    20260826_202754
    20260827_083158
    20260827_195947
    20260828_153334
    20260829_091754

The development sessions may be used only for:

- deterministic calibration of the execution thresholds;
- debugging implementation;
- checking timing logic;
- verifying that calculations are mechanically correct;
- development-stage execution diagnostics.

The five holdout sessions must not be used to:

- choose thresholds;
- choose latency;
- choose holding period;
- choose direction;
- choose cost assumptions;
- choose whether to trade;
- redesign the signal;
- optimize execution parameters.

Once the implementation has been verified on the development sample, the
holdout execution evaluation will be run once under this frozen protocol.


# 5. SIGNAL THRESHOLD CALIBRATION

The validated statistical analysis used five signal quantiles.

To translate this structure into an executable decision rule, the primary
execution strategy will trade only extreme signal states.

The lower and upper execution thresholds will be calculated using ONLY the
development sessions.

All valid development observations of:

    median_book_imbalance

will be pooled after removing missing values.

The thresholds will then be defined deterministically as:

    lower_threshold = 20th percentile
    upper_threshold = 80th percentile

No search over alternative percentiles is allowed for the confirmatory
execution result.

Once calculated, the two numerical thresholds will be saved to a parameter file
and fingerprinted before holdout execution is evaluated.


# 6. PRIMARY TRADING RULE

At each completed one-second feature bucket:

If:

    median_book_imbalance >= upper_threshold

then:

    desired direction = LONG

If:

    median_book_imbalance <= lower_threshold

then:

    desired direction = SHORT

Otherwise:

    desired direction = FLAT / NO TRADE

No additional indicator will be used to override the primary decision.


# 7. FEATURE TIMING AND LOOK-AHEAD CONTROL

The feature timestamp represents the start of its one-second aggregation bucket.

Therefore, a feature associated with timestamp:

    t

contains information collected over approximately:

    [t, t + 1 second)

and cannot be considered known at timestamp t.

The earliest valid decision time is therefore:

    decision_time = feature_timestamp + 1 second

This rule prevents the execution simulator from trading on information that had
not yet been observed.

No trade may be executed before its decision time.


# 8. CLOCK DEFINITION

Execution timing will use:

    received_at_utc

from the locally recorded Binance market-data stream.

This timestamp represents local receipt of the market update.

Consequently, modeled execution latency represents ADDITIONAL delay after local
receipt.

The simulator does NOT measure or claim to know:

- exchange matching-engine latency;
- exchange-to-client network latency;
- order-gateway latency;
- exchange acknowledgement latency.

Any interpretation must explicitly retain this limitation.


# 9. RAW QUOTE EXECUTION

Execution prices will be obtained from the raw BTCUSDT Level-1 bookTicker stream.

For any target execution timestamp, the simulator will select:

    the first observed valid book quote at or after the target timestamp.

It must never use a quote observed before the target execution time.

This rule applies to both entry and exit.


# 10. PRIMARY LATENCY ASSUMPTION

Reference modeled execution latency:

    100 milliseconds

Therefore:

    target_entry_time =
        decision_time + 100 milliseconds

The actual simulated entry timestamp is:

    first recorded book quote
    at or after target_entry_time


# 11. LATENCY SENSITIVITY GRID

The following latency values are pre-specified:

    0 ms
    50 ms
    100 ms
    250 ms
    500 ms
    1000 ms

The 100 ms result is the reference execution result.

The other values are sensitivity analyses.

No additional latency value will be introduced because it produces a more
favourable result.


# 12. AGGRESSIVE / TAKER EXECUTION

The primary execution model uses aggressive execution.

For a LONG entry:

    entry_price = observed ask price

For a SHORT entry:

    entry_price = observed bid price

This directly incorporates the observable cost of crossing the spread.


# 13. EXIT RULE

Nominal holding period:

    1 second

For every entry:

    target_exit_time =
        actual_entry_time + 1 second

The actual exit quote is:

    first recorded valid book quote
    at or after target_exit_time


# 14. EXIT PRICE

For a LONG position:

    exit_price = observed bid price

For a SHORT position:

    exit_price = observed ask price

Therefore, the primary execution test crosses the spread at both entry and exit.

This is deliberately conservative relative to assuming mid-price execution.


# 15. LONG RETURN

Before additional fees and slippage:

    gross_return_bps =
        ((exit_bid / entry_ask) - 1)
        * 10,000


# 16. SHORT RETURN

Before additional fees and slippage:

    gross_return_bps =
        ((entry_bid / exit_ask) - 1)
        * 10,000


# 17. POSITION SIZE

The execution study uses normalized unit exposure.

Performance will primarily be reported in:

    basis points

rather than currency P&L.

This avoids introducing arbitrary capital or leverage assumptions.

No leverage will be modeled during the primary execution validation.


# 18. POSITION OVERLAP

Only one position may be open at a time.

While a position is open:

- subsequent entry signals are ignored;
- no pyramiding is allowed;
- no averaging into a position is allowed;
- no simultaneous long and short exposure is allowed.

After the position exits, the strategy becomes eligible to act on the next
completed signal observation.


# 19. POSITION REVERSALS

An opposing signal occurring while an existing position is open does NOT
immediately reverse the position.

The current trade follows its frozen one-second holding period.

The opposite signal may only generate a new trade after the previous position
has exited.


# 20. INCOMPLETE TRADES

If the raw data do not contain a valid entry quote after the required entry
timestamp, no trade is recorded.

If an entry occurs but no valid exit quote exists before the session data end,
that trade is classified as incomplete and excluded from return statistics.

The number of skipped and incomplete trades must be reported.


# 21. BID-ASK SPREAD

Observed bid and ask prices are included directly in execution.

Therefore:

    spread cost

must NOT subsequently be subtracted a second time.

Gross execution return means:

    return after observable bid/ask crossing
    but before additional fees and modeled slippage.


# 22. ADDITIONAL COST MODEL

Because actual trading fees depend on exchange, account tier, volume, rebates,
and other conditions, the project will not select a favourable single fee
assumption.

Instead, the strategy will report a predefined additional per-side cost
sensitivity grid.

Additional cost per side:

    0.00 bps
    0.05 bps
    0.10 bps
    0.25 bps
    0.50 bps
    1.00 bps
    2.00 bps
    5.00 bps

The cost represents any combination of:

- fees;
- additional slippage;
- unmodeled execution friction.

For a completed round trip:

    total_additional_cost =
        2 * per_side_cost


# 23. NET RETURN

For every trade:

    net_return_bps =
        gross_return_bps
        - 2 * additional_cost_per_side_bps


# 24. BREAK-EVEN COST

The project will calculate the maximum additional cost the strategy could
support before its average return becomes zero.

For mean gross round-trip return:

    break_even_cost_per_side =
        mean_gross_return_bps / 2

This is one of the primary economic outputs.

It provides a more transparent measure than selecting one convenient exchange
fee assumption.


# 25. PRIMARY EXECUTION ENDPOINT

The primary execution endpoint is:

    equal-weighted mean session-level gross return per trade

under:

    extreme-quintile signal rule
    1-second holding period
    100 ms modeled additional latency
    aggressive bid/ask execution
    no additional cost beyond observed spread

This is the reference execution result.


# 26. SECONDARY ECONOMIC ENDPOINTS

Secondary endpoints include:

- median return per trade;
- total number of trades;
- positive-trade rate;
- session-level mean return;
- cumulative normalized return;
- turnover;
- maximum drawdown;
- latency sensitivity;
- additional-cost sensitivity;
- break-even cost per side;
- long versus short performance;
- performance by activity level;
- performance by holdout session.


# 27. SESSION WEIGHTING

The five holdout sessions will be treated as separate market windows.

Primary cross-session summaries will use:

    equal weighting by session

rather than allowing a high-activity session with many trades to dominate the
result.

Pooled trade-level results may also be shown as descriptive secondary results.


# 28. DIRECTIONAL CONSISTENCY

For each holdout session, the following will be reported:

    mean gross return per trade

The number of sessions with:

    mean gross return > 0

will be reported explicitly.

No claim of broad robustness will be made solely from a pooled result if the
effect is concentrated in one or two sessions.


# 29. ACTIVITY ANALYSIS

The previously frozen statistical activity condition:

    trades >= 25 per second

may be analyzed as a secondary diagnostic.

It will NOT replace the unrestricted primary execution test.

This is particularly important because holdout_5 contains relatively few
high-activity observations.


# 30. LATENCY DECAY

For each pre-specified latency:

    0
    50
    100
    250
    500
    1000 ms

the simulator will recompute:

- trade count;
- mean gross return;
- median gross return;
- positive-trade rate;
- cumulative return;
- equal-weighted session mean.

The purpose is to estimate how rapidly economic value decays after signal
observation.

No latency will be selected retrospectively as "the strategy latency" merely
because it performs best.


# 31. COST FRONTIER

For every latency assumption, results will be evaluated across the frozen
additional-cost grid:

    0.00
    0.05
    0.10
    0.25
    0.50
    1.00
    2.00
    5.00 bps per side

This produces an economic viability frontier:

    signal
        x latency
        x trading cost


# 32. NO STOP-LOSS OR TAKE-PROFIT

The confirmatory execution strategy will not use:

- stop-losses;
- take-profit levels;
- trailing stops;
- volatility-adjusted exits.

These would create additional tunable strategy parameters.

The exit remains fixed at one second.


# 33. NO SIGNAL OPTIMIZATION

The execution stage will not test alternative primary signals such as:

- mean book imbalance;
- trade-flow imbalance;
- notional-flow imbalance;
- weighted combinations;
- spread-adjusted imbalance;
- nonlinear transformations;
- machine-learning predictions.

Such models may be studied later as new research projects, but they are not part
of the confirmatory execution test.


# 34. NO HOLDOUT THRESHOLD OPTIMIZATION

The holdout data must not be used to search over:

- imbalance thresholds;
- quantile cutoffs;
- minimum trade activity;
- holding periods;
- latency values;
- transaction-cost assumptions.

Sensitivity grids may be reported only where explicitly defined in this
protocol.


# 35. PASSIVE EXECUTION

Passive maker execution is NOT part of the primary confirmatory test.

The present dataset contains Level-1 quotes and trades but does not contain
sufficient information to reconstruct reliably:

- queue position;
- our own limit-order timestamp;
- queue-ahead volume;
- cancellation priority;
- actual order acknowledgements;
- individual fill probability.

A later passive-execution model may therefore be implemented only as a clearly
labeled scenario analysis.

It must not be presented as reconstructed historical fills.


# 36. INVENTORY MANAGEMENT

Inventory optimization is NOT part of the first confirmatory execution test.

Because the primary strategy allows only one normalized unit position at a time,
inventory is bounded to:

    -1
     0
    +1

A later project phase may introduce:

- persistent inventory;
- inventory penalties;
- position limits;
- inventory-aware quoting;
- market-making logic.

Those extensions will be analyzed only after the basic economic viability of
the signal is established.


# 37. EXECUTION SUCCESS LEVELS

The project will distinguish four levels of evidence.

LEVEL 1 — STATISTICAL PREDICTABILITY

Already established by the frozen statistical holdout analysis.

LEVEL 2 — SPREAD-AWARE ECONOMIC SURVIVAL

Satisfied only if the reference aggressive execution strategy produces a
positive equal-weighted holdout return after observed bid/ask crossing.

LEVEL 3 — COST ROBUSTNESS

Evaluated by determining the positive additional-cost range and break-even
per-side cost.

LEVEL 4 — PRACTICAL TRADING VIABILITY

Requires additional evidence concerning:

- real fees;
- measured latency;
- slippage;
- market impact;
- fill mechanics;
- larger samples;
- longer market regimes;
- operational reliability.

Passing Levels 1-3 does NOT automatically establish Level 4.


# 38. FAILURE IS A VALID RESULT

If the signal is statistically predictive but fails after bid/ask execution,
the correct conclusion is:

> The microstructure variable contains short-horizon predictive information,
> but the magnitude is insufficient to overcome aggressive execution costs
> under the tested assumptions.

This result must not trigger retrospective changes to the frozen strategy.

Likewise, if the signal survives spread but fails under small additional costs,
that limitation will be reported directly.


# 39. HOLDOUT INTERPRETATION

The five holdout sessions provide genuine unseen validation relative to the
earlier predictive research.

However, five ten-minute windows do not represent all possible:

- market regimes;
- volatility environments;
- liquidity states;
- days;
- exchange conditions.

The project must therefore use terms such as:

    pre-registered holdout replication

and must avoid exaggerated claims such as:

    universally robust
    proven alpha
    production-ready strategy


# 40. IMPLEMENTATION REPRODUCIBILITY

The execution simulator must output deterministic CSV results.

At minimum it will save:

    execution_parameters.csv
    execution_trades_development.csv
    execution_summary_development.csv
    execution_trades_holdout.csv
    execution_summary_holdout.csv
    execution_latency_sensitivity.csv
    execution_cost_sensitivity.csv

The exact file names may differ only for technical reasons and must be
documented.


# 41. DEVELOPMENT WORKFLOW

The permitted workflow is:

1. Freeze this protocol.
2. Calculate development-only 20th / 80th percentile thresholds.
3. Save and fingerprint the thresholds.
4. Build the simulator.
5. Debug simulator using development sessions only.
6. Verify timestamp causality manually on sample trades.
7. Freeze simulator implementation.
8. Run the five holdout sessions once.
9. Report all pre-specified results.
10. Do not redesign the strategy based on holdout performance.


# 42. PRIMARY HYPOTHESIS OF THE EXECUTION STAGE

The primary economic hypothesis is:

> Extreme values of the previously validated median Level-1 book-imbalance
> signal retain positive economic value after causal 100 ms delayed aggressive
> bid/ask execution and a one-second holding period.

The reference test includes observable spread crossing but no additional
assumed fee or slippage.

Additional economic viability is evaluated using the frozen cost frontier.


# 43. RESEARCH GUARDRAIL

The purpose of this phase is not to manufacture a profitable backtest.

The purpose is to determine whether the previously validated predictive
relationship survives the transition:

    statistical signal
        ->
    causal decision
        ->
    delayed execution
        ->
    bid/ask prices
        ->
    transaction costs
        ->
    realized trading return

The final conclusion will follow the evidence even if execution eliminates the
entire apparent predictive edge.