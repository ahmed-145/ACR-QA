#!/usr/bin/env python3
"""
generate_eval_figures.py  —  ACR-QA Thesis Figure Generator
============================================================
Generates ALL data-driven figures for Chapter 5 in publication quality.
Run from the ACR-QA-Book/figures/ directory:

    cd ACR-QA-Book/figures
    python generate_eval_figures.py

Outputs (all 300 dpi, ready for LaTeX):
  CONFUSION_MATRIX.png      — SecurityEval 2×2 CM + metrics bar
  PR_OPERATING_POINTS.png   — Precision-Recall scatter (iso-F1 curves)
  REALVULN_LEADERBOARD.png  — Recall bar chart (arXiv:2604.13764)
  METRICS_TABLE.png         — Full metrics comparison table
  FUNNEL_SLIDE.png          — Precision funnel (replaces old dark-bg version)
  HEAD_TO_HEAD.png          — Tool bar chart (replaces old dark-bg version)
  CONFIDENCE_SCORING.png    — Five-signal score diagram
  TEST_PYRAMID.png          — Testing pyramid with real counts

Numbers source: docs/ACTIVE_ROADMAP.md (verified 2026-06-05)
Tests:         2,805 passed, 83.60% coverage (task-765, 2026-06-05)
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

# ── KSIU colour palette ────────────────────────────────────────
NAVY    = "#002654"
NAVY2   = "#00336E"
GOLD    = "#C9A84C"
GOLD2   = "#a88535"
WHITE   = "#FFFFFF"
BGRAY   = "#f9fafb"
LGRAY   = "#e5e7eb"
MGRAY   = "#6b7280"
GREEN   = "#16a34a"
ORANGE  = "#ea580c"
RED     = "#dc2626"
PURPLE  = "#7c3aed"

plt.rcParams.update({
    "font.family":        "DejaVu Serif",
    "axes.titlesize":     13,
    "axes.labelsize":     11,
    "xtick.labelsize":    10,
    "ytick.labelsize":    10,
    "figure.dpi":         150,
    "savefig.dpi":        300,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.15,
})

def _spine_off(ax, sides=("top","right")):
    for s in sides:
        ax.spines[s].set_visible(False)

def _save(fig, name):
    pdf_name = name.replace(".png", ".pdf")
    fig.savefig(pdf_name)  # vector PDF for Overleaf (fast compile)
    fig.savefig(name)
    print(f"  [✓]  {name}")
    plt.close(fig)


# ══════════════════════════════════════════════════════════════
# FIG 1 — SecurityEval Confusion Matrix  (89+89 dual corpus)
# TPR=91.0%  → TP=81, FN=8
# FPR=75.3%  → FP=67, TN=22
# Precision=54.7%, F3=0.854, MCC=0.210, Youden J=0.157
# ══════════════════════════════════════════════════════════════
def fig1_confusion_matrix():
    TP, FN, FP, TN = 81, 8, 67, 22

    precision   = TP / (TP + FP)
    recall      = TP / (TP + FN)
    specificity = TN / (TN + FP)
    f1  = 2*precision*recall / (precision + recall)
    f3  = (1+9)*precision*recall / (9*precision + recall)   # β=3
    mcc = (TP*TN - FP*FN) / np.sqrt((TP+FP)*(TP+FN)*(TN+FP)*(TN+FN))
    fpr = FP / (FP + TN)
    j   = recall - fpr

    fig = plt.figure(figsize=(13, 5.5), facecolor=WHITE)
    gs  = fig.add_gridspec(1, 2, width_ratios=[1.1, 1], wspace=0.35)

    # ── LEFT: confusion matrix ────────────────────────────────
    ax = fig.add_subplot(gs[0])
    ax.set_facecolor(WHITE)

    vals   = [[TP, FN], [FP, TN]]
    lbl1   = [["TP = 81", "FN = 8"], ["FP = 67", "TN = 22"]]
    lbl2   = [["Correctly\ndetected", "Missed\nvulnerabilities"],
               ["False\nalarms", "Correctly\nrejected"]]
    colors = [[GREEN, ORANGE], [ORANGE, GREEN]]

    for r in range(2):
        for c in range(2):
            x0, y0 = c * 2.5, (1 - r) * 2.5
            rect = FancyBboxPatch((x0 + 0.06, y0 + 0.06), 2.38, 2.38,
                                  boxstyle="round,pad=0.08",
                                  facecolor=colors[r][c], edgecolor=WHITE,
                                  linewidth=2, alpha=0.88)
            ax.add_patch(rect)
            ax.text(x0 + 1.25, y0 + 1.75, lbl1[r][c],
                    ha="center", va="center", fontsize=16,
                    fontweight="bold", color=WHITE)
            ax.text(x0 + 1.25, y0 + 0.9, lbl2[r][c],
                    ha="center", va="center", fontsize=9.0,
                    color=WHITE, style="italic")

    ax.set_xlim(-0.5, 5.5); ax.set_ylim(-0.8, 5.5)
    ax.set_xticks([1.25, 3.75])
    ax.set_xticklabels(["Predicted:\nVulnerable", "Predicted:\nClean"],
                       fontsize=10.5, fontweight="bold", color=NAVY)
    ax.set_yticks([1.25, 3.75])
    ax.set_yticklabels(["Actual: Clean", "Actual: Vulnerable"],
                       fontsize=10.5, fontweight="bold", color=NAVY,
                       rotation=0, ha="right", va="center")
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for sp in ax.spines.values(): sp.set_visible(False)

    # dataset note
    ax.text(2.5, -0.55,
            "SecurityEval benchmark · 89 vulnerable + 89 clean Python snippets · CWE-matched",
            ha="center", va="center", fontsize=8, color=MGRAY, style="italic")

    ax.set_title("SecurityEval Confusion Matrix",
                 fontsize=12, fontweight="bold", color=NAVY, pad=14)

    # ── RIGHT: metrics horizontal bars ───────────────────────
    ax2 = fig.add_subplot(gs[1])
    ax2.set_facecolor(BGRAY)
    _spine_off(ax2, ("top", "right"))

    metrics = [
        ("TPR (Recall)",         recall,      GREEN,  "↑ higher is better"),
        ("Specificity (TNR)",     specificity, ORANGE, "↑ limited by FPR"),
        ("Precision",             precision,   ORANGE, "↑ context-dependent"),
        ("F₃  (β=3, recall-heavy)", f3,        GREEN,  "↑ key metric"),
        ("F₁  (harmonic mean)",  f1,           GREEN,  "↑"),
        ("MCC",                  mcc,          GOLD2,  "↑ balanced"),
        ("Youden J",             j,            GOLD2,  "↑ vs Bandit 0.090"),
        ("FPR",                  fpr,          RED,    "↓ lower is better"),
    ]
    names, vals2, cols, notes = zip(*metrics)
    y_pos = np.arange(len(names))

    bars = ax2.barh(y_pos, vals2, color=cols, edgecolor=WHITE,
                    height=0.62, linewidth=0.8, zorder=2)

    for i, (bar, val, note) in enumerate(zip(bars, vals2, notes)):
        ax2.text(val + 0.02, bar.get_y() + bar.get_height()/2,
                 f"{val:.3f}", va="center", ha="left",
                 fontsize=9.5, fontweight="bold", color=cols[i])
        ax2.text(1.05, bar.get_y() + bar.get_height()/2,
                 note, va="center", ha="left", fontsize=7.5, color=MGRAY)

    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(names, fontsize=9.5)
    ax2.set_xlim(0, 1.55)
    ax2.set_xlabel("Score (0–1)", fontsize=10)
    ax2.axvline(0.5, color=MGRAY, linestyle="--", linewidth=0.9, zorder=1)
    ax2.text(0.5, 7.6, "Random Baseline (0.5)", fontsize=8, color=MGRAY, ha="center", va="bottom")
    ax2.set_ylim(-0.6, 8.2)
    ax2.grid(axis="x", alpha=0.2, linewidth=0.5, zorder=0)
    ax2.set_title("Derived Metrics at SecurityEval\nOperating Point",
                  fontsize=12, fontweight="bold", color=NAVY)

    # Context callout
    callout_text = (
        "High FPR reflects SecurityEval's synthetic clean snippets (adversarial by design).\n"
        "Production adversarial corpus (Layer B, 30 repos): Confirmed Tier → 96.4% precision."
    )
    fig.text(0.5, 0.08, callout_text,
             ha="center", va="top", fontsize=8.5, color=MGRAY, style="italic",
             bbox=dict(boxstyle="round,pad=0.4", facecolor=LGRAY, edgecolor=LGRAY))

    fig.subplots_adjust(top=0.85, bottom=0.25)
    _save(fig, "CONFUSION_MATRIX.png")


# ══════════════════════════════════════════════════════════════
# FIG 2 — Precision-Recall Operating Points
# ══════════════════════════════════════════════════════════════
def fig2_pr_curve():
    fig, ax = plt.subplots(figsize=(9, 7), facecolor=WHITE)
    ax.set_facecolor(BGRAY)
    _spine_off(ax)

    # iso-F1 background curves
    r_range = np.linspace(0.02, 1.0, 500)
    for fval, alpha in [(0.2, 0.35), (0.4, 0.45), (0.6, 0.55), (0.8, 0.65)]:
        p = (fval * r_range) / np.maximum(2*r_range - fval, 1e-9)
        p = np.clip(p, 0, 1)
        m = p > 0
        ax.plot(r_range[m], p[m], color=LGRAY, linewidth=0.9,
                linestyle="--", zorder=1)
        idx = np.searchsorted(r_range[m], 0.10)
        if idx < len(r_range[m]):
            ax.text(r_range[m][idx], p[m][idx] + 0.015,
                    f"F₁={fval}", fontsize=7.5, color="#9ca3af")

    # Ideal zone
    ax.fill_between([0.75, 1.0], [0.75, 0.75], [1.0, 1.0],
                    alpha=0.10, color=GREEN)
    ax.text(0.87, 0.78, "Ideal\nZone", fontsize=8, color=GREEN,
            ha="center", style="italic")

    # (recall, precision, label, color, marker, size, text_x, text_y)
    points = [
        (0.910, 0.547, "ACR-QA Full Output\n(TPR=91.0%, Prec=54.7%, F\u2083=0.854)",
         NAVY,   "o", 200, 0.70,  0.42),
        (0.371, 0.964, "ACR-QA Confirmed Tier\n(TPR=37.1%, Prec=96.4%)\nAuto-block mode",
         GOLD,   "D", 200, 0.50,  0.80),
        (0.324, 0.874, "ACR-QA + LLM\n(TPR=32.4%, Prec=87.4%)",
         NAVY2,  "s", 130, 0.07,  0.72),
        (0.251, 0.903, "ACR-QA RealVuln\n(TPR=25.1%, Prec=90.3%)",
         PURPLE, "^", 130, 0.07,  0.98),
        (0.510, 0.140, "Bandit\n(TPR=51%, Prec=14.0%)",
         RED,    "o", 110, 0.52,  0.23),
        (0.240, 0.360, "Semgrep CE\n(TPR=24%, Prec=36.0%)",
         ORANGE, "o", 110, 0.06,  0.27),
    ]

    for rec, prec, lbl, color, marker, sz, tx, ty in points:
        ax.scatter(rec, prec, color=color, marker=marker, s=sz,
                   zorder=5, edgecolors=WHITE, linewidths=1.5)
        ax.annotate(lbl, xy=(rec, prec), xytext=(tx, ty),
                    fontsize=8.5, color=color, fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color=color, lw=0.8),
                    bbox=dict(boxstyle="round,pad=0.2", facecolor=WHITE,
                              edgecolor=color, alpha=0.92, linewidth=0.9))

    ax.set_xlim(0, 1.05); ax.set_ylim(0, 1.12)
    ax.set_xlabel("Recall (TPR)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Precision", fontsize=11, fontweight="bold")
    ax.set_title("Precision-Recall Operating Points\n"
                 "ACR-QA v5.0.0rc2 vs. Baselines — Multiple Evaluation Corpora",
                 fontsize=13, fontweight="bold", color=NAVY)
    ax.grid(True, alpha=0.25, linewidth=0.5)
    ax.tick_params(labelsize=10)

    handles = [
        mpatches.Patch(color=c, label=l) for c, l in [
            (NAVY,   "ACR-QA Full  (SecurityEval)"),
            (GOLD,   "ACR-QA Confirmed Tier  (auto-block)"),
            (NAVY2,  "ACR-QA + LLM  (augmented)"),
            (PURPLE, "ACR-QA  (RealVuln corpus)"),
            (RED,    "Bandit  (SecurityEval)"),
            (ORANGE, "Semgrep CE  (SecurityEval)"),
        ]
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=8,
              framealpha=0.95, edgecolor=LGRAY)
    _save(fig, "PR_OPERATING_POINTS.png")


# ══════════════════════════════════════════════════════════════
# FIG 3 — RealVuln 2026 Recall Leaderboard
# Source: arXiv:2604.13764
# ══════════════════════════════════════════════════════════════
def fig3_realvuln():
    tools   = ["ACR-QA\n+LLM\nAugmented", "ACR-QA\nFull\nOutput",
               "Bandit", "Semgrep\nCE", "Snyk\nCode", "SonarQube\nCE"]
    vals    = [32.4, 25.1, 19.4, 17.5, 17.4, 6.5]
    colors  = [GOLD, NAVY, MGRAY, "#9ca3af", "#9ca3af", "#d1d5db"]

    fig, ax = plt.subplots(figsize=(10, 5.8), facecolor=WHITE)
    ax.set_facecolor(BGRAY)
    _spine_off(ax)

    bars = ax.bar(np.arange(len(tools)), vals, color=colors,
                  edgecolor=WHITE, linewidth=0.9, width=0.56, zorder=2)

    for bar, val, col in zip(bars, vals, colors):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.4,
                f"{val}%", ha="center", va="bottom",
                fontsize=11, fontweight="bold",
                color=NAVY if col in (GOLD, NAVY) else MGRAY)

    # ACR-QA baseline dashed line
    ax.axhline(25.1, color=NAVY, linestyle="--", linewidth=1.1,
               alpha=0.55, zorder=1)
    ax.text(5.55, 25.7, "ACR-QA\nbaseline", fontsize=8, color=NAVY,
            ha="right")

    # +7.3pp arrow on LLM bar
    ax.annotate("+7.3 pp gain\nover SAST-only",
                xy=(0, 32.4), xytext=(0.62, 40.5),
                fontsize=9, color=GOLD2, fontweight="bold",
                ha="left",
                arrowprops=dict(arrowstyle="->", color=GOLD2, lw=1.3))

    # star on plain ACR-QA (no star glyph to avoid box characters)
    ax.text(1, 28.5, "Best open-source\nrule-based tool",
            ha="center", fontsize=8.5, color=NAVY, fontweight="bold")

    ax.set_xticks(np.arange(len(tools)))
    ax.set_xticklabels(tools, fontsize=10)
    ax.set_ylim(0, 50)
    ax.set_ylabel("Full-Corpus Recall (%)", fontsize=11, fontweight="bold")
    ax.yaxis.set_minor_locator(mticker.MultipleLocator(5))
    ax.grid(axis="y", alpha=0.25, linewidth=0.5, zorder=0)
    ax.set_title("RealVuln 2026 Recall Leaderboard\n"
                 "22 Real-World Python CVE Applications · "
                 "Third-Party Ground Truth (arXiv:2604.13764)",
                 fontsize=13, fontweight="bold", color=NAVY)
    ax.text(0.5, -0.17,
            "ACR-QA detectable-subset recall: 37.8%  ·  Source: arXiv:2604.13764, verified June 2026",
            ha="center", transform=ax.transAxes,
            fontsize=8.5, color=MGRAY, style="italic")
    _save(fig, "REALVULN_LEADERBOARD.png")


# ══════════════════════════════════════════════════════════════
# FIG 4 — Metrics Comparison Table (rendered as figure)
# ══════════════════════════════════════════════════════════════
def fig4_metrics_table():
    fig, ax = plt.subplots(figsize=(14, 4.8), facecolor=WHITE)
    ax.set_axis_off()

    cols = ["Tool / Mode", "Corpus", "Prec.", "TPR\n(Recall)", "F₁",
            "F₃", "MCC", "Youden J", "CVE\nRecall"]
    rows = [
        ["ACR-QA Full Output",          "SecurityEval (89+89)", "54.7%", "91.0%", "68.3%", "0.854", "0.210", "0.157", "8/8 (100%)"],
        ["ACR-QA Confirmed Tier (P4)",  "Adversarial 30-repo",  "96.4%", "37.1%", "98.2%", "—",    "—",    "—",     "8/8 (100%)"],
        ["ACR-QA + LLM Augmented",     "RealVuln 2026",         "87.4%", "32.4%", "—",     "—",    "—",    "—",     "—"],
        ["ACR-QA (Layer A core)",       "DVPWA/Pygoat/VulPy/DSVW", "97.1%", "100%†", "—", "—",   "—",    "—",     "—"],
        ["Bandit (standalone)",         "SecurityEval / Adv.",   "14.0%", "51.0%", "21.8%", "—",   "—",    "0.090", "1/8 (12.5%)"],
        ["Semgrep CE",                  "SecurityEval / Adv.",   "36.0%", "24.0%", "45.7%", "—",   "—",    "0.056", "5/8 (62.5%)"],
        ["Snyk Code",                   "RealVuln 2026",         "—",     "17.4%", "—",     "—",   "—",    "—",     "—"],
        ["SonarQube CE",                "RealVuln 2026",         "—",     "6.5%",  "—",     "—",   "—",    "—",     "—"],
    ]

    cell_colors = []
    for r in rows:
        if "ACR-QA" in r[0]:
            cell_colors.append(["#e8f0fe"] * len(cols))
        else:
            cell_colors.append([WHITE] * len(cols))

    tbl = ax.table(cellText=rows, colLabels=cols,
                   cellLoc="center", loc="center",
                   cellColours=cell_colors,
                   colWidths=[0.22, 0.18, 0.08, 0.09, 0.07, 0.07, 0.07, 0.08, 0.11])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.72)

    for j in range(len(cols)):
        cell = tbl[0, j]
        cell.set_facecolor(NAVY)
        cell.set_text_props(color=WHITE, fontweight="bold", fontsize=9)

    ax.set_title("Full Evaluation Metrics — ACR-QA v5.0.0rc2 vs. Baselines",
                 fontsize=12, fontweight="bold", color=NAVY, pad=10, loc="left")
    ax.text(0.0, -0.05,
            "† Recall limited to annotated categories (DVPWA 50%/67% at category/file level). "
            "— = not measured on this corpus. "
            "SecurityEval: 89+89 Python snippets. "
            "Adversarial: 30-repo corpus, conservative triage.",
            transform=ax.transAxes, fontsize=7.5, color=MGRAY, style="italic")
    _save(fig, "METRICS_TABLE.png")


# ══════════════════════════════════════════════════════════════
# FIG 5 — Precision Funnel  (replaces dark-bg HTML version)
# ══════════════════════════════════════════════════════════════
def fig5_funnel():
    labels  = ["Rung 0", "Rung 1", "Rung 2", "Rung 3", "P3", "P4 Confirmed"]
    descs   = ["Raw output — all tools, all severities",
               "+ HIGH / MEDIUM severity filter",
               "+ Reachability demote",
               "+ Security-tier rule set",
               "+ Semantic taint gate",
               "Confirmed Tier (4-criterion gate)"]
    counts  = [1942, 630, 623, 219, 151, 55]
    precs   = [8.6,  8.6,  8.5, 24.7, 26.9, 96.4]
    n = len(labels)
    y = np.arange(n)[::-1]
    max_c = max(counts)
    widths = [max(0.08, c/max_c) for c in counts]

    def _rung_color(prec):
        t = prec / 100.0
        r = int(200*(1-t) + 22*t)
        g = int(50*(1-t)  + 160*t)
        b = int(30*(1-t)  + 74*t)
        return f"#{r:02x}{g:02x}{b:02x}"

    colors = [_rung_color(p) for p in precs]
    colors[-1] = GOLD

    fig, ax = plt.subplots(figsize=(14, 6), facecolor=WHITE)
    ax.set_facecolor(BGRAY)
    _spine_off(ax, ("top", "right", "bottom"))
    ax.tick_params(left=False, bottom=False)
    ax.set_xticks([])

    bars = ax.barh(y, widths, height=0.62, color=colors,
                   edgecolor=WHITE, linewidth=1.0, left=0)

    is_p4_flags = [False]*5 + [True]
    for bar, tag, desc, count, prec, is_p4 in zip(
            bars, labels, descs, counts, precs, is_p4_flags):
        bw = bar.get_width()
        by = bar.get_y() + bar.get_height() / 2
        ax.text(bw + 0.015, by, desc,
                va="center", ha="left", fontsize=9.5,
                fontweight="bold" if is_p4 else "normal",
                color=GOLD2 if is_p4 else NAVY)
        if bw > 0.12:
            ax.text(bw / 2, by, f"{count:,}",
                    va="center", ha="center",
                    fontsize=10, fontweight="bold", color=WHITE)
        else:
            ax.text(bw + 0.002, by + 0.24, f"{count:,}",
                    va="center", ha="left", fontsize=9,
                    fontweight="bold", color=GOLD2 if is_p4 else NAVY)
        ax.text(1.52, by, f"{prec:.1f}%", va="center", ha="right",
                fontsize=10 if is_p4 else 9,
                fontweight="bold" if is_p4 else "normal",
                color=GOLD2 if is_p4 else NAVY)
        ax.text(1.60, by, "8/8 (100%)", va="center", ha="left",
                fontsize=8.5, color=GREEN, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10, fontweight="bold", color=NAVY)
    ax.set_xlim(0, 1.90)
    ax.set_ylim(-0.55, n - 0.05)
    ax.text(1.52, n - 0.2, "Precision", ha="right", fontsize=9,
            fontweight="bold", color=MGRAY)
    ax.text(1.60, n - 0.2, "CVE Recall", ha="left", fontsize=9,
            fontweight="bold", color=GREEN)
    ax.set_title("The Precision Funnel \u2014 ACR-QA v5.0.0rc2\n"
                 "1,942 raw findings  \u2192  55 Confirmed Tier  \u2192  96.4% precision  \u00b7  "
                 "100% CVE recall preserved at every rung",
                 fontsize=13, fontweight="bold", color=NAVY, pad=12)
    _save(fig, "FUNNEL_SLIDE.png")


# ══════════════════════════════════════════════════════════════
# FIG 6 — Head-to-Head Bar Chart  (replaces dark-bg HTML version)
# ══════════════════════════════════════════════════════════════
def fig6_head_to_head():
    tools = ["Bandit\n(open source\nPython only)",
             "Semgrep CE\n(open source\nmulti-lang)",
             "ACR-QA Rung 3\n(sec-tier rules)",
             "ACR-QA P3\n(+ taint gate)",
             "ACR-QA P4\nConfirmed Tier\n(auto-block)"]
    prec      = [14.0, 36.0, 24.7, 26.9, 96.4]
    cve_pct   = [12.5, 62.5, 100.,  100., 100.]   # CVE recall %
    f1        = [21.8, 45.7, 39.6,  42.5, 98.2]

    x = np.arange(len(tools))
    w = 0.25

    fig, ax = plt.subplots(figsize=(12, 6.2), facecolor=WHITE)
    ax.set_facecolor(BGRAY)
    _spine_off(ax)

    b1 = ax.bar(x - w,   prec,    w, label="Conservative Precision (%)",
                color=[LGRAY]*4 + [NAVY],   edgecolor=WHITE, linewidth=0.8)
    b2 = ax.bar(x,        cve_pct, w, label="CVE Recall % (8 detectable)",
                color=[LGRAY]*4 + [GOLD],   edgecolor=WHITE, linewidth=0.8)
    b3 = ax.bar(x + w,   f1,      w, label="F₁ Score (%)",
                color=[LGRAY]*4 + [GREEN],  edgecolor=WHITE, linewidth=0.8)

    # Darken bars for non-ACR-QA tools to distinguish them
    for bars, alt_colors in [
        (b1, ["#9ca3af", "#9ca3af", "#6b7280", "#4b5563"]),
        (b2, ["#9ca3af", "#9ca3af", "#6b7280", "#4b5563"]),
        (b3, ["#9ca3af", "#9ca3af", "#6b7280", "#4b5563"]),
    ]:
        for i, (bar, col) in enumerate(zip(list(bars)[:-1], alt_colors)):
            bar.set_facecolor(col)

    def _label(bars):
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.8,
                    f"{h:.0f}%", ha="center", va="bottom",
                    fontsize=8, fontweight="bold", color=NAVY)
    _label(b1); _label(b2); _label(b3)

    # F1=98.2% champion callout
    ax.annotate("F₁ = 98.2%\n>52pp margin\nover next best",
                xy=(x[-1] + w, 98.2), xytext=(x[-1] + w + 0.55, 85),
                fontsize=9, fontweight="bold", color=GREEN,
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.3),
                bbox=dict(boxstyle="round,pad=0.3", facecolor=WHITE,
                          edgecolor=GREEN, alpha=0.9))

    ax.set_xticks(x); ax.set_xticklabels(tools, fontsize=9.5)
    ax.set_ylim(0, 118)
    ax.set_ylabel("Score (%)", fontsize=11, fontweight="bold")
    ax.set_title("Head-to-Head Benchmark: Precision · CVE Recall · F₁\n"
                 "Same 30-repo adversarial corpus · Same 8-CVE recall battery · Conservative triage",
                 fontsize=13, fontweight="bold", color=NAVY)
    # Create custom legend patches to match the ACR-QA P4 colors (NAVY, GOLD, GREEN)
    handles = [
        mpatches.Patch(color=NAVY, label="Conservative Precision (%)"),
        mpatches.Patch(color=GOLD, label="CVE Recall % (8 detectable)"),
        mpatches.Patch(color=GREEN, label="F₁ Score (%)")
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=9, framealpha=0.95, edgecolor=LGRAY)
    ax.grid(axis="y", alpha=0.25, linewidth=0.5, zorder=0)
    ax.tick_params(axis="x", length=0)

    ax.text(0.5, -0.14,
            "95% CI [90.9%, 100%] via bootstrap (10,000 resamples, seed 42). "
            "Corpus: top-20 PyPI + top-6 npm + top-4 Go, SHA-pinned.",
            ha="center", transform=ax.transAxes,
            fontsize=8, color=MGRAY, style="italic")
    _save(fig, "HEAD_TO_HEAD.png")


# ══════════════════════════════════════════════════════════════
# FIG 7 — Confidence Scoring Five-Signal Diagram
# ══════════════════════════════════════════════════════════════
def fig7_confidence_scoring():
    fig, ax = plt.subplots(figsize=(10, 7.5), facecolor=WHITE)
    ax.set_axis_off()
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)

    # Signal boxes
    signals = [
        ("Signal 1 — Severity Level",       "CRITICAL=100, HIGH=80,\nMEDIUM=50, LOW=20",    "weight ×0.40", 8.5),
        ("Signal 2 — Finding Category",      "security=100, style=40,\ndeadcode=30",         "weight ×0.20", 6.9),
        ("Signal 3 — Tool Reliability",      "Bandit=90, Ruff=80,\nVulture=70, Radon=60",   "weight ×0.15", 5.3),
        ("Signal 4 — Rule Specificity",      "CWE-mapped=100,\ngeneric=50",                  "weight ×0.10", 3.7),
        ("Signal 5 — Auto-Fix Available",    "yes=100, no=0",                                "weight ×0.10", 2.1),
    ]
    for title, body, weight, y in signals:
        rect = FancyBboxPatch((0.3, y - 0.55), 4.1, 1.22,
                              boxstyle="round,pad=0.08",
                              facecolor=LGRAY, edgecolor=NAVY2, linewidth=1.2)
        ax.add_patch(rect)
        ax.text(0.5, y + 0.44, title, fontsize=9, fontweight="bold", color=NAVY, va="center")
        ax.text(0.5, y - 0.02, body,  fontsize=8,  color=MGRAY,  va="center")
        ax.text(4.25, y + 0.22, weight, fontsize=8.5, color=NAVY2, va="center", ha="right", style="italic")

        # arrow to weighted sum
        ax.annotate("", xy=(5.85, 4.85),
                    xytext=(4.42, y + 0.06),
                    arrowprops=dict(arrowstyle="-|>", color=NAVY2,
                                    lw=0.9, mutation_scale=10,
                                    connectionstyle="arc3,rad=-0.15"))

    # Bonus box
    rect_b = FancyBboxPatch((0.3, 0.3), 4.1, 1.0,
                             boxstyle="round,pad=0.08",
                             facecolor="#fef9c3", edgecolor=GOLD, linewidth=1.5)
    ax.add_patch(rect_b)
    ax.text(2.35, 0.80, "Bonus: Multi-tool agreement  (+5 pts)",
            fontsize=9, fontweight="bold", color=GOLD2, ha="center")
    # Start the arrow from the right edge of the Bonus box to avoid crossing Signal 5
    ax.annotate("", xy=(5.85, 4.5),
                xytext=(4.42, 0.8),
                arrowprops=dict(arrowstyle="-|>", color=GOLD2,
                                lw=0.9, mutation_scale=10,
                                connectionstyle="arc3,rad=-0.1"))

    # Weighted sum box
    ws = FancyBboxPatch((5.5, 4.35), 2.2, 1.0,
                          boxstyle="round,pad=0.1",
                          facecolor=NAVY, edgecolor=NAVY2, linewidth=1.5)
    ax.add_patch(ws)
    ax.text(6.6, 4.86, "Weighted\nSum", ha="center", va="center",
            fontsize=10, fontweight="bold", color=WHITE)

    # Arrow down to Cs
    ax.annotate("", xy=(6.6, 2.95),
                xytext=(6.6, 4.35),
                arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.5,
                                mutation_scale=14))

    # Cs box
    cs = FancyBboxPatch((5.0, 1.65), 3.2, 1.2,
                         boxstyle="round,pad=0.08",
                         facecolor=GOLD, edgecolor=GOLD2, linewidth=2.0)
    ax.add_patch(cs)
    ax.text(6.6, 2.28, "Confidence Score  Cₛ  [0–100]",
            ha="center", va="center", fontsize=10.5, fontweight="bold", color=WHITE)

    # Threshold band (shifted right and adjusted to prevent overlap)
    band_text = (
        "Cₛ < 30    →  Deprioritised (soft suppression)\n"
        "30 ≤ Cₛ < 60  →  LOW confidence tier\n"
        "60 ≤ Cₛ < 80  →  MEDIUM confidence tier\n"
        "Cₛ ≥ 80    →  HIGH confidence tier  (Confirmed Tier gate)\n"
        "No labelled dataset required — label-free design (RQ3)"
    )
    rect_t = FancyBboxPatch((4.8, -0.28), 4.9, 1.5,
                             boxstyle="round,pad=0.06",
                             facecolor="#f0fdf4", edgecolor=GREEN, linewidth=1.2)
    ax.add_patch(rect_t)
    ax.text(7.25, 0.47, band_text, ha="center", va="center",
            fontsize=8, color=NAVY, family="monospace")
    ax.annotate("", xy=(6.6, 1.28),
                xytext=(6.6, 1.65),
                arrowprops=dict(arrowstyle="-|>", color=GOLD2, lw=1.2,
                                mutation_scale=12))

    ax.set_title("ACR-QA: Five-Signal Label-Free Confidence Scoring (RQ3)\n"
                 "No labelled dataset required — signal weights tuned on ground-truth corpus",
                 fontsize=12, fontweight="bold", color=NAVY, pad=10)
    _save(fig, "CONFIDENCE_SCORING.png")


# ══════════════════════════════════════════════════════════════
# FIG 8 — Test Pyramid with real counts (June 2026)
# Total: 2,805 Python passing + 104 Vitest + 55 Playwright + 14 axe
# ══════════════════════════════════════════════════════════════
def fig8_test_pyramid():
    # Bottom → Top (widest first)
    layers = [
        # label,               count,   detail,                           color
        ("Unit Tests\n(pytest)", "~1,933",
         "19 engine modules · 3 adapters\nconfidence scorer · JWT · risk predictor",
         NAVY),
        ("Integration Tests\n(pytest)", "~667",
         "Full pipeline · FastAPI · Celery · PostgreSQL\nChaos resilience (13 failure tests)",
         NAVY2),
        ("TypeScript Unit\n(Vitest)", "104",
         "Components · hooks · API client\nFindingHistory · PRRisk · RunHeatmap",
         GOLD2),
        ("Accessibility\n(axe-core)", "14",
         "WCAG 2.1 AA · 5 dashboard pages\nEN + AR RTL · colour contrast · ARIA",
         "#7c3aed"),
        ("End-to-End\n(Playwright)", "55",
         "Full user journeys · scan submission\nresult browsing · SARIF export",
         GREEN),
    ]

    fig, ax = plt.subplots(figsize=(10, 7), facecolor=WHITE)
    ax.set_axis_off()
    ax.set_xlim(-2.0, 15.0); ax.set_ylim(-0.5, len(layers) * 1.28 + 0.5)

    max_half_w = 4.5
    for i, (label, count, detail, color) in enumerate(layers):
        t = i / (len(layers) - 1)
        w = max_half_w * (1 - t * 0.65)
        x0 = 5.0 - w
        y0 = i * 1.28

        rect = FancyBboxPatch((x0, y0 + 0.05), w*2, 1.10,
                              boxstyle="round,pad=0.07",
                              facecolor=color, edgecolor=WHITE,
                              linewidth=1.5, alpha=0.88)
        ax.add_patch(rect)

        ax.text(5.0, y0 + 0.60, label, ha="center", va="center",
                fontsize=10, fontweight="bold", color=WHITE)

        # count badge (vertically aligned on the right)
        ax.text(9.8, y0 + 0.60, count,
                ha="left", va="center", fontsize=12,
                fontweight="bold", color=color)

        # detail (vertically aligned on the far right)
        ax.text(11.0, y0 + 0.60, detail,
                ha="left", va="center", fontsize=7.5, color=MGRAY)

    # Vertical indicator arrow and labels on the left side (outside the pyramid)
    ax.annotate("", xy=(-0.4, len(layers)*1.28 - 0.4), xytext=(-0.4, 0.4),
                arrowprops=dict(arrowstyle="->", color=MGRAY, lw=1.5, mutation_scale=15))
    ax.text(-0.55, 0.4, "Fastest / Most\n(pytest / Unit)", ha="right", va="center",
            fontsize=8.5, color=GREEN, fontweight="bold")
    ax.text(-0.55, len(layers)*1.28 - 0.4, "Slowest / Fewest\n(Playwright / E2E)", ha="right", va="center",
            fontsize=8.5, color=MGRAY, fontweight="bold")

    total = "2,805 Python tests passing  +  104 Vitest  +  55 Playwright  +  14 axe-core"
    ax.text(5.0, -0.42, total, ha="center", va="top",
            fontsize=9.5, color=NAVY, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.35", facecolor=LGRAY, edgecolor=LGRAY))

    ax.set_title("ACR-QA v5.0.0rc2 — Test Suite: Four-Layer Architecture\n"
                 "83.60% combined coverage · CI gate: 82% · run ≈ 12 min",
                 fontsize=13, fontweight="bold", color=NAVY, pad=10)
    _save(fig, "TEST_PYRAMID.png")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys, os
    print("=" * 60)
    print("ACR-QA Thesis — Evaluation Figures Generator")
    print("=" * 60)
    figures = [
        ("1. SecurityEval Confusion Matrix",    fig1_confusion_matrix),
        ("2. Precision-Recall Operating Points", fig2_pr_curve),
        ("3. RealVuln 2026 Leaderboard",        fig3_realvuln),
        ("4. Metrics Comparison Table",          fig4_metrics_table),
        ("5. Precision Funnel",                  fig5_funnel),
        ("6. Head-to-Head Benchmark",            fig6_head_to_head),
        ("7. Confidence Scoring Diagram",        fig7_confidence_scoring),
        ("8. Test Pyramid",                      fig8_test_pyramid),
    ]
    for name, fn in figures:
        print(f"\n→ Generating {name}...")
        fn()
    print("\n" + "=" * 60)
    print("All 8 figures generated. Recompile PDF with:")
    print("  pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex")
    print("=" * 60)
