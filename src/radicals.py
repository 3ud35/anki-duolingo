"""Isolates individual radicals out of the `Analyse clés kanjis` tab.

`Radicaux` / `Sens des Radicaux` hold one or more radicals per kanji as
parallel, comma-separated lists. A radical token can itself carry a
parenthesized note (an alternate/traditional form, e.g. "阝 (邑)"), which must
not be split on, and must be stripped off since it's about a different
character, not the radical actually used here.

The same radical repeats across many kanji, generally with near-identical
meanings that only differ in capitalization or level of detail (this dataset
is machine-generated) - so for each radical we keep whichever phrasing (once
lowercased) was seen most often.

Some rows have more radicals than meanings (a stray/unexplained radical).
Rather than discarding the whole row, any radical in it that's already known
from a clean row elsewhere still gets credited with that kanji - only the
genuinely unknown radical (no meaning anywhere in the dataset) is left out.
"""

import re
from collections import Counter, defaultdict

NO_RADICAL_MARKERS = {"-", "", "aucun", "(aucun)"}


def extract_radicals(kanji_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Returns (radicals, unresolved).

    `radicals` is one entry per unique radical: {"Radical", "Meaning", "Kanjis"}.
    `unresolved` lists radicals that appear in the data but have no meaning
    anywhere to derive - these need a fix in the source spreadsheet.
    """
    clean_rows, mismatched_rows = [], []

    for row in kanji_rows:
        radicals_field = row["Radicaux"].strip()
        if radicals_field.lower() in NO_RADICAL_MARKERS:
            continue

        radical_tokens = [_strip_note(t) for t in _split_top_level(radicals_field)]
        sense_tokens = [
            _strip_note(t).lower()
            for t in _split_top_level(row["Sens des Radicaux"].strip())
        ]

        if len(radical_tokens) == len(sense_tokens):
            clean_rows.append((row["Kanji"], radical_tokens, sense_tokens))
        else:
            mismatched_rows.append((row["Kanji"], radical_tokens))

    kanjis_by_radical: dict[str, list[str]] = defaultdict(list)
    senses_by_radical: dict[str, Counter] = defaultdict(Counter)

    for kanji, radical_tokens, sense_tokens in clean_rows:
        for radical, sense in zip(radical_tokens, sense_tokens):
            kanjis_by_radical[radical].append(kanji)
            senses_by_radical[radical][sense] += 1

    known_radicals = set(kanjis_by_radical)
    unresolved = []

    for kanji, radical_tokens in mismatched_rows:
        for radical in radical_tokens:
            if radical in known_radicals:
                kanjis_by_radical[radical].append(kanji)
            else:
                unresolved.append({"Kanji": kanji, "Radical": radical})

    radicals = [
        {
            "Radical": radical,
            "Meaning": senses_by_radical[radical].most_common(1)[0][0],
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
