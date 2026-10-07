"""Render the README figures (docs/img/*.png) from exports/*.csv."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

OUT = Path("docs/img")
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
# Fixed identity colors: A / marcel_naive = naive curve, B / hybrid = corrected curve, C / mixed.
COLOR = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a",
         "marcel_naive": "#2a78d6", "hybrid": "#eb6834", "mixed": "#1baf7a", "persistence": "#8a8984"}
METHOD = {"A": "Naive delta method", "B": "Survivorship-corrected (IPW)", "C": "Mixed-effects fixed curve"}
MODEL = {"marcel_naive": "Marcel + naive curve", "hybrid": "Marcel + corrected curve (shipped)", "mixed": "Mixed-effects model"}
STAT = {
    "bpm": "BPM (pts/100)", "fg3_pct": "3P%", "fg3a_rate": "3PA rate", "ft_pct": "FT%",
    "rim_fg_pct": "Rim FG%", "rim_share": "Rim shot share", "ast_pct": "AST%", "tov_pct": "TOV%",
    "drb_pct": "DRB%", "stl_pct": "STL%", "blk_pct": "BLK%", "mp": "Minutes",
    "xfg_pct": "Shot quality (xFG%)", "shotmaking": "Shot-making",
}
SKILLS = list(STAT)[:12]  # the 12 box-score skills; the two shot-model measures get their own chart
PCT_0_1 = {"fg3_pct", "fg3a_rate", "ft_pct", "rim_fg_pct", "rim_share", "xfg_pct", "shotmaking"}  # shown ×100 as points

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.edgecolor": GRID, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10, "axes.titlesize": 11,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
})


def scaled(df, stat, cols=("value", "lo", "hi")):
    k = 100 if stat in PCT_0_1 else 1
    return df.assign(**{c: df[c] * k for c in cols if c in df})


def headline(curves):
    d = curves[curves.stat == "bpm"]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for m in ["A", "B"]:
        s = d[d.method == m]
        ax.fill_between(s.age, s.lo, s.hi, color=COLOR[m], alpha=0.15, linewidth=0)
        ax.plot(s.age, s.value, color=COLOR[m], linewidth=2, label=METHOD[m] + " (80% bootstrap band)")
        at34 = s[s.age == 34].iloc[0]  # label the age the title quotes
        ax.scatter(at34.age, at34.value, s=40, color=COLOR[m], edgecolors=SURFACE, linewidths=2, zorder=3)
        ax.annotate(f"{at34.value:+.1f}", (at34.age, at34.value), xytext=(-8, 0), textcoords="offset points",
                    ha="right", va="center", color=INK, fontsize=9)
    ax.axhline(0, color=INK2, linewidth=0.8)
    ax.axvline(27, color=GRID, linewidth=1, linestyle="--")
    ax.set_xticks(range(20, 37, 2))
    ax.set_xlabel("Age")
    ax.set_ylabel("BPM change vs. age 27")
    a, b = (d[(d.method == m) & (d.age == 34)].value.iloc[0] for m in "AB")
    ax.set_title(f"The naive method overstates BPM decline: {a:+.1f} vs {b:+.1f} by age 34")
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT / "bpm_curve.png", dpi=160)


def small_multiples(curves):
    fig, axes = plt.subplots(3, 4, figsize=(12, 7.5))
    for ax, stat in zip(axes.flat, SKILLS):
        s = scaled(curves[(curves.stat == stat) & (curves.method == "B")], stat)
        ax.fill_between(s.age, s.lo, s.hi, color=COLOR["B"], alpha=0.15, linewidth=0)
        ax.plot(s.age, s.value, color=COLOR["B"], linewidth=2)
        ax.axhline(0, color=INK2, linewidth=0.8)
        ax.set_title(STAT[stat], fontsize=10)
        ax.tick_params(labelsize=8)
    fig.suptitle("How each skill ages (survivorship-corrected, change vs. age 27, 80% band)",
                 x=0.01, ha="left", fontweight="bold", fontsize=12)
    fig.supxlabel("Age", color=INK2, fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "skills_small_multiples.png", dpi=160)


def backtest_chart(scores):
    base = scores[scores.model == "persistence"].set_index(["stat", "season"]).rmse
    s = scores[scores.model != "persistence"].copy()
    s["gain"] = 100 * (1 - s.rmse / s.set_index(["stat", "season"]).index.map(base))
    g = s.groupby(["stat", "model"]).gain.mean().unstack()
    g = g.loc[g["hybrid"].sort_values().index]
    fig, ax = plt.subplots(figsize=(8.5, 6.4))
    h = 0.26
    for i, m in enumerate(["marcel_naive", "hybrid", "mixed"]):
        ax.barh([y + (i - 1) * h for y in range(len(g))], g[m], height=h, color=COLOR[m], label=MODEL[m],
                edgecolor=SURFACE, linewidth=1)
    ax.set_axisbelow(True)
    ax.set_yticks(range(len(g)), [STAT[x] for x in g.index])
    ax.axvline(0, color=INK2, linewidth=0.8)
    ax.set_xlabel("% lower error than 'same as last season'\n(minutes-weighted RMSE, average of 2022-23 to 2025-26)")
    wins = int((g["hybrid"] > 0).sum())
    ax.set_title(f"Backtest: the shipped model beats 'same as last season' on {wins} of {len(g)}")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "backtest.png", dpi=160)


def risk_chart(proj, n=15, min_age=31):
    # Young players' biggest drops are regression from a career year, not aging, so only 31+ here.
    d = proj[(proj.stat == "bpm") & (proj.mp_last >= 1500) & (proj.age >= min_age)].assign(change=lambda x: x.projection - x.current)
    d = d.nsmallest(n, "change").iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 5.8))
    y = range(len(d))
    ax.hlines(y, d.lo, d.hi, color=COLOR["B"], alpha=0.35, linewidth=6)
    ax.scatter(d.current, y, s=40, facecolors=SURFACE, edgecolors=INK2, linewidths=1.5, zorder=3, label="2025-26 BPM")
    ax.scatter(d.projection, y, s=48, color=COLOR["B"], zorder=4, label="2026-27 projection (80% interval)")
    ax.set_yticks(list(y), [f"{p} ({a})" for p, a in zip(d.player, d.age)])
    fig.text(0.01, 0.01, "Age shown is age during 2026-27. Players with ≥1,500 minutes in 2025-26.", color=INK2, fontsize=8)
    ax.set_xlabel("BPM")
    ax.set_title(f"Aging risk: largest projected BPM drops for players {min_age}+ in 2026-27")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "aging_risk.png", dpi=160)


def shot_quality_chart(curves):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, stat in zip(axes, ["xfg_pct", "shotmaking"]):
        for m in ["A", "B"]:
            s = scaled(curves[(curves.stat == stat) & (curves.method == m)], stat)
            ax.fill_between(s.age, s.lo, s.hi, color=COLOR[m], alpha=0.15, linewidth=0)
            ax.plot(s.age, s.value, color=COLOR[m], linewidth=2, label=METHOD[m])
        ax.axhline(0, color=INK2, linewidth=0.8)
        ax.set_title(STAT[stat] + (" (FG% minus xFG%)" if stat == "shotmaking" else ""))
        ax.set_xlabel("Age")
    axes[0].set_ylabel("Change vs. age 27 (percentage points)")
    axes[0].legend(loc="lower right", fontsize=9)
    for ax in axes:
        ax.set_xticks(range(20, 37, 2))
    fig.suptitle("Shot-making fades after 32, and the naive curve doubles that decline", x=0.01, ha="left",
                 fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "shot_quality.png", dpi=160)


def horizons_chart(hz):
    g = hz.groupby(["stat", "horizon", "model"])[["rmse", "bias"]].mean().reset_index()
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4))
    name = {"persistence": "Same as last season", "marcel_naive": "Marcel + naive curve",
            "hybrid": "Marcel + corrected curve"}
    for m in ["persistence", "marcel_naive", "hybrid"]:
        s = g[(g.stat == "mp") & (g.model == m)]
        a.plot(s.horizon, s.rmse, marker="o", color=COLOR[m], linewidth=2, label=name[m])
    a.set_title("Minutes: projection error")
    a.set_ylabel("Minutes-weighted RMSE (minutes)")
    a.legend(fontsize=9)
    for m in ["marcel_naive", "hybrid"]:
        s = g[(g.stat == "bpm") & (g.model == m)]
        b.plot(s.horizon, s.bias, marker="o", color=COLOR[m], linewidth=2, label=name[m])
    b.axhline(0, color=INK2, linewidth=0.8)
    b.set_title("BPM: average miss (actual minus projected)")
    b.set_ylabel("BPM")
    for ax in (a, b):
        ax.set_xticks([1, 2, 3], ["1 season", "2 seasons", "3 seasons"])
        ax.set_xlabel("How far ahead")
    fig.suptitle("Projecting further ahead, the correction cuts more minutes error and BPM bias", x=0.01, ha="left",
                 fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "horizons.png", dpi=160)


def contract_chart(cr, min_age=31, n_labels=10):
    d = cr[(cr.age_2027 >= min_age) & (cr.mp_last >= 1500)].copy()
    d["owed"] = d.salary_2027_2029 / 1e6
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.scatter(d.owed, d.bpm_change_by_2029, s=36, color=COLOR["B"], alpha=0.8, edgecolors=SURFACE, linewidths=1)
    for _, r in pd.concat([d.nlargest(n_labels, "owed"), d.nsmallest(1, "bpm_change_by_2029")]).iterrows():
        ax.annotate(r.player, (r.owed, r.bpm_change_by_2029), xytext=(5, 3), textcoords="offset points",
                    fontsize=8, color=INK)
    ax.axhline(0, color=INK2, linewidth=0.8)
    ax.set_xlabel("Salary owed 2026-27 through 2028-29 ($M)")
    ax.set_ylabel("Projected BPM change, 2025-26 to 2028-29")
    ax.set_title(f"Who's paid the most through their decline (players {min_age}+)")
    fig.text(0.01, 0.01, "Players with 1,500+ minutes in 2025-26. Salaries from Basketball-Reference.",
             color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "contract_risk.png", dpi=160)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    curves = pd.read_csv("exports/aging_curves.csv")
    headline(curves)
    small_multiples(curves)
    backtest_chart(pd.read_csv("exports/backtest.csv"))
    risk_chart(pd.read_csv("exports/projections_2026_27.csv"))
    shot_quality_chart(curves)
    horizons_chart(pd.read_csv("exports/backtest_horizons.csv"))
    contract_chart(pd.read_csv("exports/contract_risk.csv"))
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
