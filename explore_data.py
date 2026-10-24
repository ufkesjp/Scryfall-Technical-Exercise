"""Getting familiar with the dataset structure, checking for nulls and duplicates,etc...."""
from pathlib import Path
import pandas as pd 

DATA_PATH = Path(__file__).parent / "data" / "oracle-cards.json.gz"

pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 100)

# quick formatting to separate sections of exploration
def section(title):
    print(f"\n{'=' * 15} {title} {'=' * 15}")

def main():
    df = pd.read_json(DATA_PATH, lines=True)

    section("Info")
    df.info(max_cols=None, show_counts=True)

    section("Describe")
    print(df.describe())

    section("NA Counts")
    print(df.isna().sum())

    section("Unique counts")
    # astype(str) because list/dict columns (colors, image_uris, ...) are unhashable
    print(df.astype(str).nunique())

    section("Sample rows")
    print(df[["name", "mana_cost", "cmc", "type_line", "rarity", "set"]].sample(8, random_state=1))

    section("Duplicate checks")
    print(f"Duplicate oracle_id: {df['oracle_id'].duplicated().sum()}")
    print(f"Duplicate name:      {df['name'].duplicated().sum()}")

if __name__ == "__main__":
    main()

