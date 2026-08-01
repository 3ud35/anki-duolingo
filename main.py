import datetime
from pathlib import Path

from src.config import SPREADSHEET_ID
from src.export import build_package
from src.radicals import extract_radicals
from src.schema import SHEET_KANJI, SHEET_VOCAB
from src.sheets import fetch_sheet_rows

OUTPUT_DIR = Path("output")

MISSING_COLUMNS_FOR_FULL_ENGLISH = [
    "MOTS: Composition (English)",
    "MOTS: Commentaire (English)",
    "Analyse clés kanjis: Sens des Radicaux (English)",
    "Analyse clés kanjis: Mnémotechnique Visuelle (English)",
    "Analyse clés kanjis: Étymologie Historique (English)",
]

MISSING_COLUMNS_FOR_FULL_FRENCH = [
    "MOTS: Sens (Français) - blocks the whole Vocabulary meaning field in French",
]


def main() -> None:
    vocab_rows = fetch_sheet_rows(SPREADSHEET_ID, SHEET_VOCAB)
    kanji_rows = fetch_sheet_rows(SPREADSHEET_ID, SHEET_KANJI)
    radicals, unresolved = extract_radicals(kanji_rows)

    print(f"{SHEET_VOCAB}: {len(vocab_rows)} rows")
    print(f"{SHEET_KANJI}: {len(kanji_rows)} rows")
    print(f"Isolated radicals: {len(radicals)}")

    for item in unresolved:
        print(
            f"  [!] {item['Kanji']}: radical {item['Radical']!r} has no "
            "meaning anywhere in the data - needs fixing in the spreadsheet."
        )

    OUTPUT_DIR.mkdir(exist_ok=True)
    today = datetime.date.today().isoformat()

    for language in ("en", "fr"):
        output_path = OUTPUT_DIR / f"anki_export_{len(vocab_rows)}words_{language}_{today}.apkg"
        build_package(vocab_rows, kanji_rows, radicals, language).write_to_file(str(output_path))
        print(f"Wrote {output_path}")

    print("\nColumns needed in the spreadsheet for a complete English export:")
    for column in MISSING_COLUMNS_FOR_FULL_ENGLISH:
        print(f"  - {column}")

    print("\nColumns needed in the spreadsheet for a complete French export:")
    for column in MISSING_COLUMNS_FOR_FULL_FRENCH:
        print(f"  - {column}")


if __name__ == "__main__":
    main()
