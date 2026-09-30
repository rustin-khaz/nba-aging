-- One row per (slug, season). Traded players keep the combined 2TM/3TM/... row.
CREATE OR REPLACE TABLE br AS
SELECT
    slug,
    season,
    a.Player                        AS player,
    TRY_CAST(a.Age      AS INT)     AS age,
    Team                            AS team,
    TRY_CAST(a.MP       AS INT)     AS mp,
    TRY_CAST(a.BPM      AS DOUBLE)  AS bpm,
    TRY_CAST(a."3PAr"   AS DOUBLE)  AS fg3a_rate,
    TRY_CAST(a."AST%"   AS DOUBLE)  AS ast_pct,
    TRY_CAST(a."TOV%"   AS DOUBLE)  AS tov_pct,
    TRY_CAST(a."DRB%"   AS DOUBLE)  AS drb_pct,
    TRY_CAST(a."STL%"   AS DOUBLE)  AS stl_pct,
    TRY_CAST(a."BLK%"   AS DOUBLE)  AS blk_pct,
    TRY_CAST(a."USG%"   AS DOUBLE)  AS usg_pct,
    TRY_CAST(t.FGA      AS INT)     AS fga,
    TRY_CAST(t."3P"     AS INT)     AS fg3m,
    TRY_CAST(t."3PA"    AS INT)     AS fg3a,
    TRY_CAST(t.FT       AS INT)     AS ftm,
    TRY_CAST(t.FTA      AS INT)     AS fta
FROM 'data/raw/br/advanced_*.parquet' a
JOIN 'data/raw/br/totals_*.parquet' t USING (slug, season, Team)
QUALIFY row_number() OVER (PARTITION BY slug, season ORDER BY Team LIKE '%TM' DESC) = 1;

CREATE OR REPLACE TABLE shots AS
SELECT
    season,
    PLAYER_ID      AS person_id,
    PLAYER_NAME    AS player_name,
    SHOT_DISTANCE  AS dist,
    SHOT_ZONE_BASIC AS zone,
    SHOT_MADE_FLAG AS made
FROM 'data/raw/shots/shots_*.parquet';
