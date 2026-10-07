"""Fetch raw data to data/raw/. Resumable: files already on disk are skipped.

Season convention everywhere in this project: `season` = the year the season ENDS
(2026 = 2025-26). shufinskiy names files by the year the season STARTS, so +1.
"""
import io
import sys
import tarfile
import time
from pathlib import Path

import pandas as pd
import requests

SEASONS = range(2001, 2027)
RAW = Path("data/raw")
HEADERS = {"User-Agent": "Mozilla/5.0 (personal research project)"}
BR_TABLES = {"advanced": "advanced", "totals": "totals_stats"}


def fetch_br(season: int, kind: str) -> None:
    out = RAW / "br" / f"{kind}_{season}.parquet"
    if out.exists():
        return
    url = f"https://www.basketball-reference.com/leagues/NBA_{season}_{kind}.html"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()  # a 429 means BR rate-limited us: wait an hour, rerun
    r.encoding = "utf-8"  # BR omits the charset header; requests would guess Latin-1 and mangle "Jokić"
    df = pd.read_html(io.StringIO(r.text), attrs={"id": BR_TABLES[kind]}, extract_links="body")[0]
    # Each cell is (text, link). Keep text; pull the player slug out of the Player link.
    slug = df["Player"].map(lambda c: c[1].rsplit("/", 1)[-1].removesuffix(".html") if c[1] else None)
    df = df.map(lambda c: c[0])
    df.columns = [str(c) for c in df.columns]
    df.insert(0, "slug", slug)
    df.insert(1, "season", season)
    df = df[df["slug"].notna()]  # drops "League Average" and repeated header rows
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    time.sleep(4)  # BR allows ~20 requests/minute


def fetch_contracts() -> None:
    """Current contracts (salary by future season) from BR's league-wide contracts page."""
    out = RAW / "br" / "contracts.parquet"
    if out.exists():
        return
    r = requests.get("https://www.basketball-reference.com/contracts/players.html", headers=HEADERS, timeout=30)
    r.raise_for_status()
    r.encoding = "utf-8"
    df = pd.read_html(io.StringIO(r.text), attrs={"id": "player-contracts"}, extract_links="body", header=[0, 1])[0]
    df.columns = [b if a.startswith("Unnamed") else f"salary_{int(b[:4]) + 1}" for a, b in df.columns]  # 2026-27 -> 2027
    slug = df["Player"].map(lambda c: c[1].rsplit("/", 1)[-1].removesuffix(".html") if c[1] else None)
    df = df.map(lambda c: c[0])
    money = [c for c in df.columns if c.startswith("salary_")] + ["Guaranteed"]
    df[money] = df[money].apply(lambda col: pd.to_numeric(col.str.replace(r"[$,]", "", regex=True), errors="coerce"))
    df.insert(0, "slug", slug)
    df = df[df["slug"].notna()].drop(columns="Rk").rename(columns={"Player": "player", "Tm": "team", "Guaranteed": "guaranteed"})
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    time.sleep(4)


def fetch_shots(season: int) -> None:
    out = RAW / "shots" / f"shots_{season}.parquet"
    if out.exists():
        return
    url = f"https://github.com/shufinskiy/nba_data/raw/main/datasets/shotdetail_{season - 1}.tar.xz"
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with tarfile.open(fileobj=io.BytesIO(r.content), mode="r:xz") as tar:
        member = next(m for m in tar.getmembers() if m.name.endswith(".csv"))
        df = pd.read_csv(tar.extractfile(member))
    df.insert(0, "season", season)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)


if __name__ == "__main__":
    seasons = [int(s) for s in sys.argv[1:]] or SEASONS
    for s in seasons:
        for kind in BR_TABLES:
            fetch_br(s, kind)
        fetch_shots(s)
        print(f"{s} done", flush=True)
    fetch_contracts()
    print("contracts done", flush=True)
