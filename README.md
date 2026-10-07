# How NBA Players Age, and What to Expect in 2026-27

Aging curves for 12 basketball skills over 26 seasons (2000-01 to 2025-26), corrected for survivorship bias, plus 2026-27 projections with 80% intervals that were checked against four seasons of real outcomes.

**Stack:** Python (pandas, statsmodels, scikit-learn) · SQL (DuckDB) · Tableau-ready CSVs · pytest
**Data:** 12,810 player-seasons from Basketball-Reference, 5.2M shots from NBA shot-chart data

![BPM aging curve: naive vs survivorship-corrected](docs/img/bpm_curve.png)

## Main finding

The standard way to build an aging curve is the **delta method**: average each player's change from one season to the next at every age. It uses only players who played both seasons, and whether a player gets that next season depends on how well he played this season. So the players who stay in the league are disproportionately coming off good, partly lucky years, and next season they regress. The delta method counts that regression as aging.

Reweighting each player by his modeled chance of returning (inverse probability weighting) removes most of that effect. **By age 34 the naive curve shows a −2.8 BPM decline from age 27. The corrected curve shows −1.9.** The naive method overstates late-career decline by about 45%.

## How every skill ages

![Aging curves for 12 skills](docs/img/skills_small_multiples.png)

- Shooting holds up with age: 3P% and FT% stay near peak into the early 30s.
- Players take more threes every year of their career (3PA rate climbs steadily) and fewer shots at the rim.
- Playmaking (AST%), minutes, and overall impact (BPM) peak at 26–27, then decline.
- Steals and blocks are young players' skills: both peak before 25 and decline from there.

## Does it predict? Backtest, 2022-23 to 2025-26

For each season, every model is fit only on earlier seasons and then scored against what actually happened. The table shows minutes-weighted RMSE averaged over four seasons; **bold** is the best in each row.

| Skill | Same as last season | Mixed model | Marcel + naive curve | **Marcel + corrected curve** | 80% interval coverage |
|---|---|---|---|---|---|
| BPM | 1.860 | 1.705 | **1.641** | 1.646 | 78% |
| 3P% | 0.095 | 0.077 | **0.077** | 0.077 | 79% |
| 3PA rate | **0.077** | 0.093 | 0.082 | 0.082 | 78% |
| FT% | 0.072 | 0.060 | **0.059** | 0.059 | 79% |
| Rim FG% | 0.069 | 0.062 | 0.058 | **0.058** | 79% |
| Rim shot share | **0.065** | 0.073 | 0.068 | 0.068 | 79% |
| AST% | 4.120 | 4.180 | **3.920** | 3.921 | 80% |
| TOV% | 2.292 | 2.109 | **2.023** | 2.025 | 81% |
| DRB% | 2.400 | 2.486 | **2.350** | 2.353 | 76% |
| STL% | 0.408 | 0.375 | 0.366 | **0.366** | 77% |
| BLK% | 0.719 | 0.660 | 0.648 | **0.648** | 77% |
| Minutes | 587 | 534 | 550 | **531** | 78% |

![Backtest: error reduction vs. persistence](docs/img/backtest.png)

What the backtest shows:

- **The intervals are well calibrated.** The 80% intervals contained the actual outcome 78.5% of the time overall, and between 76% and 81% for every skill.
- **For one-year forecasts, the correction matters most for minutes.** It cut minutes error from 550 to 531 and made almost no difference for the rate stats. That fits the mechanism: whether a player gets another season depends mostly on his minutes.
- **The mixed-effects model lost to Marcel** on all 12 skills. A player's random effect averages over his whole career, while Marcel weights recent seasons most heavily. I shipped the simpler model that won.
- **For shot profile, "same as last season" beats every model** (3PA rate and rim shot share). Shot selection is a stable trait, and pulling it toward the league average only adds error.

## Aging risk for 2026-27

![Largest projected BPM drops, players 31+](docs/img/aging_risk.png)

The full projections for every player and skill are in [`exports/projections_2026_27.csv`](exports/projections_2026_27.csv).

## Method

1. **Data layer (SQL).** [`sql/`](sql) turns raw Basketball-Reference tables and shot logs into a player-season panel.
   - For players traded mid-season, only the combined `2TM`/`3TM` row is kept.
   - Basketball-Reference player IDs are matched to NBA IDs by normalized name, covering 99.98% of minutes, with [9 manual overrides](data/manual/id_overrides.csv) for nicknames.
   - The 12 stats are unpivoted into long format, and season-to-season transitions are built with `LEAD()` window functions.
2. **Method A, naive curve.** Weighted mean change at each age, cumulatively summed and anchored at age 27.
3. **Method B, corrected curve.** A logistic regression predicts `P(return next season | age, stat, minutes)`, and each transition is reweighted by `1 / P`.
4. **Method C, mixed-effects model.** `stat ~ spline(age) + (1 + age | player)`, fit with statsmodels. This is the comparison model.
5. **Shipped model.** Marcel (a weighted 5/4/3 average of the last three seasons, pulled toward the league average) plus curve B's age adjustment. The 80% intervals come from the model's past backtest errors, calculated separately for low-, mid- and high-minute players.
6. **No leakage.** A fold that projects season T may only use transitions whose *second* season is before T. A transition out of T−1 would reveal who played in T.

Checks: [`test_pipeline.py`](test_pipeline.py) (10 data checks) and [`test_models.py`](test_models.py) (7 model checks). The model checks use simulated players with a known aging curve and deliberately built-in survivorship, and confirm the code recovers that curve.

## Limitations

- IPW only corrects for selection on things we observe (age, the stat, minutes). A decline nobody measured, such as an unreported injury, isn't captured.
- BPM is a box-score estimate of impact, not a plus-minus measure like RAPM.
- A player who skips a season (injury, playing overseas) counts as not returning.
- The survivorship correction reshapes the curve much more than it changes one-year forecasts. Its real value is in multi-year questions, such as how a 30-year-old will look at 34.

## Run it (Python 3.12)

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python download.py        # ~10 min, resumable; 55 MB into data/raw/
.venv/bin/python run_sql.py         # builds nba.duckdb
.venv/bin/python -m pytest          # 17 checks
.venv/bin/python export.py          # ~6 min; writes exports/*.csv
.venv/bin/python charts.py          # writes docs/img/*.png
```

`exports/` holds three CSVs shaped for Tableau: `aging_curves.csv`, `projections_2026_27.csv` and `backtest.csv`. A non-technical summary is in [`memo.md`](memo.md).

**Next steps:** a contract/salary layer, a weighted refit in R's `lme4`, and a shot-quality (xFG%) component.

Data: [Basketball-Reference](https://www.basketball-reference.com), [shufinskiy/nba_data](https://github.com/shufinskiy/nba_data).
