from __future__ import annotations

import pandas as pd
import streamlit as st

from services.alertas import gerar_alertas
from utils.exportacao import dataframe_to_csv_bytes


def render(ctx: dict) -> None:
    st.title("Alertas")
    alertas = gerar_alertas(ctx["frames"].get("vendas", pd.DataFrame()), ctx["frames"].get("estoque", pd.DataFrame()), ctx["frames"].get("clientes", pd.DataFrame()), ctx["relationship"], ctx["meta_mensal"])
    if alertas.empty:
        st.success("Nenhum alerta automatico gerado com os filtros atuais.")
        return
    st.dataframe(alertas, width="stretch", hide_index=True)
    st.download_button("Exportar alertas CSV", dataframe_to_csv_bytes(alertas), "alertas.csv")

