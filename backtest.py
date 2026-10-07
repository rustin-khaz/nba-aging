import numpy as np
import pandas as pd

from aging import add_intervals, delta_curve, fit_mixed, marcel, project, return_prob

TARGETS = range(2022, 2027)  # 2022 only seeds the interval residuals; scored seasons are 2023-2026


def fold(long, trans, T):
    """Everything a model may see when projecting season T."""
    train = long[long.season < T]
    train_trans = trans[trans.season <= T - 2]  # a transition out of T-1 would reveal who played in T
    truth = long[(long.season == T) & long.slug.isin(long[long.season == T - 1].slug)]
    return train, train_trans, truth


def age_deltas(t, ipw):
    t = t.copy()
    t["w"] = t.w_pair / return_prob(t) if ipw else t.w_pair
    return delta_curve(t, "w").set_index("age").delta


def predict_fold(long, trans, T):
    train, tt, truth = fold(long, trans, T)
    preds = {
        "persistence": train[train.season == T - 1][["slug", "value", "mp"]].rename(columns={"value": "proj", "mp": "mp_last"}),
        "marcel_naive": marcel(train, T, age_deltas(tt, ipw=False)),
        "hybrid": marcel(train, T, age_deltas(tt, ipw=True)),
        "mixed": project(fit_mixed(train), truth[["slug", "age"]]),
    }
    out = [p.assign(model=m) for m, p in preds.items()]
    return pd.concat(out).merge(truth[["slug", "value", "mp"]], on="slug").assign(season=T, resid=lambda d: d.value - d.proj)


def backtest_horizons(long, trans, horizons=(1, 2, 3), targets=range(2023, 2027)):
    """Score 1-, 2- and 3-season-ahead projections on the same target seasons.

    Projecting season S from h seasons out may only use data through S - h,
    and transitions whose second season is S - h or earlier.
    """
    rows, resid = [], []
    for h in horizons:
        for S in targets:
            base = S - h
            train = long[long.season <= base]
            tt = trans[trans.season <= base - 1]
            truth = long[(long.season == S) & long.slug.isin(long[long.season == base].slug)]
            preds = {
                "persistence": train[train.season == base][["slug", "value"]].rename(columns={"value": "proj"}),
                "marcel_naive": marcel(train, S, age_deltas(tt, ipw=False), horizon=h),
                "hybrid": marcel(train, S, age_deltas(tt, ipw=True), horizon=h),
            }
            for m, p in preds.items():
                d = p.merge(truth[["slug", "value", "mp"]], on="slug")
                rows.append({"horizon": h, "season": S, "model": m, "n": len(d),
                             "rmse": np.sqrt(np.average((d.value - d.proj) ** 2, weights=d.mp)),
                             "bias": np.average(d.value - d.proj, weights=d.mp)})
                if m == "hybrid":
                    resid.append(d.assign(horizon=h, season=S, resid=d.value - d.proj))
    return pd.DataFrame(rows), pd.concat(resid)


def backtest(long, trans):
    preds = pd.concat(predict_fold(long, trans, T) for T in TARGETS)
    h = preds[preds.model == "hybrid"]
    covered = [add_intervals(h[h.season == T], h[h.season < T]) for T in TARGETS[1:]]
    cov = pd.concat(covered).assign(hit=lambda d: (d.value >= d.lo) & (d.value <= d.hi)).groupby("season").hit.mean()
    s = preds[preds.season >= TARGETS[1]]
    scores = s.groupby(["season", "model"]).apply(lambda d: pd.Series({
        "rmse": np.sqrt(np.average(d.resid**2, weights=d.mp)),
        "mae": np.average(d.resid.abs(), weights=d.mp)}), include_groups=False).reset_index()
    scores["coverage"] = np.where(scores.model == "hybrid", scores.season.map(cov), np.nan)
    return scores, preds

