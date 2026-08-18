#!/usr/bin/env python3
"""Generate graphs for the research paper (inspired by EDM report chart types only)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "paper_figures"
OUT.mkdir(exist_ok=True)

runs = pd.read_csv(ROOT / "data" / "original_16_runs.csv")
labels = pd.read_csv(ROOT / "data" / "run_visual_labels.csv")
df = runs.merge(labels, on="Run")
df["Energy"] = df["Peak_Current_A"] * df["Pulse_On_Time_us"] * (df["Duty_Factor_pct"] / 100.0)
df["Mean_Dev"] = (df["Hole_Dev_Top_um"] + df["Hole_Dev_Bottom_um"]) / 2.0
df["Asymmetry"] = (df["Hole_Dev_Top_um"] - df["Hole_Dev_Bottom_um"]).abs()
df["Dev_Score"] = df["Mean_Dev"] + 0.5 * df["Asymmetry"]
df["Success"] = (df["Boundary_circularity_1to5"] >= 5) & (df["Supporting_boundary_intact"] == 1)
df["Circ_ratio"] = df["Boundary_circularity_1to5"] / 5.0

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "axes.titlesize": 11,
        "axes.labelsize": 9.5,
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


# C1-style: SEM circularity by run
fig, ax = plt.subplots(figsize=(8.2, 3.5))
colors = ["#1b7a3d" if s else "#4a90c2" for s in df["Success"]]
ax.bar(df["Run"].astype(str), df["Boundary_circularity_1to5"], color=colors, edgecolor="#222", lw=0.4)
ax.axhline(3.5, color="#555", ls="--", lw=1, label="PASS threshold (3.5)")
ax.set_xlabel("Experiment Run")
ax.set_ylabel("SEM Boundary Circularity (1–5)")
ax.set_title("SEM Circularity Scores Across 16 EDM Experiments")
ax.set_ylim(0, 5.5)
ax.legend(fontsize=8)
save(fig, "fig_circularity_by_run.png")

# Pass/fail pie
fig, ax = plt.subplots(figsize=(5.0, 3.8))
ax.pie(
    [int(df.Success.sum()), int((~df.Success).sum())],
    labels=[f"PASS (Run 4)\nn=1", f"FAIL\nn=15"],
    colors=["#1b7a3d", "#b33a3a"],
    autopct="%1.0f%%",
    startangle=90,
    explode=(0.06, 0),
    textprops={"fontsize": 10},
)
ax.set_title("SEM Supporting-Boundary Outcome (16 Runs)")
save(fig, "fig_pass_fail_pie.png")

# C2-style: Top vs Bottom deviation grouped bars
fig, ax = plt.subplots(figsize=(8.4, 3.8))
x = np.arange(len(df))
w = 0.38
ax.bar(x - w / 2, df["Hole_Dev_Top_um"], w, label="Top deviation", color="#2c6eaf", edgecolor="#222", lw=0.3)
ax.bar(x + w / 2, df["Hole_Dev_Bottom_um"], w, label="Bottom deviation", color="#e67e22", hatch="//", edgecolor="#222", lw=0.3)
ax.set_xticks(x)
ax.set_xticklabels(df["Run"].astype(str))
ax.set_xlabel("Run")
ax.set_ylabel("Hole Deviation (µm)")
ax.set_title("Top vs Bottom Hole Deviation — All 16 Runs")
ax.legend(fontsize=8)
save(fig, "fig_top_bottom_deviation.png")

# C3-style: Absolute asymmetry
fig, ax = plt.subplots(figsize=(8.2, 3.5))
cols = ["#b33a3a" if a > 50 else "#2e8b57" for a in df["Asymmetry"]]
ax.bar(df["Run"].astype(str), df["Asymmetry"], color=cols, edgecolor="#222", lw=0.4)
ax.axhline(50, color="#555", ls="--", lw=1, label="50 µm reference")
ax.set_xlabel("Run")
ax.set_ylabel("|Dev_Top − Dev_Bottom| (µm)")
ax.set_title("Hole Asymmetry per Run (Top–Bottom Gap)")
ax.legend(fontsize=8)
save(fig, "fig_asymmetry.png")

# C4-style: Circularity vs mean deviation paradox scatter
fig, ax = plt.subplots(figsize=(7.6, 4.2))
for _, r in df.iterrows():
    c = "#1b7a3d" if r.Success else "#888888"
    ax.scatter(r.Circ_ratio, r.Mean_Dev, s=90, c=c, edgecolors="black", lw=0.5, zorder=3)
    ax.annotate(f"R{int(r.Run)}", (r.Circ_ratio, r.Mean_Dev), textcoords="offset points", xytext=(4, 3), fontsize=7)
ax.set_xlabel("SEM Circularity Ratio (higher = better)")
ax.set_ylabel("Mean Hole Deviation (µm, lower looks 'better')")
ax.set_title("Paradox: SEM Circularity vs Mean Deviation")
ax.annotate(
    "Run 4 PASS\n(high circ, higher deviation)",
    xy=(1.0, df.loc[df.Run == 4, "Mean_Dev"].iloc[0]),
    xytext=(0.55, 250),
    fontsize=8,
    color="#1b7a3d",
    arrowprops=dict(arrowstyle="->", color="#1b7a3d"),
)
ax.annotate(
    "Run 5 FAIL\n(low deviation, bad SEM)",
    xy=(0.4, df.loc[df.Run == 5, "Mean_Dev"].iloc[0]),
    xytext=(0.55, 160),
    fontsize=8,
    color="#b33a3a",
    arrowprops=dict(arrowstyle="->", color="#b33a3a"),
)
save(fig, "fig_deviation_vs_circularity.png")

# Also keep energy / current-pulse heatmaps
fig, ax = plt.subplots(figsize=(7.5, 3.8))
ax.scatter(
    df["Energy"],
    df["Boundary_circularity_1to5"],
    c=["#1b7a3d" if s else "#888" for s in df.Success],
    s=70,
    edgecolors="black",
    lw=0.5,
)
for _, r in df.iterrows():
    ax.annotate(f"R{int(r.Run)}", (r.Energy, r.Boundary_circularity_1to5), textcoords="offset points", xytext=(3, 3), fontsize=7)
ax.set_xlabel("Discharge Energy E = I × T × (D/100)")
ax.set_ylabel("SEM Circularity (1–5)")
ax.set_title("Discharge Energy vs Supporting-Boundary Circularity")
save(fig, "fig_energy_vs_circularity.png")

pivot = df.pivot_table(index="Peak_Current_A", columns="Pulse_On_Time_us", values="Boundary_circularity_1to5", aggfunc="mean")
fig, ax = plt.subplots(figsize=(7.0, 3.6))
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
            ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=8)
fig.colorbar(im, ax=ax, label="Circularity")
save(fig, "fig_current_pulse_heatmap.png")

# C5-style: Mean top/bottom deviation by current and by pulse-on
fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.6))
for ax, col, title in [
    (axes[0], "Peak_Current_A", "By Peak Current"),
    (axes[1], "Pulse_On_Time_us", "By Pulse-on Time"),
]:
    g = df.groupby(col)[["Hole_Dev_Top_um", "Hole_Dev_Bottom_um"]].mean()
    xx = np.arange(len(g))
    ax.bar(xx - 0.18, g["Hole_Dev_Top_um"], 0.36, label="Top", color="#2c6eaf", edgecolor="#222", lw=0.3)
    ax.bar(xx + 0.18, g["Hole_Dev_Bottom_um"], 0.36, label="Bottom", color="#e67e22", hatch="//", edgecolor="#222", lw=0.3)
    ax.set_xticks(xx)
    ax.set_xticklabels([str(int(v)) for v in g.index])
    ax.set_title(title)
    ax.set_ylabel("Mean Deviation (µm)")
    ax.legend(fontsize=7)
fig.suptitle("Parameter Effects on Top/Bottom Deviation", fontsize=11)
save(fig, "fig_param_effects_dev.png")

# C6-style: Duty factor effect
fig, ax = plt.subplots(figsize=(7.2, 3.6))
g = df.groupby("Duty_Factor_pct")[["Hole_Dev_Top_um", "Hole_Dev_Bottom_um"]].mean()
xx = np.arange(len(g))
ax.bar(xx - 0.18, g["Hole_Dev_Top_um"], 0.36, label="Top", color="#2c6eaf", edgecolor="#222", lw=0.3)
ax.bar(xx + 0.18, g["Hole_Dev_Bottom_um"], 0.36, label="Bottom", color="#e67e22", hatch="//", edgecolor="#222", lw=0.3)
ax.set_xticks(xx)
ax.set_xticklabels([f"{int(v)}%" for v in g.index])
ax.set_xlabel("Duty Factor")
ax.set_ylabel("Mean Deviation (µm)")
ax.set_title("Duty Factor Effect on Top/Bottom Deviation")
ax.legend(fontsize=8)
save(fig, "fig_duty_effects_dev.png")

# MRR and TWR by run (report-inspired process response charts)
fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.5))
axes[0].bar(df["Run"].astype(str), df["Volume_Removal_Rate"], color="#5d6d7e", edgecolor="#222", lw=0.3)
axes[0].set_title("Volume Removal Rate by Run")
axes[0].set_xlabel("Run")
axes[0].set_ylabel("Volume Removal Rate")
axes[1].bar(df["Run"].astype(str), df["Tool_Wear_Rate"], color="#884ea0", edgecolor="#222", lw=0.3)
axes[1].set_title("Tool Wear Rate by Run")
axes[1].set_xlabel("Run")
axes[1].set_ylabel("Tool Wear Rate")
save(fig, "fig_mrr_twr.png")

# Deviation score ranking bar (shows wrong metric ordering)
fig, ax = plt.subplots(figsize=(8.2, 3.6))
ord_df = df.sort_values("Dev_Score")
cols = ["#1b7a3d" if s else "#b33a3a" for s in ord_df["Success"]]
ax.bar(ord_df["Run"].astype(str), ord_df["Dev_Score"], color=cols, edgecolor="#222", lw=0.4)
ax.set_xlabel("Run (ordered by deviation score, lower = 'better' on wrong metric)")
ax.set_ylabel("Deviation Score = MeanDev + 0.5·|Asym|")
ax.set_title("Wrong Metric Ranking: Deviation Score (green = only SEM PASS)")
save(fig, "fig_dev_score_ranking.png")

# Final recommendations (zone-based, no Phase wording in title)
recs = [
    ("Unknown\nposition", 4, 150, 80),
    ("Pore\ncenter", 4, 150, 80),
    ("Mid\npore", 4, 148, 79),
    ("Near\nstrut", 3.5, 150, 78),
    ("Near\nnode", 3.5, 145, 76),
]
names = [r[0] for r in recs]
I = np.array([r[1] for r in recs])
T = np.array([r[2] for r in recs])
D = np.array([r[3] for r in recs])
x = np.arange(len(names))
w = 0.25
fig, ax = plt.subplots(figsize=(8.0, 3.6))
ax.bar(x - w, I, w, label="Peak Current (A)", color="#2c6eaf")
ax.bar(x, T / 50.0, w, label="Pulse-on ÷ 50 (scaled)", color="#d4a017")
ax.bar(x + w, D / 20.0, w, label="Duty ÷ 20 (scaled)", color="#2e8b57")
ax.set_xticks(x)
ax.set_xticklabels(names, fontsize=8)
ax.set_ylabel("Scaled parameter value")
ax.set_title("Recommended EDM Parameters by Landing Zone")
ax.legend(fontsize=8)
save(fig, "fig_final_recommendations.png")

# Pipeline diagram
fig, ax = plt.subplots(figsize=(9.0, 5.4))
ax.set_xlim(0, 10)
ax.set_ylim(0, 6.5)
ax.axis("off")
ax.set_title("Prediction Pipeline: Circularity Ratio at Any (I, T, D, x, y)", fontsize=12)


def box(x, y, w, h, text, fc):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                       facecolor=fc, edgecolor="#222", linewidth=1.0)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7.6)


boxes = [
    (0.3, 5.1, 2.2, 1.0, "16 Lab Runs\n+ SEM labels\n(ground truth)", "#d9e8f5"),
    (2.9, 5.1, 2.4, 1.0, "GP posterior\n→ 1100 synthetic\nEDM points", "#f5e6c8"),
    (5.7, 5.1, 2.6, 1.0, "16 × grid landings\ngeometry-modulated\nlabels (~400 rows)", "#e2f0d9"),
    (0.3, 3.4, 4.0, 1.2, "Physics / Geometry Engine\nstrut/node distances, overlaps,\nintersection, geometry risk", "#f2d7d5"),
    (4.7, 3.4, 4.0, 1.2, "EDM Feature Engineering\nI, T, D, Energy, pulse-off,\nI×D, T/D", "#d5e8d4"),
    (0.3, 1.8, 4.0, 1.1, "GradientBoosting (120)\n→ circularity score 1–5", "#dae8fc"),
    (4.7, 1.8, 4.0, 1.1, "GradientBoosting (80)\n→ supporting intact 0/1", "#dae8fc"),
    (0.3, 0.3, 4.0, 1.1, "Physics Heuristic Blend\nlow I, long T, high D\nweighted by geometry drift", "#fff2cc"),
    (4.7, 0.3, 4.0, 1.1, "Output for any position\ncircularity ratio = score/5\nPASS if ≥3.5 & support OK", "#d5f5e3"),
]
for b in boxes:
    box(*b)
for (x1, y1, x2, y2) in [
    (1.4, 5.1, 1.4, 4.6), (4.1, 5.1, 2.5, 4.6), (7.0, 5.1, 6.5, 4.6),
    (2.3, 3.4, 2.3, 2.9), (6.7, 3.4, 6.7, 2.9),
    (2.3, 1.8, 2.3, 1.4), (6.7, 1.8, 6.7, 1.4), (4.3, 0.85, 4.7, 0.85),
]:
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", color="#333", lw=1.2))
save(fig, "fig_ml_pipeline.png")

# Geometry ideation schematic
fig, ax = plt.subplots(figsize=(7.2, 4.8))
ax.set_xlim(0, 1500)
ax.set_ylim(0, 1500)
ax.set_aspect("equal")
ax.set_xlabel("x (µm)")
ax.set_ylabel("y (µm)")
ax.set_title("Tool Landing Anywhere on 3×3 Lattice (1500 µm)")
for i in range(4):
    ax.axhline(i * 500, color="#888", lw=0.8)
    ax.axvline(i * 500, color="#888", lw=0.8)
for i in range(4):
    for j in range(4):
        ax.add_patch(plt.Circle((i * 500, j * 500), 117.8, color="#c0392b", alpha=0.55, zorder=2))
for i in range(3):
    for j in range(3):
        ax.add_patch(plt.Circle((i * 500 + 250, j * 500 + 250), 117.8, facecolor="white", edgecolor="#2980b9", lw=1.2, zorder=2))
ax.add_patch(plt.Circle((750, 750), 450, facecolor="none", edgecolor="#1a5276", lw=2.2, ls="--", zorder=3))
ax.plot(750, 750, "k+", markersize=10)
ax.text(760, 1180, "900 µm tool footprint", color="#1a5276", fontsize=9)
ax.text(40, 1420, "Nodes (may be destroyed)", color="#c0392b", fontsize=8)
ax.text(40, 1360, "Pores (openings)", color="#2980b9", fontsize=8)
ax.text(40, 1300, "Struts must survive as ring", color="#333", fontsize=8)
save(fig, "fig_geometry_ideation.png")

# Data expansion
fig, ax = plt.subplots(figsize=(8.0, 3.4))
ax.axis("off")
ax.set_title("How 16 Experiments Become Thousands of Training Rows", fontsize=12)
items = [
    (0.05, "16 SEM-labeled\nEDM runs", "#d9e8f5"),
    (0.28, "× grid landings\n(~150 µm step\nin 1500 µm area)", "#e2f0d9"),
    (0.55, "Geometry-modulated\ncircularity targets\n+ EDM features", "#f5e6c8"),
    (0.78, "GB models +\nphysics blend\nfor any (x,y)", "#d5f5e3"),
]
for x0, text, fc in items:
    ax.add_patch(FancyBboxPatch((x0, 0.25), 0.18, 0.5, transform=ax.transAxes,
                                boxstyle="round,pad=0.02,rounding_size=0.02",
                                facecolor=fc, edgecolor="#222"))
    ax.text(x0 + 0.09, 0.5, text, transform=ax.transAxes, ha="center", va="center", fontsize=8.5)
for x0 in (0.23, 0.46, 0.73):
    ax.annotate("", xy=(x0 + 0.04, 0.5), xytext=(x0, 0.5),
                xycoords=ax.transAxes, textcoords=ax.transAxes,
                arrowprops=dict(arrowstyle="->", lw=1.4, color="#333"))
save(fig, "fig_data_expansion.png")

print("All paper figures generated in", OUT)
