from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

INPUT_CSV = (
    ROOT
    / "data"
    / "processed"
    / "execution_cost_sensitivity_holdout.csv"
)

OUTPUT_DIR = ROOT / "figures"
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_PNG = OUTPUT_DIR / "transaction_cost_frontier_holdout.png"
OUTPUT_SVG = OUTPUT_DIR / "transaction_cost_frontier_holdout.svg"


# ------------------------------------------------------------
# Load frozen holdout results
# ------------------------------------------------------------

df = pd.read_csv(INPUT_CSV)

TARGET_LATENCY_MS = 100.0

plot_df = df.loc[
    df["latency_ms"] == TARGET_LATENCY_MS
].copy()

if plot_df.empty:
    raise RuntimeError(
        f"No rows found for latency_ms == {TARGET_LATENCY_MS}"
    )

plot_df = (
    plot_df
    .sort_values("additional_cost_per_side_bps")
    .reset_index(drop=True)
)


# ------------------------------------------------------------
# Focused economic region
# ------------------------------------------------------------

# The full frozen grid extends to 5 bps/side.
# For the README figure we focus on the economically relevant
# region around the observed break-even boundary.
focus_df = plot_df.loc[
    plot_df["additional_cost_per_side_bps"] <= 0.50
].copy()

x = focus_df["additional_cost_per_side_bps"]
y = focus_df["equal_weight_mean_net_return_bps"]


# ------------------------------------------------------------
# Break-even interpolation
# ------------------------------------------------------------

break_even_cost = None

for i in range(len(plot_df) - 1):
    x1 = float(
        plot_df.loc[i, "additional_cost_per_side_bps"]
    )
    x2 = float(
        plot_df.loc[i + 1, "additional_cost_per_side_bps"]
    )

    y1 = float(
        plot_df.loc[i, "equal_weight_mean_net_return_bps"]
    )
    y2 = float(
        plot_df.loc[i + 1, "equal_weight_mean_net_return_bps"]
    )

    if y1 == 0:
        break_even_cost = x1
        break

    if y1 > 0 and y2 < 0:
        break_even_cost = (
            x1
            + (0 - y1)
            * (x2 - x1)
            / (y2 - y1)
        )
        break

    if y2 == 0:
        break_even_cost = x2
        break


if break_even_cost is None:
    raise RuntimeError(
        "Could not identify a break-even crossing."
    )


# ------------------------------------------------------------
# Plot
# ------------------------------------------------------------

fig, ax = plt.subplots(figsize=(8.5, 5.2))

ax.plot(
    x,
    y,
    marker="o",
    linewidth=2,
    markersize=7,
)

# Zero-return boundary.
ax.axhline(
    0,
    linestyle="--",
    linewidth=1,
    alpha=0.7,
)

# Break-even boundary.
ax.axvline(
    break_even_cost,
    linestyle="--",
    linewidth=1,
    alpha=0.8,
)


# ------------------------------------------------------------
# Point labels
# ------------------------------------------------------------

offsets = {
    0.00: (0, 10),
    0.05: (-15, 10),
    0.10: (15, -18),
    0.25: (0, -18),
    0.50: (0, -18),
}

for cost, mean_return in zip(x, y):
    cost_float = float(cost)
    dx, dy = offsets.get(cost_float, (0, 10))

    ax.annotate(
        f"{mean_return:+.4f}",
        xy=(cost, mean_return),
        xytext=(dx, dy),
        textcoords="offset points",
        ha="center",
        va="bottom" if dy >= 0 else "top",
        fontsize=9,
    )


# ------------------------------------------------------------
# Break-even annotation
# ------------------------------------------------------------

ax.annotate(
    f"Break-even ≈ {break_even_cost:.4f} bps/side",
    xy=(break_even_cost, 0),
    xytext=(35, 30),
    textcoords="offset points",
    arrowprops={
        "arrowstyle": "->",
        "linewidth": 1,
    },
    fontsize=9,
)


# ------------------------------------------------------------
# Labels and presentation
# ------------------------------------------------------------

ax.set_title(
    "Holdout Execution: Transaction-Cost Frontier",
    fontsize=14,
    pad=14,
)

ax.set_xlabel(
    "Additional transaction cost per side (bps)"
)

ax.set_ylabel(
    "Equal-weight mean net return (bps/trade)"
)

ax.set_xticks(
    focus_df["additional_cost_per_side_bps"]
)

ax.set_xlim(
    -0.015,
    0.52,
)

ax.set_ylim(
    y.min() - 0.10,
    y.max() + 0.10,
)

ax.grid(
    True,
    alpha=0.25,
)

fig.text(
    0.5,
    0.015,
    "At 100 ms latency, mean net return turns negative between "
    "0.05 and 0.10 bps additional cost per side.",
    ha="center",
    fontsize=9,
)

fig.tight_layout(
    rect=[0, 0.05, 1, 1]
)


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

fig.savefig(
    OUTPUT_PNG,
    dpi=180,
    bbox_inches="tight",
)

fig.savefig(
    OUTPUT_SVG,
    bbox_inches="tight",
)

plt.close(fig)


# ------------------------------------------------------------
# Report
# ------------------------------------------------------------

zero_cost_value = float(
    plot_df.loc[
        plot_df["additional_cost_per_side_bps"] == 0.0,
        "equal_weight_mean_net_return_bps",
    ].iloc[0]
)

print("Transaction-cost frontier figure created.")
print(f"Reference latency: {TARGET_LATENCY_MS:.0f} ms")
print(
    f"Zero-cost mean net return: "
    f"{zero_cost_value:+.6f} bps/trade"
)
print(
    f"Estimated break-even additional cost: "
    f"{break_even_cost:.6f} bps/side"
)
print(f"PNG: {OUTPUT_PNG}")
print(f"SVG: {OUTPUT_SVG}")