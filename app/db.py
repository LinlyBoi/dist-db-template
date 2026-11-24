"""
Database access helpers for the chat project.

Provided to students:
  - a connection pool that points at HAProxy (so node failures are survivable)
  - run_transaction(): retries on serialization conflicts and dropped connections

NOT provided (your job): idempotent writes. If a retry happens after an
ambiguous failure, your INSERT must not create a duplicate message.
Hint: client-generated message IDs + ON CONFLICT DO NOTHING.
"""
import os
import random
import time

import psycopg
from psycopg import errors
from psycopg_pool import ConnectionPool

DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://root@localhost:26257/defaultdb?sslmode=disable",
)

# Short max_lifetime and a health check make the pool drop connections to a
# node that has died instead of handing them to your code.
pool = ConnectionPool(
    DSN,
    min_size=2,
    max_size=20,
    max_lifetime=60,
    check=ConnectionPool.check_connection,
    open=False,
)


def open_pool():
    pool.open(wait=True, timeout=30)


def close_pool():
    pool.close()


# SQLSTATE 40001: serialization failure (CockroachDB asks you to retry).
# Connection-level errors happen when a node dies mid-request.
RETRYABLE = (
    errors.SerializationFailure,
    psycopg.OperationalError,
    psycopg.InterfaceError,
)


def run_transaction(fn, max_retries=8, base_delay=0.05, max_delay=2.0):
    """
    Run fn(conn) inside a transaction, retrying on retryable errors.

    fn must be safe to run more than once: it gets a fresh transaction each
    attempt, and nothing from a failed attempt is kept.

    Example:
        def send(conn):
            conn.execute("INSERT INTO messages ... VALUES (%s, %s)", (a, b))
        run_transaction(send)
    """
    attempt = 0
    while True:
        try:
            with pool.connection() as conn:
                with conn.transaction():
                    return fn(conn)
        except RETRYABLE as e:
            attempt += 1
            if attempt > max_retries:
                raise
            # Exponential backoff with full jitter
            delay = min(max_delay, base_delay * (2 ** attempt))
            time.sleep(random.uniform(0, delay))
            print(f"[retry {attempt}/{max_retries}] {type(e).__name__}: {e}")
        # Any other exception (constraint violation, bad SQL) is a real bug:
        # let it propagate.


if __name__ == "__main__":
    open_pool()
    print(run_transaction(lambda c: c.execute("SELECT version()").fetchone()))
    close_pool()
