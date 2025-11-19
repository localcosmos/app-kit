CREATE TABLE taxa (
    id SERIAL PRIMARY KEY,
    genus TEXT,
    species TEXT,
    subspecies TEXT,
    variety TEXT,
    forma TEXT,
    nomenclatural_authorities TEXT,
    year_of_publication TEXT,
    id_current_name INTEGER,
    current_flag TEXT,
    record_status TEXT,
    phylum TEXT,
    subphylum TEXT,
    class TEXT,
    "order" TEXT,  -- "order" is a reserved word, so it must be quoted
    family TEXT,
    subfamily TEXT,
    tribe TEXT,
    habitat TEXT
);
CREATE INDEX idx_taxa_genus ON taxa(genus);
CREATE INDEX idx_taxa_species ON taxa(species);