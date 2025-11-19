COPY (
    SELECT name_uuid, taxon_latname, taxon_author
    FROM algaebase_algaebasetaxontree
    UNION ALL
    SELECT name_uuid, taxon_latname, taxon_author
    FROM algaebase_algaebasetaxonsynonym
) TO '/path/to/algae_all_names.psv' WITH (FORMAT CSV, DELIMITER '|', HEADER, ENCODING 'UTF8')"