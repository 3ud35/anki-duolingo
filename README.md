# anki-duolingo

Generates [Anki](https://apps.ankiweb.net/) flashcard packages from a personal Japanese vocabulary Google Sheet.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in the spreadsheet ID (found in its URL):

```bash
cp .env.example .env
```

## Data source

The spreadsheet must be shared as read-only ("Anyone with the link" → Viewer). The script reads two tabs, whose schema is declared in `src/schema.py`:

### `MOTS` tab

| Column | Content |
|---|---|
| Ordre | Entry number |
| Anglais | English translation |
| Rômaji | Romanization |
| Japonais | Japanese writing (kana/kanji) |
| Alphabet | Script used (Hiragana, Katakana, Kanji, Mixed) |
| Composition | Structure/etymology notes |
| Thème | Semantic category |
| Grammaire | Part of speech |
| Propriété | Usage sub-category |
| Commentaire | Contextual explanation |
| Hiragana | Hiragana variant |
| Katakana | Katakana variant |
| Kanji | Kanji variant |

### `Analyse clés kanjis` tab

| Column | Content |
|---|---|
| Kanji | Character |
| Romaji | Romanization |
| Sens (Anglais) | Meaning in English |
| Sens (Français) | Meaning in French |
| Radicaux | Radicals making up the kanji |
| Sens des Radicaux | Meaning of those radicals |
| Mnémotechnique Visuelle | Memory aid |
| Étymologie Historique | Character origin |

Column names are kept as-is (matching the actual spreadsheet headers) rather than translated, since they're literal keys into the source data, not descriptive text.

If the spreadsheet's structure changes upstream, the script fails explicitly with a message pointing at the mismatch instead of misreading the columns.

## Usage

```bash
python main.py
```

This produces two `.apkg` files in `output/` (gitignored), one per language:

```
output/anki_export_<word count>words_en_<date>.apkg
output/anki_export_<word count>words_fr_<date>.apkg
```

Each file bundles 3 decks: `Vocabulary`, `Kanji`, `Radicals` (the last one built by isolating and deduplicating every radical mentioned across the `Analyse clés kanjis` tab, with the list of kanji it appears in). Each deck has a Recognition and a Production card per note. Re-importing a regenerated file updates existing cards in place instead of duplicating them (each note's guid is derived from a stable spreadsheet key, not from content that's expected to change).

Re-running the script after editing the spreadsheet is the normal workflow: it always regenerates the full package from the current sheet content.

### Known data gaps

Some fields only exist in French in the source spreadsheet, so the English export leaves them blank until the corresponding column is added upstream:

- `MOTS`: no `Composition`/`Commentaire` in English.
- `Analyse clés kanjis`: no `Sens des Radicaux`, `Mnémotechnique Visuelle`, or `Étymologie Historique` in English.

Conversely, the French export's Vocabulary `Meaning` field is empty because `MOTS` has no `Sens (Français)` column (only `Anglais`). Categorical fields (part of speech, theme, alphabet) don't have this problem - they're translated in code (`src/translations.py`) since the set of possible values is small and fixed.
