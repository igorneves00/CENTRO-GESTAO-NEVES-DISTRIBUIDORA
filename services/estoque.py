from __future__ import annotations

import pandas as pd


def estoque_parado(estoque: pd.DataFrame, vendas: pd.DataFrame) -> pd.DataFrame:
    if estoque.empty:
        return pd.DataFrame()
    out = estoque.copy()
    if not vendas.empty and "DATA_VENDA" in vendas:
        last = vendas[vendas.get("VENDA_VALIDA", False) == True].groupby("COD_PRODUTO")["DATA_VENDA"].max()
        out["ULTIMA_VENDA"] = out["COD_PRODUTO"].map(last)
        ref = vendas["DATA_VENDA"].max()
        out["DIAS_SEM_VENDA"] = (ref - out["ULTIMA_VENDA"]).dt.days
    else:
        out["ULTIMA_VENDA"] = pd.NaT
        out["DIAS_SEM_VENDA"] = None
    out["ACAO_RECOMENDADA"] = "Analisar giro antes de comprar"
    out.loc[out["DIAS_SEM_VENDA"].fillna(9999) >= 90, "ACAO_RECOMENDADA"] = "Fazer promocao ou criar kit"
    return out

