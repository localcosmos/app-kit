# Algaebase Database Operations

## Export name_uuids to a File

This file can then be used to make the name_uuid constant across database updates.

```bash
psql -d database -c "\COPY (
    SELECT name_uuid, taxon_latname, taxon_author
    FROM algaebase_algaebasetaxontree
    UNION ALL
    SELECT name_uuid, taxon_latname, taxon_author
    FROM algaebase_algaebasetaxonsynonym
) TO '/path/to/algae_all_names.psv' WITH (FORMAT CSV, DELIMITER '|', HEADER, ENCODING 'UTF8')"
```

## Export Database

```bash
pg_dump -U datauser -h localhost -p 5432 -d taxonomy --no-owner --no-privileges --format=plain -t 'algaebase_*' > algaebase_tables_dump.sql
```

## Import the Dump

```bash
psql -U datauser -h localhost -p 5432 -d target_db < algaebase_tables_dump.sql
```