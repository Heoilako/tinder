import sqlite3
from typing import List

class DatabaseHandler:
    def __init__(self, db_name: str):
        self.db_name = db_name

    def connect(self):
        """Connect to the SQLite database."""
        return sqlite3.connect(self.db_name)

    def create_table(self):
        """Create the auth_tokens table if it doesn't already exist."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    id INTEGER PRIMARY KEY,
                    auth_token TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def insert_tokens(self, auth_tokens: List[str]):
        """Insert multiple auth tokens into the database."""
        with self.connect() as conn:
            c = conn.cursor()
            c.executemany("INSERT INTO auth_tokens (auth_token) VALUES (?)", [(token,) for token in auth_tokens])
            conn.commit()

    def fetch_all_tokens(self):
        """Fetch all auth tokens from the database."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT auth_token FROM auth_tokens")
            return c.fetchall()



# # To insert tokens
# tokens = ['token1', 'token2', 'token3']
# db_handler.insert_tokens(tokens)

# # To fetch all tokens
# all_tokens = db_handler.fetch_all_tokens()
# print(all_tokens)
