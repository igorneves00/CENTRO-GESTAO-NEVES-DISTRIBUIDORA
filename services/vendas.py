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
    if "TOTAL_VENDA" in vendas and "VENDA" in vendas:
        pedido = vendas.dropna(subset=["VENDA"]).drop_duplicates(subset=["VENDA"])
        total = float(pedido["TOTAL_VENDA"].fillna(0).sum())
        if total > 0:
            return total
    return float(vendas.get("VALOR_ITEM", pd.Series(dtype=float)).fillna(0).sum())


def summary_metrics(vendas: pd.DataFrame, estoque: pd.DataFrame, clientes: pd.DataFrame, meta_mensal: float) -> dict:
    validas = vendas_validas(vendas)
    faturamento = faturamento_sem_duplicar_total_pedido(validas)
    pedidos = int(validas["VENDA"].nunique()) if "VENDA" in validas else 0
    clientes_atendidos = int(validas["COD_CLIENTE"].nunique()) if "COD_CLIENTE" in validas else 0
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

