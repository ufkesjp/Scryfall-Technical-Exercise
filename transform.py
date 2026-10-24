"""Read the Oracle Cards JSON Lines file and flatten each card into rows for the schema's tables."""
from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, Iterator

Rows = dict[str, list[tuple]]

# Words before the em dash in a type line that are supertypes; everything else there is a card type.
SUPERTYPES = {"Basic", "Legendary", "Snow", "World", "Ongoing", "Elite", "Host"}


def read_cards(path: Path | str) -> Iterator[dict[str, Any]]:
    """Stream cards from a gzipped JSON Lines file, one card per line."""
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def split_type_line(type_line: str) -> list[tuple[str, str]]:
    """Split a type line into (type_role, type_name) pairs, de-duplicated across faces.

    'Legendary Creature — Elf Druid' -> supertype Legendary, card_type Creature, subtypes Elf, Druid.
    Multi-faced cards use 'Front // Back', so every face is split on its own. Multi-word subtypes
    (e.g. 'Time Lord') are split on whitespace like the rest.
    """
    parts: dict[tuple[str, str], None] = {}  # dict as an ordered set
    for face in type_line.split(" // "):
        left, _, right = face.partition(" — ")
        for word in left.split():
            parts[("supertype" if word in SUPERTYPES else "card_type", word)] = None
        for word in right.split():
            parts[("subtype", word)] = None
    return list(parts)


def transform_card(card: dict[str, Any]) -> Rows:
    """Return {table: [row tuples]} for one card. Child rows carry the keyword name, not its id."""
    oracle_id = card["oracle_id"]
    return {
        "sets": [(card["set"], card["set_name"], card["set_type"])],
        "cards": [(
            oracle_id,
            card["id"],
            card["name"],
            card["layout"],
            card.get("mana_cost"),  # absent on multi-faced cards
            card["cmc"],
            card["type_line"],
            card.get("oracle_text"),
            card.get("power"),
            card.get("toughness"),
            card["rarity"],
            card["set"],
            card["collector_number"],
            card["released_at"],
            card.get("edhrec_rank"),
            int(card["reserved"]),
            int(card["digital"]),
        )],
        "keywords": [(k,) for k in card.get("keywords", [])],
        "card_keywords": [(oracle_id, k) for k in card.get("keywords", [])],
        "card_types": [(oracle_id, role, name) for role, name in split_type_line(card["type_line"])],
        "card_color_identity": [(oracle_id, c) for c in card.get("color_identity", [])],
    }
