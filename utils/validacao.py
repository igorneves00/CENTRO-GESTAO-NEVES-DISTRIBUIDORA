from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class ValidationResult:
    valid_rows: int
    invalid_rows: int
    duplicated_rows: int
    invalid_dates: int = 0
    invalid_values: int = 0


def count_duplicates(df: pd.DataFrame, subset: list[str] | None = None) -> int:
    if df.empty:
        return 0
    if subset:
        subset = [col for col in subset if col in df.columns]
    return int(df.duplicated(subset=subset or None).sum())

