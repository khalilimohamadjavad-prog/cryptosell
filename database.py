import sqlite3, os, json
from datetime import datetime
class Database:
    def __init__(self, db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()
    def _init(self):
        cur=self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS signals (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, type TEXT, severity TEXT, payload TEXT, drop_pct REAL, generated_at TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, level TEXT, message TEXT, ts TEXT)''')
        self.conn.commit()
    def insert_signal(self, sig):
        cur=self.conn.cursor(); cur.execute('INSERT INTO signals (symbol,type,severity,payload,drop_pct,generated_at) VALUES (?,?,?,?,?,?)', (sig['symbol'], sig.get('type',''), sig.get('severity',''), json.dumps(sig.get('payload',{})), sig.get('drop_pct',0.0), datetime.utcnow().isoformat())); self.conn.commit(); return cur.lastrowid
    def fetch_signals(self, limit=100):
        cur=self.conn.cursor(); cur.execute('SELECT * FROM signals ORDER BY id DESC LIMIT ?', (limit,)); rows=cur.fetchall(); return [dict(r) for r in rows]
    def insert_log(self, level, message):
        cur=self.conn.cursor(); cur.execute('INSERT INTO logs (level,message,ts) VALUES (?,?,?)', (level, message, datetime.utcnow().isoformat())); self.conn.commit()
