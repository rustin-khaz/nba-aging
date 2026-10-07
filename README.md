# How NBA Players Age, and What to Expect in 2026-27

I built aging curves for 12 basketball skills across 26 seasons (2000-01 through 2025-26), corrected them for survivorship bias, and used them to project every player's 2026-27 season with 80% intervals. Then I backtested the projections against four seasons that already happened, to see whether any of it actually works.

Stack: Python (pandas, statsmodels, scikit-learn), SQL in DuckDB, pytest, and CSV exports shaped for Tableau.
Data: 12,810 player-seasons from Basketball-Reference and 5.2M shots from NBA shot-chart data.

![BPM aging curve: naive vs survivorship-corrected](docs/img/bpm_curve.png)

## The main finding

The usual way to build an aging curve is the delta method. You take every player who played two seasons in a row, look at how much he changed, and average those changes at each age. The catch is who gets that second season. A player usually sticks around because he just had a good year, and some of that good year was luck. The next season he drifts back down, and the delta method books that drift as aging.

To fix it, I modeled each player's chance of coming back and reweighted the season-to-season changes by the inverse of that probability (inverse probability weighting). By age 34, the naive curve has players down 2.8 BPM from their age-27 level. The corrected curve has them down 1.9. So the standard method overstates late-career decline by about 45%.

## How each skill ages

![Aging curves for 12 skills](docs/img/skills_small_multiples.png)

Shooting holds up well. 3P% and FT% stay close to their peak into the early 30s.

Players take more threes every single year of their careers, and fewer shots at the rim.

Playmaking (AST%), minutes and overall impact (BPM) peak around 26 or 27 and then decline.

Steals and blocks belong to young players. Both peak before 25 and slide from there.

## Does it predict anything? Backtest, 2022-23 to 2025-26

For each test season, I fit every model only on the seasons before it and then scored it against what really happened. The table is minutes-weighted RMSE averaged over the four seasons, with the best result in each row in bold.

| Skill | Same as last season | Mixed model | Marcel + naive curve | Marcel + corrected curve | 80% interval coverage |
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

A few things stood out.

The intervals are honest. The 80% intervals caught the real outcome 78.5% of the time overall, and somewhere between 76% and 81% for every skill.

For a one-year forecast, the survivorship correction mostly matters for minutes. It cut minutes error from 550 to 531 and barely touched the rate stats. That makes sense once you think about it, because whether a player gets another season depends mostly on how much he plays.

The mixed-effects model lost to Marcel on all 12 skills. Its player effect averages over a whole career, while Marcel leans on the most recent seasons, and recent seasons turned out to matter more. So I went with the simpler model.

For shot profile (3PA rate and rim shot share), plain "same as last season" beat every model I tried. Shot selection is a stable habit, and pulling it toward the league average just adds error.

## Aging risk for 2026-27

![Largest projected BPM drops, players 31+](docs/img/aging_risk.png)

Projections for every player and every skill are in [`exports/projections_2026_27.csv`](exports/projections_2026_27.csv).

## How it works

1. Data layer in SQL. The files in [`sql/`](sql) turn the raw Basketball-Reference tables and shot logs into one player-season panel.
   - Players traded mid-season keep only their combined `2TM`/`3TM` row.
   - Basketball-Reference IDs get matched to NBA IDs by normalized name. That covers 99.98% of minutes for players with 250+ minutes, plus [9 manual overrides](data/manual/id_overrides.csv) for nicknames the name match misses.
   - The 12 stats get unpivoted into long format, and season-to-season transitions come from `LEAD()` window functions.
2. Method A, the naive curve: the weighted average change at each age, summed up and anchored at 27.
3. Method B, the corrected curve: a logistic regression estimates `P(return next season | age, stat, minutes)`, and each transition gets weighted by `1 / P`.
4. Method C, a mixed-effects model (`stat ~ spline(age) + (1 + age | player)` in statsmodels), mostly there as a comparison.
5. The model I actually use: Marcel (a 5/4/3 weighted average of the last three seasons, pulled toward league average) plus the age adjustment from curve B. The 80% intervals come from the model's own past backtest errors, computed separately for low-, mid- and high-minute players.
6. No leakage. When a fold projects season T, it can only use transitions whose second season is before T, since a transition out of T-1 would give away who played in T.

The checks live in [`test_pipeline.py`](test_pipeline.py) (10 data checks) and [`test_models.py`](test_models.py) (7 model checks). The model checks build fake players with an aging curve I chose and survivorship baked in on purpose, then make sure the code gets that curve back.

## Limitations

IPW can only correct for things I can see: age, the stat itself, and minutes. If a player declines for a reason nobody measured, like an injury nobody reported, the correction misses it.

BPM is a box-score estimate of impact. It isn't a plus-minus based measure like RAPM.

A player who skips a season (injury, playing overseas) counts as not coming back.

The correction changes the shape of the curve a lot more than it changes one-year forecasts. Where it really pays off is multi-year questions, like what a 30-year-old will look like at 34.

## Running it (Python 3.12)

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python download.py        # about 10 min, resumable; 55 MB into data/raw/
.venv/bin/python run_sql.py         # builds nba.duckdb
.venv/bin/python -m pytest          # 17 checks
.venv/bin/python export.py          # about 6 min; writes exports/*.csv
.venv/bin/python charts.py          # writes docs/img/*.png
```

`exports/` has three CSVs set up for Tableau: `aging_curves.csv`, `projections_2026_27.csv` and `backtest.csv`. There's a shorter, non-technical summary in [`memo.md`](memo.md).

Things I'd add next: contract and salary data, a weighted refit in R's `lme4`, and a shot-quality (xFG%) piece.

Data comes from [Basketball-Reference](https://www.basketball-reference.com) and [shufinskiy/nba_data](https://github.com/shufinskiy/nba_data).
