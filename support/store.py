"""SQLite-backed simulation. A write lock spans authorization and ledger commit."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3

from support.config import ROOT


class Store:
    def __init__(self, path=None):
        self.path = str(path or os.environ.get('SUPPORT_DB') or ROOT / 'state/support.db')
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, customer TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL)')
            fixture = (ROOT / 'data/fixtures.json').read_text()
            db.execute('INSERT OR IGNORE INTO state VALUES (1, ?)', (fixture,))

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    @contextmanager
    def transaction(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state = json.loads(db.execute('SELECT value FROM state WHERE id=1').fetchone()[0])
            yield state
            db.execute('UPDATE state SET value=? WHERE id=1', (json.dumps(state),))

    def snapshot(self):
        with self.connect() as db:
            return json.loads(db.execute('SELECT value FROM state WHERE id=1').fetchone()[0])

    def identify(self, identity):
        key = identity.strip().lower()
        return next((c['id'] for c in self.snapshot()['customers']
                     if key in (c['id'].lower(), c['email'].lower())), None)

    def history(self, customer):
        with self.connect() as db:
            rows = db.execute('SELECT role,content FROM history WHERE customer=? ORDER BY id DESC LIMIT 12', (customer,)).fetchall()
        return [{'role': role, 'content': content} for role, content in reversed(rows)]

    def remember(self, customer, message, result):
        with self.connect() as db:
            db.executemany('INSERT INTO history(customer,role,content) VALUES(?,?,?)',
                           [(customer, 'user', message[:6000]),
                            (customer, 'assistant', json.dumps(result)[:12000])])
