"""Load seed/tickets.csv and seed/customers.csv into app.db.

Run with `uv run python load_seed.py`. Each run rebuilds both tables from the
CSV files, so running it twice gives the same database as running it once.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "app.db"
SEED_DIR = ROOT / "seed"

# Table name -> seed file. Column names come from each file's header row.
TABLES = {"tickets": "tickets.csv", "customers": "customers.csv"}

# Stored as INTEGER so the Enterprise rule (3 or more open tickets) compares
# numerically; every other column is TEXT.
INTEGER_COLUMNS = {"open_tickets"}


def _read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        return header, list(reader)


def load(db_path: Path = DB_PATH, seed_dir: Path = SEED_DIR) -> dict[str, int]:
    """Rebuild every table in `TABLES` inside `db_path`; return row counts."""
    # Read every file before connecting, so a missing seed file cannot leave
    # an empty app.db behind.
    seeds = {table: _read_csv(seed_dir / name) for table, name in TABLES.items()}
    counts: dict[str, int] = {}
    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        conn.execute("BEGIN")
        for table, (header, rows) in seeds.items():
            columns = ", ".join(
                f'"{name}" {"INTEGER" if name in INTEGER_COLUMNS else "TEXT"}'
                for name in header
            )
            placeholders = ", ".join("?" for _ in header)
            conn.execute(f'DROP TABLE IF EXISTS "{table}"')
            conn.execute(f'CREATE TABLE "{table}" ({columns})')
            conn.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})', rows)
            counts[table] = len(rows)
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return counts


def main() -> None:
    counts = load()
    summary = ", ".join(f"{count} {table}" for table, count in counts.items())
    print(f"Loaded {summary} into {DB_PATH.name}")


if __name__ == "__main__":
    main()
