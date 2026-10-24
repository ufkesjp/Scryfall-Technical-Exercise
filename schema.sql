-- Scryfall Oracle Cards: one row per unique Oracle ID (rules-identical cards collapse to one row).
-- Applied once by db.connect() when the database is first created.

CREATE TABLE sets (
    set_code TEXT PRIMARY KEY,          -- source field "set"
    set_name TEXT NOT NULL,
    set_type TEXT NOT NULL              -- expansion, token, memorabilia, ...
);

-- Reference table so rarities sort common -> mythic instead of alphabetically.
CREATE TABLE rarities (
    rarity     TEXT PRIMARY KEY,
    sort_order INTEGER NOT NULL UNIQUE
);

INSERT INTO rarities VALUES ('common', 1), ('uncommon', 2), ('rare', 3), ('mythic', 4), ('special', 5), ('bonus', 6);

CREATE TABLE cards (
    oracle_id        TEXT PRIMARY KEY,
    scryfall_id      TEXT NOT NULL,     -- source field "id" (the printing Scryfall chose to represent this card)
    name             TEXT NOT NULL,     -- NOT unique: tokens and art cards share names
    layout           TEXT NOT NULL,     -- normal, token, art_series, transform, ...
    mana_cost        TEXT,              -- NULL on multi-faced cards (lives on the faces)
    cmc              REAL NOT NULL,
    type_line        TEXT NOT NULL,
    oracle_text      TEXT,
    power            TEXT,              -- text because of values like '*' and '1+*'
    toughness        TEXT,
    rarity           TEXT NOT NULL REFERENCES rarities (rarity),
    set_code         TEXT NOT NULL REFERENCES sets (set_code),
    collector_number TEXT NOT NULL,
    released_at      TEXT NOT NULL,     -- ISO date
    edhrec_rank      INTEGER,
    reserved         INTEGER NOT NULL CHECK (reserved IN (0, 1)),
    digital_only     INTEGER NOT NULL CHECK (digital_only IN (0, 1))   -- source field "digital"
);

CREATE TABLE keywords (
    keyword_id INTEGER PRIMARY KEY,
    keyword    TEXT NOT NULL UNIQUE
);

CREATE TABLE card_keywords (
    oracle_id  TEXT NOT NULL REFERENCES cards (oracle_id) ON DELETE CASCADE,
    keyword_id INTEGER NOT NULL REFERENCES keywords (keyword_id),
    PRIMARY KEY (oracle_id, keyword_id)
) WITHOUT ROWID;

-- Type line split into parts. For multi-faced cards the parts of every face are included.
CREATE TABLE card_types (
    oracle_id TEXT NOT NULL REFERENCES cards (oracle_id) ON DELETE CASCADE,
    type_role TEXT NOT NULL CHECK (type_role IN ('supertype', 'card_type', 'subtype')),
    type_name TEXT NOT NULL,
    PRIMARY KEY (oracle_id, type_role, type_name)
) WITHOUT ROWID;

-- WUBRG reference: gives color letters a name and a sort order.
CREATE TABLE colors (
    color_code TEXT PRIMARY KEY CHECK (length(color_code) = 1),   -- W, U, B, R, G
    color_name TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL UNIQUE                            -- WUBRG order
);

INSERT INTO colors VALUES ('W', 'White', 1), ('U', 'Blue', 2), ('B', 'Black', 3), ('R', 'Red', 4), ('G', 'Green', 5);

-- One row per color in the card's color identity. Colorless cards (empty identity) have no rows.
CREATE TABLE card_color_identity (
    oracle_id  TEXT NOT NULL REFERENCES cards (oracle_id) ON DELETE CASCADE,
    color_code TEXT NOT NULL REFERENCES colors (color_code),
    PRIMARY KEY (oracle_id, color_code)
) WITHOUT ROWID;

CREATE INDEX idx_cards_set_code    ON cards (set_code);
CREATE INDEX idx_cards_layout_name ON cards (layout, name);
CREATE INDEX idx_card_keywords_kw  ON card_keywords (keyword_id);
CREATE INDEX idx_card_types_name   ON card_types (type_role, type_name);
CREATE INDEX idx_card_color_identity ON card_color_identity (color_code);
