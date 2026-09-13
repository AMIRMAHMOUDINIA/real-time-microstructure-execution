from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

INPUT_CSV = (
    REPO_ROOT
    / "data"
    / "processed"
    / "execution_latency_sensitivity_holdout.csv"
)

OUTPUT_DIR = REPO_ROOT / "figures"
OUTPUT_PNG = OUTPUT_DIR / "latency_sensitivity_holdout.png"
OUTPUT_SVG = OUTPUT_DIR / "latency_sensitivity_holdout.svg"


# ------------------------------------------------------------
# Load frozen holdout results
# ------------------------------------------------------------

df = pd.read_csv(INPUT_CSV)

required_columns = {
    "latency_ms",
    "equal_weight_mean_session_return_bps",
}

missing = required_columns.difference(df.columns)

if missing:
    raise ValueError(
        f"Missing required columns in {INPUT_CSV.name}: "
        f"{sorted(missing)}"
    )

df = df.sort_values("latency_ms").reset_index(drop=True)

x = df["latency_ms"]
y = df["equal_weight_mean_session_return_bps"]


# ------------------------------------------------------------
# Verify primary 100 ms specification
# ------------------------------------------------------------

primary = df.loc[df["latency_ms"] == 100.0]

if len(primary) != 1:
    raise ValueError(
        "Expected exactly one 100 ms row in the latency-sensitivity file."
    )

primary_x = float(primary["latency_ms"].iloc[0])
primary_y = float(
    primary["equal_weight_mean_session_return_bps"].iloc[0]
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
    markersize=6,
)

# Highlight frozen primary specification.
ax.scatter(
    [primary_x],
    [primary_y],
    s=110,
    marker="D",
    zorder=4,
)

# Zero-return reference.
ax.axhline(
    0,
    linestyle="--",
    linewidth=1,
    alpha=0.6,
)

# Point labels.
# Custom offsets prevent the first three labels from overlapping.
offsets = {
    0.0: (0, 10),
    50.0: (0, -18),
    100.0: (20, 12),
    250.0: (0, 10),
    500.0: (0, 10),
    1000.0: (0, 10),
}

for latency, mean_return in zip(x, y):
    dx, dy = offsets.get(float(latency), (0, 10))

    label = f"{mean_return:+.4f}"

    if float(latency) == 100.0:
        label = f"Primary 100 ms\n{mean_return:+.4f}"

    ax.annotate(
        label,
        xy=(latency, mean_return),
        xytext=(dx, dy),
        textcoords="offset points",
        ha="center",
        va="bottom" if dy >= 0 else "top",
        fontsize=9,
    )

ax.set_title(
    "Holdout Execution: Latency Sensitivity",
    fontsize=14,
    pad=14,
)

ax.set_xlabel("Modeled additional latency (ms)")
ax.set_ylabel("Equal-weight gross return (bps/trade)")

ax.set_xticks(x)

ax.set_ylim(
    bottom=0,
    top=y.max() + 0.035,
)

ax.grid(
    True,
    alpha=0.25,
)

# Keep the robustness statement outside the plotting area.
fig.text(
    0.5,
    0.015,
    "All 5 holdout sessions remained positive at every tested latency.",
    ha="center",
    fontsize=9,
)

fig.tight_layout(rect=[0, 0.05, 1, 1])


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

print("Latency-sensitivity figure created.")
print(f"Primary 100 ms result: {primary_y:+.6f} bps/trade")
print(f"PNG: {OUTPUT_PNG}")
print(f"SVG: {OUTPUT_SVG}")