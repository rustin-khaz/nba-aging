"""Rebuild nba.duckdb from data/raw by running sql/*.sql in filename order."""
from pathlib import Path

import duckdb

con = duckdb.connect("nba.duckdb")
for f in sorted(Path("sql").glob("*.sql")):
    con.execute(f.read_text())
    print(f"ran {f}")
