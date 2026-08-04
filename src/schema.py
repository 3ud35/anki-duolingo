"""Local record of the spreadsheet's tab names and expected columns.

The spreadsheet is fed by an external, evolving pipeline, so ingestion
validates the live headers against this schema on every fetch and fails
loudly if they've drifted, instead of silently mis-mapping columns.

Tab names and column headers below are literal strings from the source
spreadsheet (French), kept verbatim since they're keys into external data,
not descriptive code content.
"""

SHEET_VOCAB = "MOTS"
SHEET_KANJI = "Analyse clés kanjis"
# This tab's name is unknown (not exposed by the public CSV endpoint used
# for gid-based access), so it's identified by gid instead of by name.
SHEET_KANA_GID = 496685825

VOCAB_COLUMNS = [
    "Ordre",
    "Anglais",
    "Français",
    "Rômaji",
    "Japonais",
    "Alphabet",
    "Composition EN",
    "Composition FR",
    "Thème",
    "Grammaire",
    "Propriété",
    "Commentaire EN",
    "Commentaire FR",
    "Hiragana",
    "Katakana",
    "Kanji",
]

KANJI_COLUMNS = [
    "Kanji",
    "Romaji",
    "Sens EN",
    "Sens FR",
    "Radicaux",
    "Sens Radicaux EN",
    "Sens Radicaux FR",
    "Mnémotechnique EN",
    "Mnémotechnique FR",
    "Étymologie EN",
    "Étymologie FR",
]

KANA_COLUMNS = [
    "Groupe",
    "Rōmaji",
    "Hiragana",
    "Katakana",
    "Type",
    "Note de prononciation",
]

SCHEMAS = {
    SHEET_VOCAB: VOCAB_COLUMNS,
    SHEET_KANJI: KANJI_COLUMNS,
    SHEET_KANA_GID: KANA_COLUMNS,
}
