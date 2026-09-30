CREATE OR REPLACE MACRO norm_name(n) AS
    trim(regexp_replace(regexp_replace(lower(strip_accents(n)), '[.''’-]', '', 'g'), '\s+(jr|sr|ii|iii|iv)$', ''));

CREATE OR REPLACE TABLE crosswalk AS
WITH b AS (SELECT slug, season, norm_name(player) AS nm FROM br
           QUALIFY count(*) OVER (PARTITION BY season, nm) = 1),
     n AS (SELECT * FROM (SELECT DISTINCT season, person_id, norm_name(player_name) AS nm FROM shots)
           QUALIFY count(*) OVER (PARTITION BY season, nm) = 1),
     o AS (SELECT * FROM read_csv('data/manual/id_overrides.csv', header = true, columns = {'slug': 'VARCHAR', 'person_id': 'BIGINT'}))
SELECT b.slug, b.season, coalesce(o.person_id, n.person_id) AS person_id
FROM b LEFT JOIN o USING (slug) LEFT JOIN n ON n.season = b.season AND n.nm = b.nm
WHERE coalesce(o.person_id, n.person_id) IS NOT NULL;
