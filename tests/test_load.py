import copy

import pytest

from db import connect
from load import load

TABLES = ["sets", "rarities", "cards", "keywords", "card_keywords", "card_types", "colors", "card_color_identity"]

SIMPLE_CARD = {
    "oracle_id": "oracle-simple", "id": "scry-simple", "name": "Llanowar Elves", "layout": "normal",
    "mana_cost": "{G}", "cmc": 1.0, "type_line": "Legendary Creature — Elf Druid", "oracle_text": "{T}: Add {G}.",
    "power": "1", "toughness": "1", "rarity": "common", "set": "m19", "set_name": "Core Set 2019",
    "set_type": "core", "collector_number": "314", "released_at": "2018-07-13", "edhrec_rank": 123,
    "reserved": False, "digital": False, "keywords": ["Mana Ability"], "color_identity": ["G"],
}

# Multi-faced: no top-level mana_cost, oracle_text, power or toughness, and a type line per face.
MULTI_FACED_CARD = {
    "oracle_id": "oracle-multi", "id": "scry-multi", "name": "Delver of Secrets // Insectile Aberration",
    "layout": "transform", "cmc": 1.0, "type_line": "Creature — Human Wizard // Creature — Human Insect",
    "rarity": "common", "set": "isd", "set_name": "Innistrad", "set_type": "expansion",
    "collector_number": "51", "released_at": "2011-09-30", "reserved": False, "digital": False,
    "keywords": ["Flying", "Transform"], "color_identity": ["U"],
}


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def counts(conn) -> dict[str, int]:
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}


def test_load_twice_gives_identical_counts(conn):
    cards = [SIMPLE_CARD, MULTI_FACED_CARD]
    assert load(conn, cards) == 2
    first = counts(conn)
    assert first["cards"] == 2 and first["keywords"] == 3
    load(conn, cards)
    assert counts(conn) == first
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_reload_with_fewer_keywords_drops_stale_rows(conn):
    load(conn, [MULTI_FACED_CARD])
    assert counts(conn)["card_keywords"] == 2
    trimmed = copy.deepcopy(MULTI_FACED_CARD)
    trimmed["keywords"] = ["Flying"]
    load(conn, [trimmed])
    assert conn.execute("SELECT COUNT(*) FROM card_keywords").fetchone()[0] == 1


def test_keyword_ids_are_stable_across_reloads(conn):
    load(conn, [SIMPLE_CARD])
    before = conn.execute("SELECT * FROM keywords").fetchall()
    load(conn, [SIMPLE_CARD])
    assert conn.execute("SELECT * FROM keywords").fetchall() == before


def test_unknown_rarity_fails_loudly(conn):
    bad = {**SIMPLE_CARD, "rarity": "legendary"}
    with pytest.raises(Exception):
        load(conn, [bad])
