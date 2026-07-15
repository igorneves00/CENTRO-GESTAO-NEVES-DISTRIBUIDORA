from __future__ import annotations

import pandas as pd
import plotly.express as px


NEVES_COLORS = ["#f4c400", "#161616", "#777777", "#f0d75a", "#404040"]


def bar(df: pd.DataFrame, x: str, y: str, title: str, orientation: str = "v"):
    fig = px.bar(df, x=x, y=y, title=title, color_discrete_sequence=NEVES_COLORS, orientation=orientation)
    fig.update_layout(margin=dict(l=10, r=10, t=45, b=10), plot_bgcolor="white", paper_bgcolor="white")
    return fig


def line(df: pd.DataFrame, x: str, y: str, title: str):
    fig = px.line(df, x=x, y=y, title=title, markers=True, color_discrete_sequence=["#f4c400"])
    fig.update_layout(margin=dict(l=10, r=10, t=45, b=10), plot_bgcolor="white", paper_bgcolor="white")
    return fig

