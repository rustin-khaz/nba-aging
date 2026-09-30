CREATE OR REPLACE TABLE shot_skills AS
SELECT season, person_id, count(*) AS fga_shots,
       count(*) FILTER (dist <= 3) AS rim_fga,
       sum(made) FILTER (dist <= 3) AS rim_fgm,
       count(*) FILTER (zone IN ('Left Corner 3', 'Right Corner 3')) AS corner3a
FROM shots GROUP BY ALL;
