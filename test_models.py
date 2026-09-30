"""Model checks on synthetic data where the true aging curve is known.

If your code can't recover a curve we planted, it can't be trusted on real data.
Run: .venv/bin/python -m pytest test_models.py -v
"""
import numpy as np
import pandas as pd

from aging import add_intervals, delta_curve, fit_mixed, marcel, project, return_prob
from backtest import fold


def true_curve(age):
    return -0.03 * (age - 27) ** 2


def synth(n=1500, seed=0):
    """Players with their own level and aging slope. Low performers drop out."""
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(n):
        age, season = int(rng.integers(19, 24)), int(rng.integers(2001, 2016))
        u0, u1 = rng.normal(0, 2), rng.normal(0, 0.15)
        while age <= 38:
            y = true_curve(age) + u0 + u1 * (age - 27) + rng.normal(0, 1)
            rows.append((f"p{p}", season, age, y, 1500.0))
            if rng.random() > 1 / (1 + np.exp(-(1.0 + 0.8 * y - 0.1 * (age - 27)))):
                break
            age, season = age + 1, season + 1
    long = pd.DataFrame(rows, columns=["slug", "season", "age", "value", "mp"])
    return long.assign(weight=long.mp)


def transitions(long):
    t = long.sort_values(["slug", "season"]).copy()
    nxt = t.groupby("slug").value.shift(-1)
    t["returned"] = nxt.notna()
    t["delta"] = nxt - t.value
    t["w_pair"] = 2 / (1 / t.weight + 1 / t.groupby("slug").weight.shift(-1))
    return t


def curve_rmse(curve):
    c = curve.set_index("age").curve.reindex(range(22, 35))
    return float(np.sqrt(((c - (true_curve(c.index) - true_curve(27))) ** 2).mean()))


def test_ipw_beats_naive_on_planted_survivorship():
    t = transitions(synth())
    naive = delta_curve(t, "w_pair")
    t["w_ipw"] = t.w_pair / return_prob(t)
    ipw = delta_curve(t, "w_ipw")
    assert curve_rmse(ipw) < curve_rmse(naive)
    assert curve_rmse(ipw) < 0.3


def test_curve_is_zero_at_27():
    t = transitions(synth(300))
    c = delta_curve(t, "w_pair").set_index("age").curve
    assert c[27] == 0


def test_mixed_recovers_curve_and_intervals_are_calibrated():
    # Calendar cutoff, like the real backtest: fit on seasons < T, project T for players seen in T-1.
    long, T = synth(1500, seed=1), 2014
    train = long[long.season < T]
    test = long[(long.season == T) & long.slug.isin(train[train.season == T - 1].slug)]
    res = fit_mixed(train)
    ages = pd.DataFrame({"age": range(22, 35)})
    fixed = np.asarray(res.predict(ages)) - float(np.asarray(res.predict(pd.DataFrame({"age": [27]})))[0])
    assert np.sqrt(((fixed - (true_curve(ages.age) - true_curve(27))) ** 2).mean()) < 0.4
    p = project(res, test[["slug", "age"]]).merge(test[["slug", "value"]], on="slug")
    coverage = ((p.value >= p.lo) & (p.value <= p.hi)).mean()
    assert 0.72 <= coverage <= 0.88, coverage


def test_unknown_player_gets_population_curve_with_wider_interval():
    res = fit_mixed(synth(300, seed=2))
    p = project(res, pd.DataFrame({"slug": ["nobody"], "age": [27]}))
    known = project(res, pd.DataFrame({"slug": [next(iter(res.random_effects))], "age": [27]}))
    assert (p.hi - p.lo).iloc[0] > (known.hi - known.lo).iloc[0]


def test_marcel_hand_example():
    # One player, three seasons. League (season 2) has only this player plus one other.
    long = pd.DataFrame({
        "slug": ["a", "a", "a", "b"],
        "season": [0, 1, 2, 2],
        "age": [25, 26, 27, 30],
        "value": [1.0, 2.0, 3.0, 0.0],
        "weight": [1000.0, 1000.0, 1000.0, 1000.0],
        "mp": [1000.0, 1000.0, 1000.0, 1000.0],
    })
    # k = median weight = 1000; league mean (season 2) = (3 + 0) / 2 = 1.5
    # a: (5*3 + 4*2 + 3*1)*1000 = 26000 ; weights 12000 ; + 1000*1.5 -> 27500 / 13000
    age_delta = pd.Series({27: -0.1, 30: -0.2})
    out = marcel(long, target=3, age_delta=age_delta).set_index("slug").proj
    assert abs(out["a"] - (27500 / 13000 - 0.1)) < 1e-9
    assert abs(out["b"] - ((0 + 1500) / (5000 + 1000) - 0.2)) < 1e-9


def test_intervals_cover_80pct_and_widen_for_low_minutes():
    rng = np.random.default_rng(3)
    def draw(n):
        mp = rng.uniform(250, 3000, n)
        return pd.DataFrame({"proj": 0.0, "mp_last": mp, "resid": rng.normal(0, 60 / np.sqrt(mp))})
    hist, new = draw(4000), draw(4000)
    out = add_intervals(new[["proj", "mp_last"]], hist)
    assert 0.77 <= ((new.resid >= out.lo) & (new.resid <= out.hi)).mean() <= 0.83
    width = out.hi - out.lo
    assert width[new.mp_last < 800].mean() > width[new.mp_last > 2200].mean()


def test_backtest_fold_cannot_see_the_future():
    long = synth(400, seed=4)
    trans = transitions(long)
    trans = trans[trans.season < long.season.max()]
    for T in range(2010, 2016):
        train, train_trans, truth = fold(long, trans, T)
        assert train.season.max() < T
        assert (train_trans.season + 1).max() < T  # the "next season" of every transition is in the past
        assert (truth.season == T).all()
