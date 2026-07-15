from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path("data/neves_gestao.db")


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db(db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mes INTEGER,
                ano INTEGER,
                tipo TEXT,
                responsavel TEXT,
                valor_meta REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alertas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                area TEXT,
                titulo TEXT,
                descricao TEXT,
                gravidade TEXT,
                impacto TEXT,
                acao_recomendada TEXT,
                responsavel TEXT,
                prazo TEXT,
                status TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plano_acao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problema TEXT,
                acao TEXT,
                area TEXT,
                responsavel TEXT,
                data_criacao TEXT,
                prazo TEXT,
                prioridade TEXT,
                status TEXT,
                observacao TEXT,
                resultado_esperado TEXT,
                resultado_alcancado TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historico_importacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT,
                arquivo TEXT,
                data_importacao TEXT DEFAULT CURRENT_TIMESTAMP,
                linhas INTEGER,
                registros_validos INTEGER,
                registros_invalidos INTEGER,
                duplicidades INTEGER,
                periodo TEXT,
                erros_relacionamento TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT
            )
            """
        )
        conn.execute("INSERT OR IGNORE INTO configuracoes(chave, valor) VALUES('meta_mensal_empresa', '500000')")
        conn.commit()


def replace_table(name: str, df: pd.DataFrame, db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        df.to_sql(name, conn, if_exists="replace", index=False)


def read_table(name: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    with get_connection(db_path) as conn:
        try:
            return pd.read_sql_query(f"SELECT * FROM {name}", conn)
        except Exception:
            return pd.DataFrame()


def write_import_history(rows: list[dict], db_path: Path = DB_PATH) -> None:
    if not rows:
        return
    with get_connection(db_path) as conn:
        pd.DataFrame(rows).to_sql("historico_importacoes", conn, if_exists="append", index=False)


def get_config(key: str, default: str = "", db_path: Path = DB_PATH) -> str:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT valor FROM configuracoes WHERE chave = ?", (key,)).fetchone()
    return row[0] if row else default


def set_config(key: str, value: str, db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.execute("INSERT OR REPLACE INTO configuracoes(chave, valor) VALUES(?, ?)", (key, value))
        conn.commit()

