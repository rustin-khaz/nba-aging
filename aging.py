import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.linear_model import LogisticRegression

Z80 = 1.2816


def delta_curve(t, weight="w_pair"):
    t = t[t.returned]
    d = t.groupby("age").apply(lambda g: np.average(g.delta, weights=g[weight]), include_groups=False)
    d = d.reindex(range(int(d.index.min()), int(d.index.max()) + 1), fill_value=0.0)
    level = pd.Series(np.r_[0.0, d.cumsum().values], index=np.r_[d.index.values, d.index.max() + 1])
    return pd.DataFrame({"age": level.index, "delta": d.reindex(level.index).values, "curve": (level - level.get(27, 0.0)).values})


def return_prob(t):
    X = np.column_stack([t.age, t.age**2, t.value, np.log(t.mp)])
    m = LogisticRegression(C=1e6, max_iter=1000).fit(X, t.returned)
    return pd.Series(m.predict_proba(X)[:, 1], index=t.index)


def fit_mixed(long):
    d = long[long.mp >= 500].assign(age_c=lambda x: x.age - 27)
    return smf.mixedlm("value ~ bs(age, df=4, lower_bound=18, upper_bound=46)", d, groups=d.slug, re_formula="~age_c").fit()


def project(res, who):
    fixed = np.asarray(res.predict(who[["age"]]))
    out = []
    for i, (slug, age) in enumerate(zip(who.slug, who.age)):
        z = np.array([1.0, age - 27])
        if slug in res.random_effects:
            re, cov = res.random_effects[slug].values, np.asarray(res.random_effects_cov[slug])
        else:
            re, cov = np.zeros(2), np.asarray(res.cov_re)
        proj = fixed[i] + z @ re
        sd = np.sqrt(z @ cov @ z + res.scale)
        out.append((slug, proj, proj - Z80 * sd, proj + Z80 * sd))
    return pd.DataFrame(out, columns=["slug", "proj", "lo", "hi"])


def marcel(long, target, age_delta):
    k = long.weight.median()
    last3 = long[long.season.between(target - 3, target - 1)]
    last = last3[last3.season == target - 1]
    mu = np.average(last.value, weights=last.weight)
    c = last3.season.map({target - 1: 5, target - 2: 4, target - 3: 3})
    g = last3.assign(cw=c * last3.weight, cwx=c * last3.weight * last3.value).groupby("slug")[["cw", "cwx"]].sum()
    g = g.loc[g.index.isin(last.slug)]
    base = (g.cwx + k * mu) / (g.cw + k)
    age_last = last.set_index("slug").age
    adj = age_last.map(age_delta).fillna(0.0)
    mp_last = last.set_index("slug").mp.reindex(base.index)
    return pd.DataFrame({"slug": base.index, "proj": (base + adj.reindex(base.index)).values, "mp_last": mp_last.values})


def add_intervals(proj, hist):
    """80% interval from past backtest residuals (actual - proj), separately for low/mid/high-minute players."""
    edges = hist.mp_last.quantile([0, 1 / 3, 2 / 3, 1]).to_numpy(copy=True)
    edges[0], edges[-1] = -np.inf, np.inf
    q = hist.groupby(pd.cut(hist.mp_last, edges, labels=False)).resid.quantile([0.1, 0.9]).unstack()
    b = pd.cut(proj.mp_last, edges, labels=False)
    return proj.assign(lo=proj.proj + b.map(q[0.1]).values, hi=proj.proj + b.map(q[0.9]).values)
