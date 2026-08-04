from pathlib import Path

from src.config import SPREADSHEET_ID
from src.export import build_package
from src.radicals import extract_radicals
from src.schema import SHEET_KANA_GID, SHEET_KANJI, SHEET_VOCAB
from src.sheets import fetch_sheet_rows, fetch_sheet_rows_by_gid

OUTPUT_DIR = Path("output")

FILE_SLUGS = {"en": "japanese_duolingo", "fr": "japonais_duolingo"}

MISSING_COLUMNS_FOR_FULL_ENGLISH = [
    "Kana tab: Note de prononciation (English)",
]

MISSING_COLUMNS_FOR_FULL_FRENCH: list[str] = []


def main() -> None:
    vocab_rows = fetch_sheet_rows(SPREADSHEET_ID, SHEET_VOCAB)
    kanji_rows = fetch_sheet_rows(SPREADSHEET_ID, SHEET_KANJI)
    kana_rows = fetch_sheet_rows_by_gid(SPREADSHEET_ID, SHEET_KANA_GID)
    radicals, unresolved = extract_radicals(kanji_rows)

    print(f"{SHEET_VOCAB}: {len(vocab_rows)} rows")
    print(f"{SHEET_KANJI}: {len(kanji_rows)} rows")
    print(f"Kana tab: {len(kana_rows)} rows")
    print(f"Isolated radicals: {len(radicals)}")

    for item in unresolved:
        print(
            f"  [!] {item['Kanji']}: radical {item['Radical']!r} has no "
            f"{item['Language']} meaning anywhere in the data - needs "
            "fixing in the spreadsheet."
        )

    OUTPUT_DIR.mkdir(exist_ok=True)

    for language in ("en", "fr"):
        # Fixed name, overwritten every run: Anki matches notes by the guid
        # baked into the file, not by filename, so there's no need to keep
        # every past export around or to make this name unique.
        output_path = OUTPUT_DIR / f"{FILE_SLUGS[language]}.apkg"
        build_package(vocab_rows, kanji_rows, radicals, kana_rows, language).write_to_file(
            str(output_path)
        )
        print(f"Wrote {output_path}")

    if MISSING_COLUMNS_FOR_FULL_ENGLISH:
        print("\nColumns needed in the spreadsheet for a complete English export:")
        for column in MISSING_COLUMNS_FOR_FULL_ENGLISH:
            print(f"  - {column}")

    if MISSING_COLUMNS_FOR_FULL_FRENCH:
        print("\nColumns needed in the spreadsheet for a complete French export:")
        for column in MISSING_COLUMNS_FOR_FULL_FRENCH:
            print(f"  - {column}")


if __name__ == "__main__":
    main()
