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

VOCAB_COLUMNS = [
    "Ordre",
    "Anglais",
    "Rômaji",
    "Japonais",
    "Alphabet",
    "Composition",
    "Thème",
    "Grammaire",
    "Propriété",
    "Commentaire",
    "Hiragana",
    "Katakana",
    "Kanji",
]

KANJI_COLUMNS = [
    "Kanji",
    "Romaji",
    "Sens (Anglais)",
    "Sens (Français)",
    "Radicaux",
    "Sens des Radicaux",
    "Mnémotechnique Visuelle",
    "Étymologie Historique",
]

SCHEMAS = {
    SHEET_VOCAB: VOCAB_COLUMNS,
    SHEET_KANJI: KANJI_COLUMNS,
}
