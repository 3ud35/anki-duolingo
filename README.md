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

The spreadsheet must be shared as read-only ("Anyone with the link" → Viewer). The script reads three tabs, whose schema is declared in `src/schema.py`. Two are identified by name, the third by its `gid` (its tab name isn't exposed by the public CSV endpoint used to fetch it).

### `MOTS` tab

| Column | Content |
|---|---|
| Ordre | Entry number |
| Anglais | English translation |
| Français | French translation |
| Rômaji | Romanization |
| Japonais | Japanese writing, exactly as taught by Duolingo (kana or kanji depending on the word) |
| Alphabet | Script used (Hiragana, Katakana, Kanji, Mixed) |
| Composition EN | Structure/etymology notes, in English |
| Composition FR | Structure/etymology notes, in French |
| Thème | Semantic category |
| Grammaire | Part of speech |
| Propriété | Usage sub-category |
| Commentaire EN | Contextual explanation, in English |
| Commentaire FR | Contextual explanation, in French |
| Hiragana | Hiragana variant |
| Katakana | Katakana variant |
| Kanji | Kanji variant |

The `Hiragana`/`Katakana`/`Kanji` variant columns are **not used** to build vocabulary cards - only `Japonais` is, since that's the exact form Duolingo actually teaches. Those three columns can hold a different script than what was learned (e.g. a kanji form for a word only ever seen in kana), which would be misleading to show instead. That said, the `Kanji` column is used to cross-reference vocabulary examples on the Radicals deck (see below) - it's read, just never shown as a substitute for `Japonais`.

### `Analyse clés kanjis` tab

| Column | Content |
|---|---|
| Kanji | Character |
| Romaji | Romanization |
| Sens EN | Meaning in English |
| Sens FR | Meaning in French |
| Radicaux | Radicals making up the kanji |
| Sens Radicaux EN | Meaning of those radicals, in English |
| Sens Radicaux FR | Meaning of those radicals, in French |
| Mnémotechnique EN | Memory aid, in English |
| Mnémotechnique FR | Memory aid, in French |
| Étymologie EN | Character origin, in English |
| Étymologie FR | Character origin, in French |

### Kana tab (`SHEET_KANA_GID`)

| Column | Content |
|---|---|
| Groupe | Consonant group label (not used for cards) |
| Rōmaji | Romanization |
| Hiragana | Hiragana character for this sound (or `(N/A)` if none, e.g. chōonpu) |
| Katakana | Katakana character for this sound |
| Type | Gojūon / Dakuten / Handakuten / Yōon / Sokuon / Chōonpu |
| Note de prononciation | Pronunciation tip |

Column names are kept as-is (matching the actual spreadsheet headers) rather than translated, since they're literal keys into the source data, not descriptive text.

If the spreadsheet's structure changes upstream, the script fails explicitly with a message pointing at the mismatch instead of misreading the columns.

## Usage

```bash
python main.py
```

This produces two `.apkg` files in `output/` (gitignored), one per language, with a fixed name that gets overwritten on every run - the filename plays no part in how Anki matches cards on import, so there's no reason to keep old exports around or to make the name unique per run:

```
output/japanese_duolingo.apkg
output/japonais_duolingo.apkg
```

Each file bundles 5 decks under a `Japanese Duolingo` / `Japonais Duolingo` parent deck:

- **Vocabulary** - from `MOTS`. Recognition, Production, and a third "FromRomaji" card (Romaji → word), each note has 3 cards.
- **Kanji** - from `Analyse clés kanjis`, radical breakdown shown as context on the card.
- **Radicals** - every radical isolated and deduplicated from the kanji tab. One card per radical: front shows the radical and its meaning, back lists every kanji that uses it (with that kanji's own meaning) plus, for each one, up to two real vocabulary words from `MOTS` that contain it (with their meaning) - concrete usage examples rather than a bare list of characters.
- **Hiragana** / **Katakana** - two separate decks from the kana tab (one row can produce a note in both, since it lists both scripts for the same sound).

Vocabulary, Kanji, Hiragana and Katakana each have a Recognition and a Production card per note (Vocabulary has the extra FromRomaji one); Radicals has a single card per note (front/back as described above). Every deck has a description (visible in Anki via the deck's "Description" button) stating its entry count, generation date, and any known data gap for that language.

### Updating

Re-running the script after editing the spreadsheet is the normal workflow: it always regenerates the full package from the current sheet content. To apply the update, just re-import the file into Anki (File → Import) - no need to delete anything first. Each note's guid is derived from a stable spreadsheet key (never from content expected to change), and matching notes are updated in place with their review history preserved; genuinely new rows are added as new cards. Rows removed from the spreadsheet are **not** automatically deleted from Anki - that would need a manual cleanup in Anki's Browse screen.

### Deleting a deck in Anki

Decks screen → gear icon next to the deck → **Delete** → confirm. This removes the deck, its subdecks, all cards, and their review history. There's no undo beyond restoring an Anki backup.

If that gear icon isn't there in your version/theme (seen in practice on at least one Linux desktop build), a reliable fallback that doesn't depend on finding it: **Browse** → search `deck:<name>` (matches subdecks too) → select all cards (Ctrl+A) → **Notes → Delete Notes**. This wipes the content; the empty deck shell left behind is harmless and can just be reused.

### Publishing to AnkiWeb's Shared Decks

This isn't a raw file upload - the deck's filename plays no role here either. The actual flow:

1. Import the generated file into Anki locally (as above), then **sync** that collection to your AnkiWeb account from the desktop app.
2. Log into [ankiweb.net](https://ankiweb.net), find the deck in your synced deck list, click **Share**, fill in title/description/tags, publish.
3. To push a later update to an already-shared deck: same thing, click **Share** again on that deck. Download counts and ratings aren't reset.

**Important**: AnkiWeb matches the shared listing to update by the deck's name/location. Renaming `Japanese Duolingo` / `Japonais Duolingo` after first sharing would break future updates to that listing - keep the deck names as they are once published. Also note: people who already downloaded the deck don't get updates automatically, they need to re-download and re-import.

Sources: [Anki Manual - Contributing](https://docs.ankiweb.net/contrib.html), [Anki Forums - Updating a shared deck](https://forums.ankiweb.net/t/how-do-i-update-a-deck-i-shared-to-ankiweb-without-deleting-the-version-already-shared/26006)

### Known data gaps

`MOTS` and `Analyse clés kanjis` are now fully bilingual (every prose field has an EN and FR sibling column). Categorical fields (part of speech, theme, alphabet, kana type) don't need a spreadsheet column at all - they're translated in code (`src/translations.py`) since the set of possible values is small and fixed.

The one remaining gap: the kana tab's `Note de prononciation` only exists in French, so the English Hiragana/Katakana decks leave that field blank until an English column is added upstream.
