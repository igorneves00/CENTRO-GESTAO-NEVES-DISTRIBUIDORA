from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime

import pandas as pd


def only_digits_code(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().replace("\x00", "")
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".")[0]
    text = re.sub(r"\s+", "", text)
    return text


def normalize_column_name(value: object) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ").replace("\x00", "")
    text = re.sub(r"\s+", " ", text).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    return text.strip("_")


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).replace("\x00", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_decimal_series(series: pd.Series) -> pd.Series:
    text = series.astype("string").fillna("")
    text = text.str.replace("\x00", "", regex=False).str.strip()
    text = text.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    text = text.str.replace(r"[^0-9.\-]", "", regex=True)
    return pd.to_numeric(text, errors="coerce")


def parse_date_series(series: pd.Series, dayfirst: bool = True) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", dayfirst=dayfirst)


def brl(value: float | int | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        value = 0
    text = f"R$ {float(value):,.2f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def number(value: float | int | None, decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        value = 0
    text = f"{float(value):,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(value: float | int | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        value = 0
    return f"{float(value):.1f}%".replace(".", ",")


def today() -> date:
    return datetime.now().date()

