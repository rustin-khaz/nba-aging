-- Expected make rate for every shot: the league's make rate that season from the same
-- zone and distance (distance capped at 30 ft so heaves share one bucket).
CREATE OR REPLACE TABLE shot_rates AS
SELECT season, zone, least(dist, 30) AS d, avg(made) AS xfg
FROM shots GROUP BY ALL;

CREATE OR REPLACE TABLE shot_skills AS
SELECT s.season, s.person_id, count(*) AS fga_shots,
       count(*) FILTER (s.dist <= 3) AS rim_fga,
       sum(s.made) FILTER (s.dist <= 3) AS rim_fgm,
       count(*) FILTER (s.zone IN ('Left Corner 3', 'Right Corner 3')) AS corner3a,
       sum(s.made) AS fgm_shots,
       sum(r.xfg) AS xfgm
FROM shots s JOIN shot_rates r ON r.season = s.season AND r.zone = s.zone AND r.d = least(s.dist, 30)
GROUP BY ALL;
