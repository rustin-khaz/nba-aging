CREATE OR REPLACE TABLE panel AS
SELECT br.*, s.rim_fga, s.fga_shots,
       s.xfgm / nullif(s.fga_shots, 0) AS xfg_pct,
       (s.fgm_shots - s.xfgm) / nullif(s.fga_shots, 0) AS shotmaking,
       s.rim_fgm / nullif(s.rim_fga, 0) AS rim_fg_pct,
       s.rim_fga / nullif(s.fga_shots, 0) AS rim_share,
       s.corner3a / nullif(s.fga_shots, 0) AS corner3_share,
       fg3m / nullif(fg3a, 0) AS fg3_pct, ftm / nullif(fta, 0) AS ft_pct
FROM br LEFT JOIN crosswalk USING (slug, season)
        LEFT JOIN shot_skills s USING (person_id, season);

CREATE OR REPLACE TABLE panel_long AS
WITH l AS (
    SELECT slug, player, season, age, mp, s.stat, s.value, s.weight
    FROM panel, (VALUES
        ('bpm', bpm, mp), ('fg3_pct', fg3_pct, fg3a), ('fg3a_rate', fg3a_rate, fga),
        ('ft_pct', ft_pct, fta), ('rim_fg_pct', rim_fg_pct, rim_fga), ('rim_share', rim_share, fga),
        ('ast_pct', ast_pct, mp), ('tov_pct', tov_pct, mp), ('drb_pct', drb_pct, mp),
        ('stl_pct', stl_pct, mp), ('blk_pct', blk_pct, mp), ('mp', mp, 1),
        ('xfg_pct', xfg_pct, fga_shots), ('shotmaking', shotmaking, fga_shots)
    ) s(stat, value, weight)
)
SELECT * FROM l WHERE mp >= 250 AND value IS NOT NULL AND weight > 0;

CREATE OR REPLACE TABLE transitions AS
WITH w AS (
    SELECT *, lead(season) OVER p AS next_season, lead(value) OVER p AS next_value, lead(weight) OVER p AS next_weight
    FROM panel_long WINDOW p AS (PARTITION BY slug, stat ORDER BY season)
)
SELECT slug, player, stat, season, age, mp, value, weight,
       coalesce(next_season = season + 1, false) AS returned,
       CASE WHEN next_season = season + 1 THEN next_value - value END AS delta,
       CASE WHEN next_season = season + 1 THEN 2 / (1 / weight + 1 / next_weight) END AS w_pair
FROM w WHERE season < (SELECT max(season) FROM panel_long);
