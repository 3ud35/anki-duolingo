"""Isolates individual radicals out of the `Analyse clés kanjis` tab.

`Radicaux` holds one or more radicals per kanji as a comma-separated list,
paralleled by `Sens Radicaux EN` / `Sens Radicaux FR` (one sense list per
language). A radical token can itself carry a parenthesized note (an
alternate/traditional form, e.g. "阝 (邑)"), which must not be split on, and
must be stripped off since it's about a different character, not the radical
actually used here.

The same radical repeats across many kanji, generally with near-identical
meanings that only differ in capitalization or level of detail (this dataset
is machine-generated) - so for each radical/language we keep whichever
phrasing (once lowercased) was seen most often.

Some rows have more radicals than meanings in a given language (a
stray/unexplained radical, or a translation that didn't preserve parity).
Rather than discarding the whole row, any radical in it that's already known
from a clean row elsewhere (in that language) still gets credited with that
kanji - only a radical genuinely unknown in that language anywhere in the
dataset is reported as unresolved. The `Kanjis` list itself (which kanji use
a given radical) is language-independent and always built from every row,
regardless of whether either language's sense list lines up.
"""

import re
from collections import Counter, defaultdict

NO_RADICAL_MARKERS = {"-", "", "aucun", "(aucun)"}

SENSE_COLUMNS = {"EN": "Sens Radicaux EN", "FR": "Sens Radicaux FR"}


def extract_radicals(kanji_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Returns (radicals, unresolved).

    `radicals` is one entry per unique radical:
    {"Radical", "MeaningEN", "MeaningFR", "Kanjis"}, where `Kanjis` is a list
    of {"Kanji", "MeaningEN", "MeaningFR"} - each kanji using this radical
    together with its own meaning, not just the bare character.
    `unresolved` lists {"Kanji", "Radical", "Language"} combos where no
    meaning could be derived anywhere in the dataset for that language -
    these need a fix in the source spreadsheet.
    """
    kanjis_by_radical: dict[str, list[dict]] = defaultdict(list)
    rows = []

    for row in kanji_rows:
        radicals_field = row["Radicaux"].strip()
        if radicals_field.lower() in NO_RADICAL_MARKERS:
            continue

        radical_tokens = [_strip_note(t) for t in _split_top_level(radicals_field)]
        for radical in radical_tokens:
            kanjis_by_radical[radical].append(
                {
                    "Kanji": row["Kanji"],
                    "MeaningEN": row["Sens EN"],
                    "MeaningFR": row["Sens FR"],
                }
            )
        rows.append((row["Kanji"], radical_tokens, row))

    meanings: dict[str, dict[str, str]] = {}
    unresolved = []

    for language, column in SENSE_COLUMNS.items():
        senses_by_radical: dict[str, Counter] = defaultdict(Counter)
        mismatched_rows = []

        for kanji, radical_tokens, row in rows:
            sense_tokens = [
                _strip_note(t).lower() for t in _split_top_level(row[column].strip())
            ]
            if len(radical_tokens) == len(sense_tokens):
                for radical, sense in zip(radical_tokens, sense_tokens):
                    senses_by_radical[radical][sense] += 1
            else:
                mismatched_rows.append((kanji, radical_tokens))

        known_radicals = {r for r, counts in senses_by_radical.items() if counts}
        for kanji, radical_tokens in mismatched_rows:
            for radical in radical_tokens:
                if radical not in known_radicals:
                    unresolved.append(
                        {"Kanji": kanji, "Radical": radical, "Language": language}
                    )

        meanings[language] = {
            radical: counts.most_common(1)[0][0]
            for radical, counts in senses_by_radical.items()
            if counts
        }

    radicals = [
        {
            "Radical": radical,
            "MeaningEN": meanings["EN"].get(radical, ""),
            "MeaningFR": meanings["FR"].get(radical, ""),
            "Kanjis": kanjis_by_radical[radical],
        }
        for radical in kanjis_by_radical
    ]
    return radicals, unresolved


def _split_top_level(value: str) -> list[str]:
    """Splits on commas, except commas found inside parentheses."""
    tokens, depth, current = [], 0, ""
    for char in value:
        if char == "(":
            depth += 1
            current += char
        elif char == ")":
            depth -= 1
            current += char
        elif char == "," and depth == 0:
            tokens.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        tokens.append(current.strip())
    return tokens


def _strip_note(token: str) -> str:
    return re.sub(r"\s*\([^)]*\)\s*$", "", token).strip()
