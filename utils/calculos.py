from __future__ import annotations

import numpy as np
import pandas as pd


def safe_divide(a: float, b: float) -> float:
    if b in (0, None) or pd.isna(b):
        return 0.0
    return float(a or 0) / float(b)


def period_comparison(df: pd.DataFrame, date_col: str, value_col: str) -> tuple[float, float, float]:
    if df.empty or date_col not in df or value_col not in df:
        return 0.0, 0.0, 0.0
    data = df.dropna(subset=[date_col]).copy()
    if data.empty:
        return 0.0, 0.0, 0.0
    start, end = data[date_col].min(), data[date_col].max()
    days = max((end - start).days + 1, 1)
    previous_start = start - pd.Timedelta(days=days)
    previous_end = start - pd.Timedelta(days=1)
    current = float(data[value_col].sum())
    previous = float(df[(df[date_col] >= previous_start) & (df[date_col] <= previous_end)][value_col].sum())
    change = safe_divide(current - previous, previous) * 100 if previous else 0.0
    return current, previous, change


def calculate_abc(df: pd.DataFrame, value_col: str = "VALOR_ITEM") -> pd.DataFrame:
    if df.empty or "COD_PRODUTO" not in df:
        return pd.DataFrame()
    product_name = "DESCRICAO" if "DESCRICAO" in df.columns else "DESCRICAO_VENDA"
    agg = df.groupby(["COD_PRODUTO", product_name], dropna=False).agg(
        FATURAMENTO=(value_col, "sum"),
        QUANTIDADE=("QTDE", "sum"),
        CLIENTES=("COD_CLIENTE", "nunique"),
    ).reset_index()
    total = float(agg["FATURAMENTO"].sum())
    agg = agg.sort_values("FATURAMENTO", ascending=False)
    agg["PARTICIPACAO"] = np.where(total > 0, agg["FATURAMENTO"] / total, 0)
    agg["PARTICIPACAO_ACUMULADA"] = agg["PARTICIPACAO"].cumsum()
    agg["CURVA_ABC"] = np.select(
        [agg["PARTICIPACAO_ACUMULADA"] <= 0.80, agg["PARTICIPACAO_ACUMULADA"] <= 0.95],
        ["A", "B"],
        default="C",
    )
    return agg

