"""Builds the Anki .apkg package from the ingested vocabulary / kanji /
radical / kana data.

Note types, each with a Recognition and a Production template (the classic
reversed-card pattern), packaged into one importable file per language
("en" / "fr"):
- Vocabulary: from the `MOTS` tab.
- Kanji: from the `Analyse clés kanjis` tab, radical breakdown included as
  context on the card itself.
- Kanji Words: a separate deck/note type, one note per kanji with at least
  one matching `MOTS` word - front shows the kanji plus up to 5 words
  containing it, back reveals the kanji's meaning. Kept as its own deck
  (not a third template on the Kanji note type) so it shows up natively in
  Anki's deck list instead of being hidden behind a Browse filter.
- Radical: from the radicals isolated by src/radicals.py, as a standalone
  reference deck on top of that (cheap to keep since the data already
  exists in this shape - safe to ignore/suspend in Anki if unwanted).
- Hiragana / Katakana: two separate decks sharing one note type, from the
  kana tab identified by gid in src/schema.py (SHEET_KANA_GID).

Kanji Words and Radicals both cross-reference `MOTS` by scanning each row's
`Japonais` field for individual kanji characters (`_vocab_index_by_kanji`) -
the `Hiragana`/`Katakana`/`Kanji` columns are never read, since `Japonais`
is the sole source of truth for what a word is written as.

Categorical labels (part of speech, theme, kana type) are translated in
code via src/translations.py. Every other free-form prose field is now
bilingual at the source (EN/FR sibling columns), except the kana tab's
pronunciation note, which is still French-only - see main.py's startup
report for exactly what's missing.

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

import datetime
import html
from collections import defaultdict

import genanki

from src.translations import translate_label

DECK_TITLES = {
    "en": {
        "root": "Japanese Duolingo",
        "vocab": "Vocabulary",
        "kanji": "Kanji",
        "kanji_words": "Kanji Words",
        "radical": "Radicals",
        "hiragana": "Hiragana",
        "katakana": "Katakana",
    },
    "fr": {
        "root": "Japonais Duolingo",
        "vocab": "Vocabulaire",
        "kanji": "Kanji",
        "kanji_words": "Kanji en contexte",
        "radical": "Radicaux",
        "hiragana": "Hiragana",
        "katakana": "Katakana",
    },
}

UNITS = {
    "en": {
        "vocab": "words",
        "kanji": "kanji",
        "kanji_words": "kanji",
        "radical": "radicals",
        "hiragana": "characters",
        "katakana": "characters",
    },
    "fr": {
        "vocab": "mots",
        "kanji": "kanjis",
        "kanji_words": "kanjis",
        "radical": "radicaux",
        "hiragana": "caractères",
        "katakana": "caractères",
    },
}

GENERATED_ON = {"en": "Generated on", "fr": "Généré le"}

GAP_NOTES = {
    ("hiragana", "en"): "Pronunciation notes aren't available in English yet.",
    ("hiragana", "fr"): "",
    ("katakana", "en"): "Pronunciation notes aren't available in English yet.",
    ("katakana", "fr"): "",
}

REIMPORT_NOTE = {
    "en": (
        "Re-import this file after updating the spreadsheet: matching cards "
        "are updated in place and review history is kept. Rows removed from "
        "the spreadsheet are not automatically deleted from Anki."
    ),
    "fr": (
        "Réimporte ce fichier après avoir mis à jour la spreadsheet : les "
        "cartes correspondantes sont mises à jour sur place, l'historique de "
        "révision est conservé. Les lignes supprimées de la spreadsheet ne "
        "sont pas automatiquement supprimées d'Anki."
    ),
}

IDS = {
    "en": {
        "model_vocab": 2076060013,
        "model_kanji": 2134279807,
        "model_kanji_words": 1767287174,
        "model_radical": 1814570334,
        "model_kana": 1410245015,
        "deck_vocab": 1683549848,
        "deck_kanji": 1593559119,
        "deck_kanji_words": 1178246352,
        "deck_radical": 1538186432,
        "deck_hiragana": 1562341696,
        "deck_katakana": 1473306337,
    },
    "fr": {
        "model_vocab": 1479258928,
        "model_kanji": 2018506066,
        "model_kanji_words": 1835993873,
        "model_radical": 1635955490,
        "model_kana": 1693701752,
        "deck_vocab": 1406830556,
        "deck_kanji": 1511132156,
        "deck_kanji_words": 1083476135,
        "deck_radical": 1456001352,
        "deck_hiragana": 1263595306,
        "deck_katakana": 1651686562,
    },
}

CSS = """
.card { font-family: "Noto Sans JP", "Helvetica Neue", sans-serif; font-size: 20px;
        text-align: center; color: #1a1a1a; background-color: #fafafa; }
.term { font-size: 42px; font-weight: bold; }
.kanji-big { font-size: 80px; font-weight: bold; }
.meaning { font-size: 24px; margin-top: 10px; }
.badge { font-size: 14px; color: #888; margin-top: 8px; }
.extra { font-size: 14px; color: #999; margin-top: 10px; }
.components, .story, .etymology { font-size: 15px; margin-top: 10px; text-align: left; }
.radical-list { text-align: left; }
.radical-entry { font-size: 15px; margin-top: 10px; }
.radical-examples { font-size: 13px; color: #999; margin-top: 2px; }
.word-list { text-align: left; margin-top: 15px; }
.word-entry { font-size: 16px; margin-top: 6px; }
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
            {"name": "Romaji"},
            {"name": "Meaning"},
            {"name": "PartOfSpeech"},
            {"name": "Theme"},
            {"name": "Extra"},
        ],
        templates=[
            {
                "name": "Recognition",
                "qfmt": '<div class="term">{{Expression}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="meaning">{{Meaning}}</div>'
                '<div class="badge">{{Romaji}} · {{PartOfSpeech}} | {{Theme}}</div>'
                '<div class="extra">{{Extra}}</div>',
            },
            {
                "name": "Production",
                "qfmt": '<div class="meaning">{{Meaning}}</div>'
                '<div class="badge">{{PartOfSpeech}} | {{Theme}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="term">{{Expression}}</div>'
                '<div class="badge">{{Romaji}}</div>'
                '<div class="extra">{{Extra}}</div>',
            },
            {
                "name": "FromRomaji",
                "qfmt": '<div class="meaning">{{Romaji}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="term">{{Expression}}</div>'
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


def _kanji_words_model(language: str) -> genanki.Model:
    return genanki.Model(
        IDS[language]["model_kanji_words"],
        f"Kanji Words ({language.upper()})",
        fields=[
            {"name": "Kanji"},
            {"name": "Romaji"},
            {"name": "Meaning"},
            {"name": "Words"},
        ],
        templates=[
            {
                "name": "WordsContaining",
                "qfmt": '<div class="kanji-big">{{Kanji}}</div>'
                '<div class="word-list">{{Words}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="meaning">{{Meaning}}</div>'
                '<div class="badge">{{Romaji}}</div>',
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
                "name": "Radical",
                "qfmt": '<div class="kanji-big">{{Radical}}</div>'
                '<div class="meaning">{{Meaning}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="radical-list">{{Kanjis}}</div>',
            },
        ],
        css=CSS,
    )


def _kana_model(language: str) -> genanki.Model:
    return genanki.Model(
        IDS[language]["model_kana"],
        f"Kana ({language.upper()})",
        fields=[
            {"name": "Character"},
            {"name": "Romaji"},
            {"name": "Note"},
        ],
        templates=[
            {
                "name": "Recognition",
                "qfmt": '<div class="kanji-big">{{Character}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="meaning">{{Romaji}}</div>'
                '<div class="extra">{{Note}}</div>',
            },
            {
                "name": "Production",
                "qfmt": '<div class="meaning">{{Romaji}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="kanji-big">{{Character}}</div>'
                '<div class="extra">{{Note}}</div>',
            },
        ],
        css=CSS,
    )


def _esc(value: str) -> str:
    return html.escape(value or "")


def _extra(row: dict, language: str) -> str:
    suffix = "EN" if language == "en" else "FR"
    parts = [row[f"Composition {suffix}"], row[f"Commentaire {suffix}"]]
    return "<br>".join(_esc(p) for p in parts if p and p != "-")


def _tag(value: str) -> str:
    return value.strip().lower().replace(" ", "_") if value and value != "-" else ""


def build_vocab_notes(vocab_rows: list[dict], language: str) -> list[genanki.Note]:
    model = _vocab_model(language)
    notes = []
    for row in vocab_rows:
        part_of_speech = translate_label(row["Grammaire"], language)
        theme = translate_label(row["Thème"], language)
        meaning = row["Anglais"] if language == "en" else row["Français"]
        extra = _extra(row, language)

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
                    _esc(row["Japonais"]),
                    _esc(row["Rômaji"]),
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
        suffix = "FR" if language == "fr" else "EN"
        meaning = row[f"Sens {suffix}"]
        radical_meanings = row[f"Sens Radicaux {suffix}"]
        mnemonic = row[f"Mnémotechnique {suffix}"]
        etymology = row[f"Étymologie {suffix}"]

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


def _words_html(kanji_char: str, vocab_by_kanji: dict, word_key: str, limit: int = 5) -> str:
    examples = vocab_by_kanji.get(kanji_char, [])[:limit]
    lines = []
    for ex in examples:
        entry = f"{_esc(ex['Japonais'])} ({_esc(ex['Rômaji'])})"
        if ex[word_key]:
            entry += f" - {_esc(ex[word_key])}"
        lines.append(f'<div class="word-entry">{entry}</div>')
    return "".join(lines)


def build_kanji_words_notes(
    kanji_rows: list[dict], vocab_rows: list[dict], language: str
) -> list[genanki.Note]:
    """One note per kanji that has at least one matching vocab word - kanji
    with zero matches are skipped rather than producing an empty word list.
    """
    model = _kanji_words_model(language)
    vocab_by_kanji = _vocab_index_by_kanji(vocab_rows)
    suffix = "FR" if language == "fr" else "EN"
    word_key = "Français" if language == "fr" else "Anglais"

    notes = []
    for row in kanji_rows:
        words = _words_html(row["Kanji"], vocab_by_kanji, word_key)
        if not words:
            continue
        notes.append(
            KeyedNote(
                model=model,
                fields=[
                    _esc(row["Kanji"]),
                    _esc(row["Romaji"]),
                    _esc(row[f"Sens {suffix}"]),
                    words,
                ],
                guid_key=f"kanji-words-{language}-{row['Kanji']}",
            )
        )
    return notes


def _vocab_index_by_kanji(vocab_rows: list[dict]) -> dict[str, list[dict]]:
    """Maps each individual kanji character to the vocab rows whose `Japonais`
    field contains it, in spreadsheet order. A row is indexed under every
    distinct character it contains (e.g. "都市" indexes under both 都 and
    市); non-kanji characters that ride along (okurigana, kana) get indexed
    too but are harmless, since no radical's kanji ever matches them. Only
    `Japonais` is used as the source of truth for what a word is written as -
    the `Hiragana` / `Katakana` / `Kanji` columns are never read.
    """
    index: dict[str, list[dict]] = defaultdict(list)
    for row in vocab_rows:
        for char in dict.fromkeys(row["Japonais"]):  # dedupe, keep first-seen order
            index[char].append(row)
    return index


def _examples_html(kanji_char: str, vocab_by_kanji: dict, word_key: str, limit: int = 5) -> str:
    examples = vocab_by_kanji.get(kanji_char, [])[:limit]
    if not examples:
        return ""
    parts = [
        f"{_esc(ex['Japonais'])} ({_esc(ex[word_key])})" if ex[word_key] else _esc(ex["Japonais"])
        for ex in examples
    ]
    return f'<div class="radical-examples">{", ".join(parts)}</div>'


def build_radical_notes(
    radicals: list[dict], vocab_rows: list[dict], language: str
) -> list[genanki.Note]:
    model = _radical_model(language)
    vocab_by_kanji = _vocab_index_by_kanji(vocab_rows)
    meaning_key = "MeaningFR" if language == "fr" else "MeaningEN"
    word_key = "Français" if language == "fr" else "Anglais"

    notes = []
    for radical in radicals:
        meaning = radical[meaning_key]
        blocks = []
        for k in radical["Kanjis"]:
            kanji_char = k["Kanji"]
            kanji_meaning = k[meaning_key]
            line = f"{_esc(kanji_char)} - {_esc(kanji_meaning)}" if kanji_meaning else _esc(kanji_char)
            block = f'<div class="radical-entry">{line}</div>'
            block += _examples_html(kanji_char, vocab_by_kanji, word_key)
            blocks.append(block)
        notes.append(
            KeyedNote(
                model=model,
                fields=[
                    _esc(radical["Radical"]),
                    _esc(meaning),
                    "".join(blocks),
                ],
                guid_key=f"radical-{language}-{radical['Radical']}",
            )
        )
    return notes


def build_kana_notes(kana_rows: list[dict], script: str, language: str) -> list[genanki.Note]:
    """`script` is `"Hiragana"` or `"Katakana"` - the column to read the
    character from. Rows without a character in that script (e.g. chōonpu,
    which is katakana-only) are skipped rather than producing an empty card.
    """
    model = _kana_model(language)
    notes = []
    for row in kana_rows:
        character = row[script]
        if not character or character == "(N/A)":
            continue
        # Note de prononciation is French-only prose, no English version.
        note = row["Note de prononciation"] if language == "fr" else ""
        notes.append(
            KeyedNote(
                model=model,
                fields=[
                    _esc(character),
                    _esc(row["Rōmaji"]),
                    _esc(note),
                ],
                guid_key=f"kana-{script}-{language}-{character}",
                tags=[f"type::{_tag(translate_label(row['Type'], language))}"],
            )
        )
    return notes


def _description(kind: str, language: str, count: int) -> str:
    unit = UNITS[language][kind]
    lines = [f"{count} {unit} - {GENERATED_ON[language]} {datetime.date.today().isoformat()}."]
    gap = GAP_NOTES.get((kind, language), "")
    if gap:
        lines.append(gap)
    lines.append(REIMPORT_NOTE[language])
    return "\n".join(lines)


def build_package(
    vocab_rows: list[dict],
    kanji_rows: list[dict],
    radicals: list[dict],
    kana_rows: list[dict],
    language: str,
) -> genanki.Package:
    titles = DECK_TITLES[language]
    root = titles["root"]

    vocab_deck = genanki.Deck(
        IDS[language]["deck_vocab"],
        f"{root}::{titles['vocab']}",
        description=_description("vocab", language, len(vocab_rows)),
    )
    kanji_deck = genanki.Deck(
        IDS[language]["deck_kanji"],
        f"{root}::{titles['kanji']}",
        description=_description("kanji", language, len(kanji_rows)),
    )
    kanji_words_notes = build_kanji_words_notes(kanji_rows, vocab_rows, language)
    kanji_words_deck = genanki.Deck(
        IDS[language]["deck_kanji_words"],
        f"{root}::{titles['kanji_words']}",
        description=_description("kanji_words", language, len(kanji_words_notes)),
    )
    radical_deck = genanki.Deck(
        IDS[language]["deck_radical"],
        f"{root}::{titles['radical']}",
        description=_description("radical", language, len(radicals)),
    )
    hiragana_notes = build_kana_notes(kana_rows, "Hiragana", language)
    katakana_notes = build_kana_notes(kana_rows, "Katakana", language)
    hiragana_deck = genanki.Deck(
        IDS[language]["deck_hiragana"],
        f"{root}::{titles['hiragana']}",
        description=_description("hiragana", language, len(hiragana_notes)),
    )
    katakana_deck = genanki.Deck(
        IDS[language]["deck_katakana"],
        f"{root}::{titles['katakana']}",
        description=_description("katakana", language, len(katakana_notes)),
    )

    for note in build_vocab_notes(vocab_rows, language):
        vocab_deck.add_note(note)
    for note in build_kanji_notes(kanji_rows, language):
        kanji_deck.add_note(note)
    for note in kanji_words_notes:
        kanji_words_deck.add_note(note)
    for note in build_radical_notes(radicals, vocab_rows, language):
        radical_deck.add_note(note)
    for note in hiragana_notes:
        hiragana_deck.add_note(note)
    for note in katakana_notes:
        katakana_deck.add_note(note)

    return genanki.Package(
        [vocab_deck, kanji_deck, kanji_words_deck, radical_deck, hiragana_deck, katakana_deck]
    )
