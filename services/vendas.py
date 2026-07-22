from __future__ import annotations

import pandas as pd

from utils.calculos import safe_divide


def vendas_validas(vendas: pd.DataFrame) -> pd.DataFrame:
    if vendas.empty or "VENDA_VALIDA" not in vendas:
        return pd.DataFrame()
    return vendas[vendas["VENDA_VALIDA"] == True].copy()


def faturamento_sem_duplicar_total_pedido(vendas: pd.DataFrame) -> float:
    if vendas.empty:
        return 0.0
    return float(vendas.get("VALOR_ITEM", pd.Series(dtype=float)).fillna(0).sum())


def summary_metrics(vendas: pd.DataFrame, estoque: pd.DataFrame, clientes: pd.DataFrame, meta_mensal: float) -> dict:
    validas = vendas_validas(vendas)
    faturamento = faturamento_sem_duplicar_total_pedido(validas)
    pedidos = int(validas["VENDA"].nunique()) if "VENDA" in validas else 0
    if "COD_CLIENTE" in validas and validas["COD_CLIENTE"].astype(str).str.strip().any():
        clientes_atendidos = int(validas["COD_CLIENTE"].nunique())
    elif "RAZAO_SOCIAL" in validas:
        clientes_atendidos = int(validas["RAZAO_SOCIAL"].replace("", pd.NA).dropna().nunique())
    else:
        clientes_atendidos = 0
    produtos_vendidos = float(validas["QTDE"].fillna(0).sum()) if "QTDE" in validas else 0.0
    ticket = safe_divide(faturamento, pedidos)
    valor_estoque = float(estoque.get("VALOR_ESTOQUE", pd.Series(dtype=float)).fillna(0).sum()) if not estoque.empty else 0.0
    produtos_sem_estoque = int((estoque.get("ESTOQUE_TOTAL", pd.Series(dtype=float)).fillna(0) <= 0).sum()) if not estoque.empty else 0
    clientes_total = int(clientes["COD_CLIENTE"].nunique()) if not clientes.empty and "COD_CLIENTE" in clientes else 0
    clientes_inativos = 0
    if not clientes.empty and "ULTIMA_COMPRA" in clientes:
        last = pd.to_datetime(clientes["ULTIMA_COMPRA"], errors="coerce")
        ref = max(last.max(), validas["DATA_VENDA"].max() if not validas.empty else last.max())
        clientes_inativos = int(((ref - last).dt.days >= 60).sum())
    percentual_meta = safe_divide(faturamento, meta_mensal) * 100
    return {
        "faturamento": faturamento,
        "meta_mensal": meta_mensal,
        "percentual_meta": percentual_meta,
        "falta_meta": max(meta_mensal - faturamento, 0),
        "pedidos": pedidos,
        "ticket_medio": ticket,
        "produtos_vendidos": produtos_vendidos,
        "clientes_atendidos": clientes_atendidos,
        "clientes_total": clientes_total,
        "clientes_inativos": clientes_inativos,
        "produtos_sem_estoque": produtos_sem_estoque,
        "valor_estoque": valor_estoque,
    }


def daily_revenue(vendas: pd.DataFrame) -> pd.DataFrame:
    validas = vendas_validas(vendas)
    if validas.empty:
        return pd.DataFrame(columns=["DATA", "FATURAMENTO"])
    out = validas.groupby(validas["DATA_VENDA"].dt.date).agg(FATURAMENTO=("VALOR_ITEM", "sum"), QTDE=("QTDE", "sum")).reset_index(names="DATA")
    return out


def monthly_revenue(vendas: pd.DataFrame) -> pd.DataFrame:
    validas = vendas_validas(vendas)
    if validas.empty:
        return pd.DataFrame(columns=["MES", "FATURAMENTO"])
    out = validas.copy()
    out["MES"] = out["DATA_VENDA"].dt.to_period("M").astype(str)
    return out.groupby("MES").agg(FATURAMENTO=("VALOR_ITEM", "sum"), PEDIDOS=("VENDA", "nunique")).reset_index()


def ranking(vendas: pd.DataFrame, group_col: str, value_col: str = "VALOR_ITEM", top: int = 10) -> pd.DataFrame:
    validas = vendas_validas(vendas)
    if validas.empty or group_col not in validas:
        return pd.DataFrame()
    return validas.groupby(group_col, dropna=False).agg(FATURAMENTO=(value_col, "sum"), PEDIDOS=("VENDA", "nunique"), QTDE=("QTDE", "sum")).sort_values("FATURAMENTO", ascending=False).head(top).reset_index()


def vendas_do_dia(vendas: pd.DataFrame) -> float:
    validas = vendas_validas(vendas)
    if validas.empty:
        return 0.0
    ref = validas["DATA_VENDA"].max().date()
    return float(validas[validas["DATA_VENDA"].dt.date == ref]["VALOR_ITEM"].fillna(0).sum())


def compare_periods(vendas: pd.DataFrame, group_col: str | None = None) -> pd.DataFrame:
    validas = vendas_validas(vendas)
    if validas.empty or "DATA_VENDA" not in validas:
        return pd.DataFrame()
    validas = validas.dropna(subset=["DATA_VENDA"]).copy()
    if validas.empty:
        return pd.DataFrame()
    end = validas["DATA_VENDA"].max()
    start = validas["DATA_VENDA"].min()
    days = max((end - start).days + 1, 1)
    half = max(days // 2, 1)
    split = end - pd.Timedelta(days=half)
    atual = validas[validas["DATA_VENDA"] > split]
    anterior = validas[validas["DATA_VENDA"] <= split]
    if group_col and group_col in validas:
        a = atual.groupby(group_col).agg(ATUAL=("VALOR_ITEM", "sum"), PEDIDOS_ATUAL=("VENDA", "nunique")).reset_index()
        b = anterior.groupby(group_col).agg(ANTERIOR=("VALOR_ITEM", "sum"), PEDIDOS_ANTERIOR=("VENDA", "nunique")).reset_index()
        out = a.merge(b, on=group_col, how="outer").fillna(0)
    else:
        out = pd.DataFrame([{"ATUAL": atual["VALOR_ITEM"].sum(), "ANTERIOR": anterior["VALOR_ITEM"].sum()}])
    out["VARIACAO"] = out.apply(lambda row: safe_divide(row["ATUAL"] - row["ANTERIOR"], row["ANTERIOR"]) * 100 if row["ANTERIOR"] else 0, axis=1)
    out["DIFERENCA"] = out["ATUAL"] - out["ANTERIOR"]
    return out


def compare_periodos(vendas: pd.DataFrame, group_col: str | None = None) -> pd.DataFrame:
    return compare_periods(vendas, group_col)


def abc_by_group(vendas: pd.DataFrame, group_col: str, label_col: str | None = None) -> pd.DataFrame:
    validas = vendas_validas(vendas)
    if validas.empty or group_col not in validas:
        return pd.DataFrame()
    agg = validas.groupby(group_col, dropna=False).agg(FATURAMENTO=("VALOR_ITEM", "sum"), PEDIDOS=("VENDA", "nunique")).reset_index()
    agg = agg[agg[group_col].astype(str).str.strip().ne("")]
    if agg.empty:
        return agg
    total = agg["FATURAMENTO"].sum()
    agg = agg.sort_values("FATURAMENTO", ascending=False)
    agg["PARTICIPACAO"] = agg["FATURAMENTO"] / total if total else 0
    agg["ACUMULADO"] = agg["PARTICIPACAO"].cumsum()
    agg["CURVA"] = pd.cut(agg["ACUMULADO"], bins=[0, 0.80, 0.95, 1.01], labels=["A", "B", "C"], include_lowest=True)
    return agg

