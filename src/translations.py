"""FR -> EN translations for the small, closed set of categorical values
(Grammaire, Thème, Alphabet) used to label and tag vocabulary entries.

These don't need a new spreadsheet column: the set of possible values is
small and stable enough to maintain as a static lookup here, unlike the
free-form prose fields (commentary, mnemonics, etymology, radical meanings)
which have no English content at all and need a real translated column
added upstream to support an English export.
"""

FR_TO_EN = {
    "Adjectif-i": "i-adjective",
    "Adjectif-na": "na-adjective",
    "Adverbe": "Adverb",
    "Alimentation": "Food",
    "Animal": "Animal",
    "Argent": "Money",
    "Commerce": "Commerce",
    "Communication": "Communication",
    "Compteur": "Counter",
    "Conjonction": "Conjunction",
    "Description": "Description",
    "Déterminant": "Determiner",
    "Espace": "Space",
    "Expression": "Expression",
    "G1 (vi)": "Group 1 verb (intr.)",
    "G3 (vt)": "Group 3 verb (trans.)",
    "Grammaire": "Grammar",
    "Hiragana": "Hiragana",
    "Kanji": "Kanji",
    "Katakana": "Katakana",
    "Loisir": "Leisure",
    "Maison": "House",
    "Mélange": "Mixed",
    "Mode": "Fashion",
    "Musique": "Music",
    "Nature": "Nature",
    "Nom": "Noun",
    "Nom Propre": "Proper noun",
    "Particule": "Particle",
    "Personne": "Person",
    "Pronom": "Pronoun",
    "Quantité": "Quantity",
    "Quotidien": "Daily life",
    "Santé": "Health",
    "Sport": "Sport",
    "Structure": "Structure",
    "Suffixe": "Suffix",
    "Temps": "Time",
    "Transport": "Transport",
    "Travail": "Work",
    "Verbe": "Verb",
    "École": "School",
}


def translate_label(value: str, language: str) -> str:
    if language != "en" or not value or value == "-":
        return value
    return FR_TO_EN.get(value, value)
