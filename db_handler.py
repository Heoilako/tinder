import sqlite3
from typing import List, Tuple, Optional, Dict

class DatabaseHandler:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.create_table()

    def connect(self):
        """Connect to the SQLite database."""
        return sqlite3.connect(self.db_name)

    def create_table(self):
        """Create the auth_tokens table if it doesn't already exist, with proxy columns."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    id INTEGER PRIMARY KEY,
                    auth_token TEXT NOT NULL,
                    http_proxy TEXT,
                    https_proxy TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def insert_tokens(self, tokens_with_proxies: List[Tuple[str, str, str]]):
        """Insert multiple auth tokens into the database, along with their proxy settings."""
        with self.connect() as conn:
            c = conn.cursor()
            # Each tuple in tokens_with_proxies should have the format: (auth_token, http_proxy, https_proxy)
            c.executemany("INSERT INTO auth_tokens (auth_token, http_proxy, https_proxy) VALUES (?, ?, ?)", tokens_with_proxies)
            conn.commit()

    def fetch_all_tokens(self) -> List[Tuple[str, str, str]]:
        """Fetch all auth tokens and their proxies from the database."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT auth_token, http_proxy, https_proxy FROM auth_tokens")
            return c.fetchall()

    def fetch_proxy_for_token(self, auth_token: str) -> Optional[Dict[str, str]]:
        """Fetch proxy settings for a specific auth token."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT http_proxy, https_proxy FROM auth_tokens WHERE auth_token = ?", (auth_token,))
            result = c.fetchone()
            if result:
                http_proxy, https_proxy = result
                proxy_dict = {}
                if http_proxy:
                    proxy_dict['http'] = http_proxy
                if https_proxy:
                    proxy_dict['https'] = https_proxy
                return proxy_dict
            return None

    def remove_token(self, auth_token: str):
        """Remove a specific auth token from the database, along with its proxy settings."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM auth_tokens WHERE auth_token = ?", (auth_token,))
            conn.commit()
