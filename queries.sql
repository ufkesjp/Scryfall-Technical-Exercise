-- Analysis queries, run by analysis.py. Each query starts with a "-- name:" line; "-- why:" lines explain why
-- the question matters. The cards table holds one representative printing per Oracle ID, so set, rarity and
-- released_at describe that printing, not every printing of the card.

-- name: setup
-- Real cards only: tokens, art cards, emblems and other non-deck objects are excluded by layout.
-- A temp view, so it exists for this connection only and the database file is not changed.
-- T-SQL equivalent: CREATE OR ALTER VIEW dbo.playable_cards AS   (T-SQL has no temp views)
CREATE TEMP VIEW playable_cards AS
SELECT * FROM cards
WHERE layout NOT IN ('token', 'double_faced_token', 'art_series', 'emblem', 'vanguard', 'scheme', 'planar', 'archenemy');

-- name: rarity_by_set_type
-- title: 1. How does the rarity mix differ by kind of set?
-- why: Rarity drives scarcity and price. Comparing set types shows which products are built for collectors (rare-heavy) and which for play (common-heavy).
-- finding: Commander sets are the most rare-heavy product (59.6% rare, 11.5% mythic), while expansions and core sets sit near 38% / 37% common and duel decks are the most common-heavy (43.9%). Alchemy is almost all non-common (3.0% common) because it is a digital-only product.
WITH counts AS (
    SELECT s.set_type, r.rarity, r.sort_order, COUNT(*) AS cards
    FROM playable_cards c
    JOIN sets s     ON s.set_code = c.set_code
    JOIN rarities r ON r.rarity = c.rarity
    GROUP BY s.set_type, r.rarity, r.sort_order
),
shares AS (
    SELECT *, SUM(cards) OVER (PARTITION BY set_type) AS set_type_cards FROM counts
)
SELECT set_type, rarity, cards, ROUND(100.0 * cards / set_type_cards, 1) AS pct_of_set_type
FROM shares
WHERE set_type_cards >= 500   -- skip set types too small to compare
ORDER BY set_type, sort_order;

-- name: cmc_by_color_count
-- title: 2. Does mana cost grow with the number of colors? (nonland cards)
-- why: Multicolor cards ask more of the player, so cost should compensate. Against that, a card needs mana of every color it uses, which also pushes cost up. Lands are excluded because their mana value of 0 would drag every average down.
-- finding: Average mana value rises with every added color, from 2.76 for colorless to 3.34 for one color and 4.76 for five. The median holds at 3 through two colors and only reaches 4 at three, so most of the early rise comes from a longer tail of expensive cards rather than a shift in the typical card.
-- One row per card; pandas does the grouping and the chart.
SELECT c.cmc, COUNT(ci.color_code) AS colors
FROM playable_cards c
LEFT JOIN card_color_identity ci ON ci.oracle_id = c.oracle_id
WHERE c.cmc < 100   -- joke cards (e.g. Gleemax, mana value 1,000,000) would wreck the averages
  AND NOT EXISTS (SELECT 1 FROM card_types t
                  WHERE t.oracle_id = c.oracle_id AND t.type_role = 'card_type' AND t.type_name = 'Land')
GROUP BY c.oracle_id, c.cmc;

-- name: subtypes_by_color
-- title: 3. Which creature types belong to which color?
-- why: Creature types are tribal identities. Which ones dominate a color shows what each color is for and which tribes are easy to build around. Multi-word types such as Time Lord count as separate words.
-- finding: Human is the most common creature type in every color. Past that, each color has its own tribes: Soldier, Cleric and Knight in white, Wizard and Merfolk in blue, Zombie and Vampire in black, Goblin in red, and Elf and Druid in green.
WITH mono AS (
    SELECT oracle_id, MIN(color_code) AS color_code
    FROM card_color_identity
    GROUP BY oracle_id
    HAVING COUNT(*) = 1
),
ranked AS (
    SELECT col.color_name, col.sort_order, t.type_name, COUNT(*) AS creatures,
           ROW_NUMBER() OVER (PARTITION BY col.color_code ORDER BY COUNT(*) DESC, t.type_name) AS rank
    FROM mono m
    JOIN playable_cards c ON c.oracle_id = m.oracle_id
    JOIN colors col       ON col.color_code = m.color_code
    JOIN card_types is_creature ON is_creature.oracle_id = c.oracle_id
                               AND is_creature.type_role = 'card_type' AND is_creature.type_name = 'Creature'
    JOIN card_types t     ON t.oracle_id = c.oracle_id AND t.type_role = 'subtype'
    GROUP BY col.color_code, col.color_name, col.sort_order, t.type_name
)
SELECT color_name AS color, rank, type_name AS creature_type, creatures
FROM ranked
WHERE rank <= 5
ORDER BY sort_order, rank;

-- name: cards_by_age_bucket
-- title: 4. How many new cards does each era of the game contribute?
-- why: Grouping release years into five-year eras hides exact dates yet still shows how card creation has changed over the game's life. Eras are counted in calendar years from the earliest release year in the dataset (the game's launch), so the era edges stay fixed from run to run and every full era spans exactly five calendar years. The average per release year makes the partial final era comparable. Note that released_at is the date of the representative printing Scryfall chose for each card, not necessarily its first release, so reprinted older cards can land in a newer era.
-- finding: Output grew steadily from about 240 cards per release year in 1993-1997 to roughly 470-540 through 2012, then accelerated to 950 in 2013-2017, 1,820 in 2018-2022 and 3,090 in 2023-2026. The final era covers only four release years so far, and the earliest era is understated because older cards are often represented by a later reprint.
WITH released AS (
    SELECT oracle_id, CAST(strftime('%Y', released_at) AS INTEGER) AS release_year   -- T-SQL: YEAR(released_at), if released_at is a date/datetime column rather than SQLite's text
    FROM playable_cards
    WHERE released_at <= date('now')   -- T-SQL: CAST(GETDATE() AS DATE). The export includes announced sets that haven't been released yet
),
eras AS (
    SELECT *, (release_year - MIN(release_year) OVER ()) / 5 * 5 AS era_start   -- 0, 5, 10, ... years after launch
    FROM released
)
SELECT MIN(release_year) || '-' || MAX(release_year) AS era,   -- T-SQL: CONCAT(MIN(release_year), '-', MAX(release_year))
       COUNT(*) AS cards,
       COUNT(DISTINCT release_year) AS release_years,
       ROUND(1.0 * COUNT(*) / COUNT(DISTINCT release_year), 1) AS avg_cards_per_release_year
FROM eras
GROUP BY era_start
ORDER BY era_start;
