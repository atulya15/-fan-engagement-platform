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
    # connect_timeout so a retry attempt fails fast on a stalled/dropped
    # network path instead of hanging indefinitely -- without it, a bad
    # connection attempt can block far longer than the actual query would
    # ever take, masking retries as a silent hang.
    return psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=15)


def load_sql(filename: str) -> str:
    """Read a .sql file from metrics/sql/ by name (e.g. 'dau_wau_mau.sql')."""
    path = SQL_DIR / filename
    return path.read_text()


def run_query(sql: str, params: tuple | dict | None = None, max_attempts: int = 3) -> pd.DataFrame:
    """Execute a SQL string against Postgres and return a DataFrame.
    Opens and closes its own connection — fine at this query volume and
    dashboard refresh rate; a connection pool would only matter under
    concurrent multi-user load, which a single-instance Streamlit app
    serving one analyst at a time doesn't have.

    Retries with a fresh connection on transport-level failures (free-
    tier Supabase's pooled connection drops mid-stream on large result
    sets — the same "insufficient data in D message" / "lost
    synchronization with server" failure mode already documented and
    handled with retry/reconnect logic for INSERTs in generate_data.py;
    this is the same class of issue on the SELECT side, hit directly
    while building Phase 6's data snapshot and recommendation API)."""
    last_error = None
    for attempt in range(max_attempts):
        conn = get_conn()
        try:
            return pd.read_sql_query(sql, conn, params=params)
        except (psycopg2.OperationalError, psycopg2.InterfaceError, pd.errors.DatabaseError) as e:
            last_error = e
            print(f"    run_query attempt {attempt + 1}/{max_attempts} failed: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
    raise last_error


def run_sql_file(filename: str, params: tuple | dict | None = None) -> pd.DataFrame:
    """Convenience: load metrics/sql/<filename> and execute it."""
    return run_query(load_sql(filename), params=params)


def run_query_chunked(sql: str, chunksize: int = 50_000, max_attempts: int = 3) -> pd.DataFrame:
    """
    Like run_query, but fetches in `chunksize`-row batches via a
    server-side cursor instead of pulling the entire result set in one
    transfer. For very large pulls (e.g. the full widget_events table
    joined with users/widgets -- ~2M rows -- a single giant transfer
    over free-tier Supabase's pooled connection is exactly what
    triggered the "lost synchronization with server" stall this
    function was added to fix, hit directly while building the Phase 6
    recommendation API. Smaller round trips are far more resilient to
    a flaky connection than one enormous one, even though they're not
    intrinsically faster."""
    last_error = None
    for attempt in range(max_attempts):
        conn = get_conn()
        try:
            chunks = list(pd.read_sql_query(sql, conn, chunksize=chunksize))
            return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
        except (psycopg2.OperationalError, psycopg2.InterfaceError, pd.errors.DatabaseError) as e:
            last_error = e
            print(f"    run_query_chunked attempt {attempt + 1}/{max_attempts} failed: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
    raise last_error
