from __future__ import annotations

from datetime import date

import pandas as pd

from services.vendas import summary_metrics, vendas_validas
from services.vendas import compare_periods


def gerar_alertas(vendas: pd.DataFrame, estoque: pd.DataFrame, clientes: pd.DataFrame, relacionamento: dict, meta_mensal: float) -> pd.DataFrame:
    rows = []
    metrics = summary_metrics(vendas, estoque, clientes, meta_mensal)
    validas = vendas_validas(vendas)
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
        zerados = estoque[estoque.get("ESTOQUE_TOTAL", pd.Series(dtype=float)).fillna(0) <= 0]
        if not zerados.empty:
            rows.append(
                {
                    "Data": str(date.today()),
                    "Area": "Estoque",
                    "Titulo": "Produtos sem estoque",
                    "Descricao": f"{len(zerados)} produtos estao zerados ou negativos.",
                    "Gravidade": "Alta",
                    "Impacto": "Risco de perder vendas por falta de produto.",
                    "Acao recomendada": "Conferir itens prioritarios e montar lista de reposicao.",
                    "Responsavel": "Estoque",
                    "Prazo": str(date.today()),
                    "Status": "A fazer",
                }
            )
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
    if not validas.empty:
        sellers = compare_periods(vendas, "VENDEDOR")
        if not sellers.empty:
            queda = sellers[(sellers["ANTERIOR"] > 0) & (sellers["VARIACAO"] <= -20)].sort_values("VARIACAO").head(3)
            for _, row in queda.iterrows():
                rows.append(
                    {
                        "Data": str(date.today()),
                        "Area": "Comercial",
                        "Titulo": "Vendedor em queda",
                        "Descricao": f"{row['VENDEDOR']} caiu {row['VARIACAO']:.1f}% no periodo atual comparado ao anterior.",
                        "Gravidade": "Alta",
                        "Impacto": "Possivel perda de ritmo comercial.",
                        "Acao recomendada": "Revisar carteira, clientes inativos e oportunidades da semana.",
                        "Responsavel": str(row["VENDEDOR"]),
                        "Prazo": str(date.today()),
                        "Status": "A fazer",
                    }
                )
        if "CIDADE" in validas:
            cities = compare_periods(vendas, "CIDADE")
            queda_cidade = cities[(cities["ANTERIOR"] > 0) & (cities["VARIACAO"] <= -20)].sort_values("VARIACAO").head(3)
            for _, row in queda_cidade.iterrows():
                rows.append(
                    {
                        "Data": str(date.today()),
                        "Area": "Comercial",
                        "Titulo": "Cidade em queda",
                        "Descricao": f"{row['CIDADE']} caiu {row['VARIACAO']:.1f}% no periodo atual.",
                        "Gravidade": "Media",
                        "Impacto": "Reducao de faturamento regional.",
                        "Acao recomendada": "Listar clientes da cidade e planejar contato ativo.",
                        "Responsavel": "Comercial",
                        "Prazo": str(date.today()),
                        "Status": "A fazer",
                    }
                )
    if not clientes.empty and "ULTIMA_COMPRA" in clientes:
        ref = validas["DATA_VENDA"].max() if not validas.empty else pd.Timestamp.today()
        base = clientes.copy()
        base["DIAS_SEM_COMPRAR"] = (ref - pd.to_datetime(base["ULTIMA_COMPRA"], errors="coerce")).dt.days
        inativos = base[base["DIAS_SEM_COMPRAR"] >= 60]
        if not inativos.empty:
            rows.append(
                {
                    "Data": str(date.today()),
                    "Area": "Clientes",
                    "Titulo": "Clientes inativos para reativar",
                    "Descricao": f"{len(inativos)} clientes estao ha 60 dias ou mais sem comprar.",
                    "Gravidade": "Media",
                    "Impacto": "Carteira pode estar esfriando.",
                    "Acao recomendada": "Separar top clientes e iniciar reativacao por WhatsApp.",
                    "Responsavel": "Comercial",
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

