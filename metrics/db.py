"""
metrics/db.py
=============
Shared Postgres connection + query helper for the metrics layer.
Every metrics module loads its SQL from metrics/sql/*.sql and runs it
through `run_query`, which returns a pandas DataFrame — the format the
Streamlit dashboard (Phase 3) and notebooks both want.
"""

import os
import warnings
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# psycopg2 connections work fine with pandas despite this warning (pandas
# only formally tests SQLAlchemy engines) — suppressing rather than adding
# a SQLAlchemy dependency for no functional benefit at this scale.
warnings.filterwarnings("ignore", message=".*pandas only supports SQLAlchemy.*")

SQL_DIR = Path(__file__).parent / "sql"


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def load_sql(filename: str) -> str:
    """Read a .sql file from metrics/sql/ by name (e.g. 'dau_wau_mau.sql')."""
    path = SQL_DIR / filename
    return path.read_text()


def run_query(sql: str, params: tuple | dict | None = None) -> pd.DataFrame:
    """Execute a SQL string against Postgres and return a DataFrame.
    Opens and closes its own connection — fine at this query volume and
    dashboard refresh rate; a connection pool would only matter under
    concurrent multi-user load, which a single-instance Streamlit app
    serving one analyst at a time doesn't have."""
    conn = get_conn()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def run_sql_file(filename: str, params: tuple | dict | None = None) -> pd.DataFrame:
    """Convenience: load metrics/sql/<filename> and execute it."""
    return run_query(load_sql(filename), params=params)
