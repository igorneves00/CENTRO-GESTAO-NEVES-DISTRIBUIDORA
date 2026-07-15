from __future__ import annotations

from datetime import date

import pandas as pd

from services.vendas import summary_metrics, vendas_validas


def gerar_alertas(vendas: pd.DataFrame, estoque: pd.DataFrame, clientes: pd.DataFrame, relacionamento: dict, meta_mensal: float) -> pd.DataFrame:
    rows = []
    metrics = summary_metrics(vendas, estoque, clientes, meta_mensal)
    if metrics["faturamento"] < meta_mensal:
        rows.append(
            {
                "Data": str(date.today()),
                "Area": "Comercial",
                "Titulo": "Faturamento abaixo da meta",
                "Descricao": f"Meta mensal ainda nao atingida. Falta R$ {metrics['falta_meta']:.2f}.",
                "Gravidade": "Alta" if metrics["percentual_meta"] < 70 else "Media",
                "Impacto": "Risco de fechamento abaixo do objetivo.",
                "Acao recomendada": "Priorizar clientes ativos e reativacao.",
                "Responsavel": "Gestor comercial",
                "Prazo": str(date.today()),
                "Status": "A fazer",
            }
        )
    if not estoque.empty:
        negativos = estoque[estoque["ESTOQUE_TOTAL"] < 0]
        if not negativos.empty:
            rows.append(
                {
                    "Data": str(date.today()),
                    "Area": "Estoque",
                    "Titulo": "Produtos com estoque negativo",
                    "Descricao": f"{len(negativos)} produtos estao com estoque negativo.",
                    "Gravidade": "Critica",
                    "Impacto": "Risco de venda sem disponibilidade real.",
                    "Acao recomendada": "Conferir saldo fisico e ajustar origem da divergencia.",
                    "Responsavel": "Estoque",
                    "Prazo": str(date.today()),
                    "Status": "A fazer",
                }
            )
    for key, value in relacionamento.items():
        if "sem" in key and value:
            rows.append(
                {
                    "Data": str(date.today()),
                    "Area": "Dados",
                    "Titulo": "Codigos sem correspondencia",
                    "Descricao": f"{key}: {value}",
                    "Gravidade": "Media",
                    "Impacto": "Indicadores por cliente/produto podem ficar incompletos.",
                    "Acao recomendada": "Revisar cadastros e padronizacao de codigos.",
                    "Responsavel": "Administrativo",
                    "Prazo": str(date.today()),
                    "Status": "A fazer",
                }
            )
    return pd.DataFrame(rows)

