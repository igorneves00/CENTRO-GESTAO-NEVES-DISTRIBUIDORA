from __future__ import annotations

import pandas as pd

from services.estoque import estoque_parado
from services.vendas import ranking, summary_metrics
from utils.formatacao import brl


def responder(pergunta: str, vendas: pd.DataFrame, estoque: pd.DataFrame, clientes: pd.DataFrame, meta_mensal: float) -> dict:
    pergunta_norm = pergunta.lower().strip()
    metrics = summary_metrics(vendas, estoque, clientes, meta_mensal)
    if not pergunta_norm:
        return {"resposta": "Digite uma pergunta para a Neves IA.", "dados": "", "acao": "", "prioridade": "Baixa"}
    if "falta" in pergunta_norm and "meta" in pergunta_norm:
        return {
            "resposta": f"Faltam {brl(metrics['falta_meta'])} para atingir a meta mensal.",
            "dados": f"Faturamento atual: {brl(metrics['faturamento'])}; meta: {brl(meta_mensal)}.",
            "acao": "Acompanhar vendedores e priorizar clientes de maior ticket.",
            "prioridade": "Alta" if metrics["falta_meta"] > 0 else "Baixa",
        }
    if "produto" in pergunta_norm and ("acabar" in pergunta_norm or "comprar" in pergunta_norm):
        if estoque.empty:
            return insuficiente()
        low = estoque.sort_values("ESTOQUE_TOTAL").head(10)
        return {
            "resposta": "Os produtos com menor saldo aparecem na lista relacionada.",
            "dados": low[["COD_PRODUTO", "DESCRICAO_ESTOQUE", "ESTOQUE_TOTAL"]].to_string(index=False),
            "acao": "Conferir giro antes de comprar automaticamente.",
            "prioridade": "Alta",
        }
    if "parado" in pergunta_norm:
        parado = estoque_parado(estoque, vendas)
        if parado.empty:
            return insuficiente()
        lista = parado.sort_values("DIAS_SEM_VENDA", ascending=False).head(10)
        return {
            "resposta": "Produtos com mais dias sem venda foram identificados.",
            "dados": lista[["COD_PRODUTO", "DESCRICAO_ESTOQUE", "ESTOQUE_TOTAL", "DIAS_SEM_VENDA"]].to_string(index=False),
            "acao": "Avaliar promocao, kit ou suspensao de compra.",
            "prioridade": "Media",
        }
    if "vendedor" in pergunta_norm:
        top = ranking(vendas, "VENDEDOR", top=10)
        if top.empty:
            return insuficiente()
        return {
            "resposta": "Ranking de vendedores calculado pelo faturamento dos itens vendidos.",
            "dados": top.to_string(index=False),
            "acao": "Comparar resultado com metas individuais quando cadastradas.",
            "prioridade": "Media",
        }
    return insuficiente()


def insuficiente() -> dict:
    return {
        "resposta": "Nao existem dados suficientes para responder com seguranca.",
        "dados": "",
        "acao": "Carregar os arquivos necessarios ou refinar a pergunta.",
        "prioridade": "Baixa",
    }

