import sqlite3
from typing import List, Tuple, Optional, Dict

class DatabaseHandler:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.create_tables()

    def connect(self):
        """Connect to the SQLite database."""
        return sqlite3.connect(self.db_name)

    def create_tables(self):
        """Create necessary tables if they don't already exist."""
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
            c.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    group_id INTEGER PRIMARY KEY,
                    group_name TEXT NOT NULL UNIQUE
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS group_members (
                    group_id INTEGER,
                    auth_token TEXT,
                    FOREIGN KEY (group_id) REFERENCES groups (group_id),
                    FOREIGN KEY (auth_token) REFERENCES auth_tokens (auth_token),
                    UNIQUE (group_id, auth_token)
                )
            ''')
            conn.commit()

    def insert_tokens(self, tokens_with_proxies: List[Tuple[str, str, str]]):
        """Insert multiple auth tokens into the database, along with their proxy settings."""
        with self.connect() as conn:
            c = conn.cursor()
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
                return {'http': http_proxy, 'https': https_proxy} if http_proxy or https_proxy else None
            return None

    def remove_token(self, auth_token: str):
        """Remove a specific auth token from the database."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM auth_tokens WHERE auth_token = ?", (auth_token,))
            conn.commit()

    def create_group(self, group_name: str):
        """Create a new group."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO groups (group_name) VALUES (?)", (group_name,))
            conn.commit()

    def remove_group(self, group_name: str):
        """Remove a group and its memberships."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM groups WHERE group_name = ?", (group_name,))
            conn.commit()

    def fetch_group_tokens(self, group_name: str) -> List[str]:
        """Fetch all auth tokens associated with a given group."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT auth_token FROM group_members
                JOIN groups ON group_members.group_id = groups.group_id
                WHERE group_name = ?
            ''', (group_name,))
            return [row[0] for row in c.fetchall()]

    def add_token_to_group(self, auth_token: str, group_name: str):
        """Add an auth token to a group."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT group_id FROM groups WHERE group_name = ?", (group_name,))
            group_id = c.fetchone()[0]
            c.execute("INSERT INTO group_members (group_id, auth_token) VALUES (?, ?)", (group_id, auth_token))
            conn.commit()

    def remove_token_from_group(self, auth_token: str, group_name: str):
        """Add an auth token to a group."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("DELETE group_id FROM groups WHERE group_name = ?", (group_name,))
            group_id = c.fetchone()[0]
            c.execute("DELETE INTO group_members (group_id, auth_token) VALUES (?, ?)", (group_id, auth_token))
            conn.commit()