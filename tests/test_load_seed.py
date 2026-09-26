import csv
import importlib.util
import sqlite3

import pytest

import load_seed

ROOT = load_seed.ROOT


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "app.db"
    load_seed.load(path)
    return path


def dump(db_path):
    """Every table as {name: (columns, sorted rows)}."""
    with sqlite3.connect(db_path) as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        result = {}
        for table in tables:
            cursor = conn.execute(f'SELECT * FROM "{table}"')
            columns = [d[0] for d in cursor.description]
            result[table] = (columns, sorted(cursor.fetchall()))
        return result


def read_csv(name):
    with (ROOT / "seed" / name).open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        return next(reader), list(reader)


@pytest.mark.parametrize("table", ["tickets", "customers"])
def test_table_matches_csv(db_path, table):
    header, rows = read_csv(f"{table}.csv")
    columns, stored = dump(db_path)[table]
    assert columns == header
    as_text = sorted([str(value) for value in row] for row in stored)
    assert as_text == sorted(rows)


def test_column_names_match_mcp_server(db_path):
    tables = dump(db_path)
    assert tables["tickets"][0] == ["ticket_id", "customer_id", "created_at", "text"]
    assert tables["customers"][0] == ["customer_id", "name", "plan", "open_tickets"]


def test_open_tickets_is_integer(db_path):
    with sqlite3.connect(db_path) as conn:
        types = {r[0] for r in conn.execute("SELECT typeof(open_tickets) FROM customers")}
        busy = conn.execute("SELECT customer_id FROM customers WHERE open_tickets >= 3").fetchall()
    _, rows = read_csv("customers.csv")
    assert types == {"integer"}
    assert {r[0] for r in busy} == {row[0] for row in rows if int(row[3]) >= 3}


def test_loading_twice_gives_the_same_database(db_path):
    first = dump(db_path)
    load_seed.load(db_path)
    assert dump(db_path) == first


def test_failed_load_keeps_the_previous_data(db_path, tmp_path):
    before = dump(db_path)
    bad_seed = tmp_path / "seed"
    bad_seed.mkdir()
    (bad_seed / "tickets.csv").write_text((ROOT / "seed" / "tickets.csv").read_text())
    # A row with too many fields makes the customers insert fail mid-load.
    (bad_seed / "customers.csv").write_text("customer_id,name,plan,open_tickets\nC-1,A,Team,0,extra\n")
    with pytest.raises(sqlite3.Error):
        load_seed.load(db_path, bad_seed)
    assert dump(db_path) == before


def test_missing_seed_file_creates_no_database(tmp_path):
    path = tmp_path / "app.db"
    with pytest.raises(FileNotFoundError):
        load_seed.load(path, tmp_path / "no-seed")
    assert not path.exists()


def test_mcp_server_reads_the_loaded_database(db_path, monkeypatch):
    # Load by file path: the repo's mcp/ folder shares its name with the
    # installed mcp package, so it cannot be imported as `mcp.triage_server`.
    spec = importlib.util.spec_from_file_location(
        "triage_server", ROOT / "mcp" / "triage_server.py"
    )
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    monkeypatch.setattr(server, "DB_PATH", db_path)

    ticket = server.get_ticket("T-1042")
    assert ticket["customer_id"] == "C-77"
    history = server.get_customer_history("C-77")
    assert "T-1042" in history["ticket_ids"]
