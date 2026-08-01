"""Builds the Anki .apkg package from the ingested vocabulary / kanji / radical data.

Three note types, each with a Recognition and a Production template (the
classic reversed-card pattern), packaged into one importable file per
language ("en" / "fr"):
- Vocabulary: from the `MOTS` tab.
- Kanji: from the `Analyse clés kanjis` tab, radical breakdown included as
  context on the card itself.
- Radical: from the radicals isolated by src/radicals.py, as a standalone
  reference deck on top of that (cheap to keep since the data already
  exists in this shape - safe to ignore/suspend in Anki if unwanted).

Categorical labels (part of speech, theme) are translated in code via
src/translations.py. Free-form prose fields with no data in the other
language (commentary, mnemonics, etymology, radical meanings) are left
blank for whichever language lacks a real source column - see main.py's
startup report for exactly what's missing.

Model/deck IDs below are fixed random constants, one set per language:
never regenerate them, since Anki uses them to recognize "the same"
model/deck across reimports. The two languages get distinct IDs so both
packages can be imported into the same Anki collection side by side
without colliding. Each note's guid is likewise derived from a stable key
plus the language (never from content expected to be edited later, e.g. a
translation) via KeyedNote, so re-running the script and reimporting
updates existing cards instead of duplicating them.

Note field names are English identifiers even though the underlying
spreadsheet columns are French - only src/schema.py's column names have to
match the source data verbatim.
"""

import html

import genanki

from src.translations import translate_label

IDS = {
    "en": {
        "model_vocab": 2076060013,
        "model_kanji": 2134279807,
        "model_radical": 1814570334,
        "deck_vocab": 1683549848,
        "deck_kanji": 1593559119,
        "deck_radical": 1538186432,
    },
    "fr": {
        "model_vocab": 1479258928,
        "model_kanji": 2018506066,
        "model_radical": 1635955490,
        "deck_vocab": 1406830556,
        "deck_kanji": 1511132156,
        "deck_radical": 1456001352,
    },
}

CSS = """
.card { font-family: "Noto Sans JP", "Helvetica Neue", sans-serif; font-size: 20px;
        text-align: center; color: #1a1a1a; background-color: #fafafa; }
.term { font-size: 42px; font-weight: bold; }
.kanji-big { font-size: 80px; font-weight: bold; }
.reading { font-size: 20px; color: #666; margin-top: 6px; }
.meaning { font-size: 24px; margin-top: 10px; }
.badge { font-size: 14px; color: #888; margin-top: 8px; }
.extra { font-size: 14px; color: #999; margin-top: 10px; }
.components, .story, .etymology { font-size: 15px; margin-top: 10px; text-align: left; }
"""


class KeyedNote(genanki.Note):
    """A Note whose guid comes from an explicit stable key instead of
    genanki's default (a hash of every field), so editing a field later
    doesn't turn a reimport into a duplicate."""

    def __init__(self, model, fields, guid_key, tags=None):
        super().__init__(model=model, fields=fields, tags=tags or [])
        self._guid_key = guid_key

    @property
    def guid(self):
        return genanki.guid_for(self._guid_key)


def _vocab_model(language: str) -> genanki.Model:
    return genanki.Model(
        IDS[language]["model_vocab"],
        f"Vocabulary ({language.upper()})",
        fields=[
            {"name": "Expression"},
            {"name": "Reading"},
            {"name": "Meaning"},
            {"name": "PartOfSpeech"},
            {"name": "Theme"},
            {"name": "Extra"},
        ],
        templates=[
            {
                "name": "Recognition",
                "qfmt": '<div class="term">{{Expression}}</div>',
                "afmt": '<div class="term">{{furigana:Reading}}</div>'
                '<hr id="answer">'
                '<div class="meaning">{{Meaning}}</div>'
                '<div class="badge">{{PartOfSpeech}} | {{Theme}}</div>'
                '<div class="extra">{{Extra}}</div>',
            },
            {
                "name": "Production",
                "qfmt": '<div class="meaning">{{Meaning}}</div>'
                '<div class="badge">{{PartOfSpeech}} | {{Theme}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="term">{{furigana:Reading}}</div>'
                '<div class="extra">{{Extra}}</div>',
            },
        ],
        css=CSS,
    )


def _kanji_model(language: str) -> genanki.Model:
    return genanki.Model(
        IDS[language]["model_kanji"],
        f"Kanji ({language.upper()})",
        fields=[
            {"name": "Kanji"},
            {"name": "Romaji"},
            {"name": "Meaning"},
            {"name": "Radicals"},
            {"name": "RadicalMeanings"},
            {"name": "Mnemonic"},
            {"name": "Etymology"},
        ],
        templates=[
            {
                "name": "Recognition",
                "qfmt": '<div class="kanji-big">{{Kanji}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="meaning">{{Meaning}}</div>'
                '<div class="badge">{{Romaji}}</div>'
                '<div class="components"><b>Radicals:</b> {{Radicals}} - {{RadicalMeanings}}</div>'
                '<div class="story"><b>Mnemonic:</b> {{Mnemonic}}</div>'
                '<div class="etymology"><b>Etymology:</b> {{Etymology}}</div>',
            },
            {
                "name": "Production",
                "qfmt": '<div class="meaning">{{Meaning}}</div>'
                '<div class="badge">Radicals: {{RadicalMeanings}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="kanji-big">{{Kanji}}</div>'
                '<div class="story">{{Mnemonic}}</div>',
            },
        ],
        css=CSS,
    )


def _radical_model(language: str) -> genanki.Model:
    return genanki.Model(
        IDS[language]["model_radical"],
        f"Radical ({language.upper()})",
        fields=[
            {"name": "Radical"},
            {"name": "Meaning"},
            {"name": "Kanjis"},
        ],
        templates=[
            {
                "name": "Recognition",
                "qfmt": '<div class="kanji-big">{{Radical}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="meaning">{{Meaning}}</div>'
                '<div class="extra">Appears in: {{Kanjis}}</div>',
            },
            {
                "name": "Production",
                "qfmt": '<div class="meaning">{{Meaning}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="kanji-big">{{Radical}}</div>'
                '<div class="extra">Appears in: {{Kanjis}}</div>',
            },
        ],
        css=CSS,
    )


def _esc(value: str) -> str:
    return html.escape(value or "")


def _reading(row: dict) -> str:
    # `Japonais` mirrors whatever script the word is natively written in
    # (kanji, hiragana or katakana), so it's not a reliable reading when the
    # word has a Kanji form - `Hiragana` always holds the phonetic reading.
    if row["Kanji"]:
        return f"{row['Kanji']}[{row['Hiragana']}]"
    return row["Japonais"]


def _extra(row: dict) -> str:
    parts = [row["Composition"], row["Commentaire"]]
    return "<br>".join(_esc(p) for p in parts if p and p != "-")


def _tag(value: str) -> str:
    return value.strip().lower().replace(" ", "_") if value and value != "-" else ""


def build_vocab_notes(vocab_rows: list[dict], language: str) -> list[genanki.Note]:
    model = _vocab_model(language)
    notes = []
    for row in vocab_rows:
        part_of_speech = translate_label(row["Grammaire"], language)
        theme = translate_label(row["Thème"], language)
        # `Anglais` is the only translated meaning MOTS has - there's no
        # French equivalent column yet, so the FR export has no meaning to
        # show until one is added.
        meaning = row["Anglais"] if language == "en" else ""
        # Composition/Commentaire are French-only prose, no English version.
        extra = _extra(row) if language == "fr" else ""

        tags = [
            f"{prefix}::{_tag(value)}"
            for prefix, value in (
                ("alphabet", translate_label(row["Alphabet"], language)),
                ("theme", theme),
                ("grammar", part_of_speech),
            )
            if _tag(value)
        ]
        notes.append(
            KeyedNote(
                model=model,
                fields=[
                    _esc(row["Kanji"] or row["Japonais"]),
                    _esc(_reading(row)),
                    _esc(meaning),
                    _esc(part_of_speech),
                    _esc(theme),
                    extra,
                ],
                guid_key=f"vocab-{language}-{row['Ordre']}",
                tags=tags,
            )
        )
    return notes


def build_kanji_notes(kanji_rows: list[dict], language: str) -> list[genanki.Note]:
    model = _kanji_model(language)
    notes = []
    for row in kanji_rows:
        meaning = row["Sens (Français)"] if language == "fr" else row["Sens (Anglais)"]
        # Sens des Radicaux / Mnémotechnique / Étymologie are French-only
        # prose, no English version exists yet.
        radical_meanings = row["Sens des Radicaux"] if language == "fr" else ""
        mnemonic = row["Mnémotechnique Visuelle"] if language == "fr" else ""
        etymology = row["Étymologie Historique"] if language == "fr" else ""

        notes.append(
            KeyedNote(
                model=model,
                fields=[
                    _esc(row["Kanji"]),
                    _esc(row["Romaji"]),
                    _esc(meaning),
                    _esc(row["Radicaux"]),
                    _esc(radical_meanings),
                    _esc(mnemonic),
                    _esc(etymology),
                ],
                guid_key=f"kanji-{language}-{row['Kanji']}",
            )
        )
    return notes


def build_radical_notes(radicals: list[dict], language: str) -> list[genanki.Note]:
    model = _radical_model(language)
    notes = []
    for radical in radicals:
        # Radical meanings come from Sens des Radicaux, French-only - see
        # build_kanji_notes.
        meaning = radical["Meaning"] if language == "fr" else ""
        notes.append(
            KeyedNote(
                model=model,
                fields=[
                    _esc(radical["Radical"]),
                    _esc(meaning),
                    _esc(", ".join(radical["Kanjis"])),
                ],
                guid_key=f"radical-{language}-{radical['Radical']}",
            )
        )
    return notes


def build_package(
    vocab_rows: list[dict], kanji_rows: list[dict], radicals: list[dict], language: str
) -> genanki.Package:
    label = language.upper()
    vocab_deck = genanki.Deck(IDS[language]["deck_vocab"], f"Japanese ({label})::Vocabulary")
    kanji_deck = genanki.Deck(IDS[language]["deck_kanji"], f"Japanese ({label})::Kanji")
    radical_deck = genanki.Deck(IDS[language]["deck_radical"], f"Japanese ({label})::Radicals")

    for note in build_vocab_notes(vocab_rows, language):
        vocab_deck.add_note(note)
    for note in build_kanji_notes(kanji_rows, language):
        kanji_deck.add_note(note)
    for note in build_radical_notes(radicals, language):
        radical_deck.add_note(note)

    return genanki.Package([vocab_deck, kanji_deck, radical_deck])
