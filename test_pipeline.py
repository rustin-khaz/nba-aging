"""Data checks. Run after run_sql.py: .venv/bin/python -m pytest test_pipeline.py -v"""
import duckdb
import pandas as pd
import pytest

con = duckdb.connect("nba.duckdb", read_only=True)


def q(sql):
    return con.sql(sql).df()


def test_br_one_row_per_player_season():
    assert q("SELECT count(*) n FROM (SELECT slug, season FROM br GROUP BY ALL HAVING count(*) > 1)").n[0] == 0


def test_traded_player_keeps_combined_row():
    # Jimmy Butler played for MIA and GSW in 2024-25: keep the combined 2TM row, not either team's.
    assert q("SELECT team FROM br WHERE slug = 'butleji01' AND season = 2025").team.tolist() == ["2TM"]


def test_types_and_ranges():
    r = q("SELECT min(age) lo, max(age) hi, min(season) s0, max(season) s1, count(*) FILTER (mp IS NULL) n_null FROM br")
    assert 18 <= r.lo[0] and r.hi[0] <= 45
    assert (r.s0[0], r.s1[0]) == (2001, 2026)
    assert r.n_null[0] == 0


def test_chris_paul_rookie_age():
    assert q("SELECT age FROM br WHERE slug = 'paulch01' AND season = 2006").age.tolist() == [20]


def test_crosswalk_covers_99pct_of_minutes():
    r = q("""SELECT sum(mp) FILTER (c.person_id IS NOT NULL) / sum(mp) AS share
             FROM br LEFT JOIN crosswalk c USING (slug, season) WHERE mp >= 250""")
    unmatched = q("""SELECT br.slug, br.player, br.season, br.mp FROM br
                     LEFT JOIN crosswalk c USING (slug, season)
                     WHERE mp >= 250 AND c.person_id IS NULL ORDER BY mp DESC LIMIT 15""")
    print(unmatched.to_string())
    assert r.share[0] >= 0.99


def test_crosswalk_is_one_to_one_per_season():
    assert q("SELECT count(*) n FROM (SELECT season, person_id FROM crosswalk GROUP BY ALL HAVING count(*) > 1)").n[0] == 0


def test_rim_share_is_a_share():
    r = q("SELECT min(rim_share) lo, max(rim_share) hi, count(*) FILTER (rim_share IS NOT NULL) n FROM panel WHERE mp >= 250")
    assert 0 <= r.lo[0] and r.hi[0] <= 1 and r.n[0] > 8000


def test_panel_long_filters():
    r = q("SELECT min(mp) mp, min(weight) w, count(*) FILTER (value IS NULL) n_null, count(DISTINCT stat) k FROM panel_long")
    assert r.mp[0] >= 250 and r.w[0] > 0 and r.n_null[0] == 0 and r.k[0] == 12


def test_transitions_match_independent_pandas_recompute():
    t = q("SELECT slug, stat, season, returned, delta FROM transitions WHERE stat = 'bpm'")
    long = q("SELECT slug, season, value FROM panel_long WHERE stat = 'bpm'")
    nxt = long.assign(season=long.season - 1).rename(columns={"value": "next_value"})
    m = long.merge(nxt, on=["slug", "season"], how="left").assign(expected=lambda d: d.next_value - d.value)
    m = m[m.season < long.season.max()].merge(t, on=["slug", "season"])
    assert len(m) == len(t)
    assert (m.returned == m.next_value.notna()).all()
    pd.testing.assert_series_equal(m.delta, m.expected, check_names=False)


def test_no_transition_out_of_final_season():
    # We can't know yet who "returns" after 2025-26, so those rows must not exist.
    assert q("SELECT count(*) n FROM transitions WHERE season = 2026").n[0] == 0
