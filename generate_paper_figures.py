#!/usr/bin/env python3
"""Generate graphs for the Lattice EDM research paper from the 16-run dataset."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "paper_figures"
OUT.mkdir(exist_ok=True)

runs = pd.read_csv(ROOT / "data" / "original_16_runs.csv")
labels = pd.read_csv(ROOT / "data" / "run_visual_labels.csv")
df = runs.merge(labels, on="Run")
df["Energy"] = df["Peak_Current_A"] * df["Pulse_On_Time_us"] * (df["Duty_Factor_pct"] / 100.0)
df["Success"] = (df["Boundary_circularity_1to5"] >= 5) & (df["Supporting_boundary_intact"] == 1)

# Style
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "figure.facecolor": "white",
        "axes.facecolor": "#fafafa",
        "axes.grid": True,
        "grid.alpha": 0.25,
    }
)


def save(fig, name):
    path = OUT / name
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("Wrote", path)


# 1) Circularity by run (bar)
fig, ax = plt.subplots(figsize=(8.2, 3.6))
colors = ["#1b7a3d" if s else "#b33a3a" for s in df["Success"]]
ax.bar(df["Run"].astype(str), df["Boundary_circularity_1to5"], color=colors, edgecolor="#222", linewidth=0.4)
ax.axhline(3.5, color="#555", linestyle="--", linewidth=1, label="PASS threshold (3.5)")
ax.set_xlabel("Experiment Run")
ax.set_ylabel("SEM Boundary Circularity (1–5)")
ax.set_title("SEM Circularity Scores Across 16 EDM Experiments")
ax.set_ylim(0, 5.5)
ax.legend(loc="upper right", fontsize=8)
save(fig, "fig_circularity_by_run.png")

# 2) Hole deviation vs circularity (scatter) — the paradox
fig, ax = plt.subplots(figsize=(7.5, 4.2))
sc = ax.scatter(
    df["Hole_Dev_Top_um"],
    df["Boundary_circularity_1to5"],
    c=df["Peak_Current_A"],
    cmap="viridis",
    s=80 + 4 * df["Pulse_On_Time_us"] / 10,
    edgecolors="black",
    linewidths=0.5,
    zorder=3,
)
for _, r in df.iterrows():
    ax.annotate(
        f"R{int(r.Run)}",
        (r.Hole_Dev_Top_um, r.Boundary_circularity_1to5),
        textcoords="offset points",
        xytext=(4, 4),
        fontsize=7,
    )
cbar = fig.colorbar(sc, ax=ax)
cbar.set_label("Peak Current (A)")
ax.set_xlabel("Hole Deviation Top (µm)")
ax.set_ylabel("SEM Circularity (1–5)")
ax.set_title("Paradox: Lower Hole Deviation ≠ Better Circularity")
# Highlight Run 4 and Run 5
r4 = df[df.Run == 4].iloc[0]
r5 = df[df.Run == 5].iloc[0]
ax.annotate(
    "Run 4 SUCCESS\n(circular ring)",
    xy=(r4.Hole_Dev_Top_um, r4.Boundary_circularity_1to5),
    xytext=(230, 4.2),
    fontsize=8,
    arrowprops=dict(arrowstyle="->", color="#1b7a3d"),
    color="#1b7a3d",
)
ax.annotate(
    "Run 5 FAIL\n(best deviation, bad SEM)",
    xy=(r5.Hole_Dev_Top_um, r5.Boundary_circularity_1to5),
    xytext=(210, 3.0),
    fontsize=8,
    arrowprops=dict(arrowstyle="->", color="#b33a3a"),
    color="#b33a3a",
)
save(fig, "fig_deviation_vs_circularity.png")

# 3) Energy vs circularity
fig, ax = plt.subplots(figsize=(7.5, 3.8))
ax.scatter(
    df["Energy"],
    df["Boundary_circularity_1to5"],
    c=["#1b7a3d" if s else "#888888" for s in df["Success"]],
    s=70,
    edgecolors="black",
    linewidths=0.5,
)
for _, r in df.iterrows():
    ax.annotate(f"R{int(r.Run)}", (r.Energy, r.Boundary_circularity_1to5), textcoords="offset points", xytext=(3, 3), fontsize=7)
ax.set_xlabel("Discharge Energy E = I × T × (D/100)")
ax.set_ylabel("SEM Circularity (1–5)")
ax.set_title("Discharge Energy vs Supporting-Boundary Circularity")
save(fig, "fig_energy_vs_circularity.png")

# 4) Parameter heatmap-like pivot: mean circularity by I and T
pivot = df.pivot_table(index="Peak_Current_A", columns="Pulse_On_Time_us", values="Boundary_circularity_1to5", aggfunc="mean")
fig, ax = plt.subplots(figsize=(7.2, 3.8))
im = ax.imshow(pivot.values, cmap="RdYlGn", vmin=1, vmax=5, aspect="auto")
ax.set_xticks(range(len(pivot.columns)))
ax.set_xticklabels([str(int(c)) for c in pivot.columns])
ax.set_yticks(range(len(pivot.index)))
ax.set_yticklabels([str(int(i)) for i in pivot.index])
ax.set_xlabel("Pulse-on Time (µs)")
ax.set_ylabel("Peak Current (A)")
ax.set_title("Mean SEM Circularity by Current × Pulse-on")
for i in range(pivot.shape[0]):
    for j in range(pivot.shape[1]):
        val = pivot.values[i, j]
        if not np.isnan(val):
            ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=8, color="black")
fig.colorbar(im, ax=ax, label="Circularity")
save(fig, "fig_current_pulse_heatmap.png")

# 5) Final recommendations comparison chart
recs = [
    ("Phase1\n+SEM\n(Final)", 4, 150, 80),
    ("Phase1\n−SEM\n(Wrong)", 6, 50, 64),
    ("P2 Center", 4, 150, 80),
    ("P2 Mid", 4, 148, 79),
    ("P2 Strut", 3.5, 150, 78),
    ("P2 Node", 3.5, 145, 76),
]
names = [r[0] for r in recs]
I = [r[1] for r in recs]
T = [r[2] for r in recs]
D = [r[3] for r in recs]
x = np.arange(len(names))
w = 0.25
fig, ax = plt.subplots(figsize=(8.2, 3.8))
ax.bar(x - w, I, w, label="Peak Current (A)", color="#2c6eaf")
ax.bar(x, np.array(T) / 50.0, w, label="Pulse-on ÷ 50 (scaled)", color="#d4a017")
ax.bar(x + w, np.array(D) / 20.0, w, label="Duty ÷ 20 (scaled)", color="#2e8b57")
ax.set_xticks(x)
ax.set_xticklabels(names, fontsize=8)
ax.set_ylabel("Scaled parameter value")
ax.set_title("Final Recommended EDM Parameters (Phase 1 & Phase 2)")
ax.legend(fontsize=8, loc="upper right")
save(fig, "fig_final_recommendations.png")

# 6) Pass/Fail summary pie
fig, ax = plt.subplots(figsize=(5.2, 4.0))
pass_n = int(df["Success"].sum())
fail_n = int((~df["Success"]).sum())
ax.pie(
    [pass_n, fail_n],
    labels=[f"PASS (Run 4)\nn={pass_n}", f"FAIL\nn={fail_n}"],
    colors=["#1b7a3d", "#b33a3a"],
    autopct="%1.0f%%",
    startangle=90,
    explode=(0.06, 0),
    textprops={"fontsize": 10},
)
ax.set_title("SEM Supporting-Boundary Outcome (16 Runs)")
save(fig, "fig_pass_fail_pie.png")

print("All paper figures generated in", OUT)
