"""Fit everything on the full data and write exports/*.csv (the files Tableau and charts.py read).

Run after run_sql.py. Takes a few minutes: 72 mixed-model fits plus bootstraps.
"""
import warnings

import duckdb
import numpy as np
import pandas as pd

from aging import add_intervals, delta_curve, fit_mixed, marcel, return_prob
from backtest import age_deltas, backtest

warnings.filterwarnings("ignore")  # statsmodels ConvergenceWarnings are expected for a few stats

N_BOOT = 200
MIN_PAIRS = 50  # don't draw a curve point from fewer transitions than this
TARGET = 2027


def curve_ab(t, ipw):
    t = t.copy()
    t["w"] = t.w_pair / return_prob(t) if ipw else t.w_pair
    return delta_curve(t, "w").set_index("age").curve


def bootstrap_band(t, ipw, rng):
    """80% band for a delta curve: resample whole players, not rows."""
    groups = t.groupby("slug").indices
    slugs = np.array(list(groups))
    curves = []
    for _ in range(N_BOOT):
        idx = np.concatenate([groups[s] for s in rng.choice(slugs, len(slugs))])
        curves.append(curve_ab(t.iloc[idx], ipw))
    c = pd.concat(curves, axis=1)
    return c.quantile(0.1, axis=1), c.quantile(0.9, axis=1)


def main():
    con = duckdb.connect("nba.duckdb", read_only=True)
    stats = con.sql("SELECT DISTINCT stat FROM panel_long ORDER BY stat").df().stat
    rng = np.random.default_rng(0)
    curves, projections, scores_all = [], [], []

    for stat in stats:
        print(stat, flush=True)
        long = con.sql(f"SELECT * FROM panel_long WHERE stat = '{stat}'").df()
        trans = con.sql(f"SELECT * FROM transitions WHERE stat = '{stat}'").df()
        n_pairs = trans[trans.returned].groupby("age").size()
        ages = n_pairs[n_pairs >= MIN_PAIRS].index

        for method, ipw in [("A", False), ("B", True)]:
            value = curve_ab(trans, ipw)
            lo, hi = bootstrap_band(trans, ipw, rng)
            curves.append(pd.DataFrame({"stat": stat, "age": ages, "method": method,
                                        "value": value.reindex(ages).values,
                                        "lo": lo.reindex(ages).values, "hi": hi.reindex(ages).values}))

        res = fit_mixed(long)
        grid = pd.DataFrame({"age": ages})
        fixed = np.asarray(res.predict(grid)) - float(np.asarray(res.predict(pd.DataFrame({"age": [27]})))[0])
        curves.append(pd.DataFrame({"stat": stat, "age": ages, "method": "C", "value": fixed, "lo": np.nan, "hi": np.nan}))

        scores, preds = backtest(long, trans)
        scores_all.append(scores.assign(stat=stat))

        hist = preds[preds.model == "hybrid"]
        proj = add_intervals(marcel(long, TARGET, age_deltas(trans, ipw=True)), hist)
        last = long[long.season == TARGET - 1][["slug", "player", "age", "value"]]
        projections.append(proj.merge(last, on="slug").assign(stat=stat, age=lambda d: d.age + 1)
                           .rename(columns={"value": "current", "proj": "projection"}))

    curves = pd.concat(curves)
    projections = pd.concat(projections)
    teams = con.sql(f"SELECT slug, team FROM br WHERE season = {TARGET - 1}").df()
    projections = projections.merge(teams, on="slug")[
        ["slug", "player", "team", "age", "stat", "current", "projection", "lo", "hi", "mp_last"]]
    scores = pd.concat(scores_all)[["stat", "season", "model", "rmse", "mae", "coverage"]]

    at27 = curves[curves.age == 27]
    assert (at27.value.abs() < 1e-9).all(), "every curve must be 0 at age 27"
    assert ((projections.lo <= projections.projection) & (projections.projection <= projections.hi)).all()
    assert len(scores) == len(stats) * 4 * 4, len(scores)

    curves.to_csv("exports/aging_curves.csv", index=False)
    projections.to_csv("exports/projections_2026_27.csv", index=False)
    scores.to_csv("exports/backtest.csv", index=False)
    print(f"wrote {len(curves)} curve points, {len(projections)} projections, {len(scores)} backtest rows")


if __name__ == "__main__":
    main()
