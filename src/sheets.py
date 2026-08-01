import csv
import io

import requests

from src.schema import SCHEMAS

GVIZ_URL = "https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq"


def fetch_sheet_rows(spreadsheet_id: str, sheet_name: str) -> list[dict]:
    return _fetch(spreadsheet_id, {"sheet": sheet_name}, sheet_name)


def fetch_sheet_rows_by_gid(spreadsheet_id: str, gid: int) -> list[dict]:
    return _fetch(spreadsheet_id, {"gid": gid}, gid)


def _fetch(spreadsheet_id: str, query: dict, label) -> list[dict]:
    response = requests.get(
        GVIZ_URL.format(spreadsheet_id=spreadsheet_id),
        params={"tqx": "out:csv", **query},
        timeout=30,
    )
    response.raise_for_status()
    if "text/csv" not in response.headers.get("Content-Type", ""):
        raise RuntimeError(
            f"Expected CSV from sheet {label!r}, got "
            f"{response.headers.get('Content-Type')!r}. The spreadsheet may no "
            "longer be shared as 'anyone with the link can view'."
        )

    reader = csv.DictReader(io.StringIO(response.text))
    rows = [
        {key: value.strip() for key, value in row.items() if key}
        for row in reader
    ]

    expected_columns = SCHEMAS.get(label)
    if expected_columns is not None:
        actual_columns = [field for field in (reader.fieldnames or []) if field]
        if actual_columns != expected_columns:
            raise RuntimeError(
                f"Column mismatch on sheet {label!r}.\n"
                f"Expected: {expected_columns}\n"
                f"Got:      {actual_columns}\n"
                "The spreadsheet layout changed upstream; update src/schema.py."
            )

    return rows
