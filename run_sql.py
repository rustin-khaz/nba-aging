"""Rebuild nba.duckdb from data/raw by running sql/*.sql in filename order.

Also writes data/derived/panel_long.csv for the R mixed-model refit (r/mixed_weighted.R).
"""
from pathlib import Path

import duckdb

con = duckdb.connect("nba.duckdb")
for f in sorted(Path("sql").glob("*.sql")):
    con.execute(f.read_text())
    print(f"ran {f}")

Path("data/derived").mkdir(parents=True, exist_ok=True)
con.execute("COPY (SELECT slug, season, age, mp, stat, value, weight FROM panel_long) TO 'data/derived/panel_long.csv' (HEADER)")
print("wrote data/derived/panel_long.csv")
