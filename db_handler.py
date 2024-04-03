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
           # Updated swipe_settings table creation with left_swipe_percentage
            c.execute('''
                CREATE TABLE IF NOT EXISTS swipe_settings (
                    id INTEGER PRIMARY KEY,
                    start_hour INTEGER,
                    end_hour INTEGER,
                    likes_per_day INTEGER,
                    left_swipe_percentage REAL DEFAULT 0
                )
            ''')
            # Ensure there's always one row present for simplicity
            c.execute('''
                INSERT OR IGNORE INTO swipe_settings (id, start_hour, end_hour, likes_per_day, left_swipe_percentage) 
                VALUES (1, 0, 0, 0, 0)
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

    def create_group(self, group_name: str) -> str:
        """Create a new group if it doesn't already exist."""
        with self.connect() as conn:
            c = conn.cursor()
            
            # Check if the group already exists
            c.execute("SELECT 1 FROM groups WHERE group_name = ?", (group_name,))
            if c.fetchone():
                return f"Group '{group_name}' already exists."
            
            # Insert the new group since it doesn't exist
            c.execute("INSERT INTO groups (group_name) VALUES (?)", (group_name,))
            conn.commit()
            return f"Group '{group_name}' created successfully."


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

    def add_token_to_group(self, auth_token: str, group_name: str) -> str:
        """Add an auth token to a group if the group exists."""
        with self.connect() as conn:
            c = conn.cursor()

            # Check if the group exists
            c.execute("SELECT group_id FROM groups WHERE group_name = ?", (group_name,))
            group_row = c.fetchone()

            if group_row is None:
                return f"Group '{group_name}' does not exist."

            group_id = group_row[0]

            # Check if the token is already in the group
            c.execute("SELECT 1 FROM group_members WHERE group_id = ? AND auth_token = ?", (group_id, auth_token))
            if c.fetchone():
                return f"Token already in group '{group_name}'."

            # Add the token to the group since the group exists and the token is not already in it
            c.execute("INSERT INTO group_members (group_id, auth_token) VALUES (?, ?)", (group_id, auth_token))
            conn.commit()
            return f"Token added to group '{group_name}' successfully."


    def remove_token_from_group(self, auth_token: str, group_name: str) -> str:
        """Remove an auth token from a group if it exists."""
        with self.connect() as conn:
            c = conn.cursor()

            # First, find the group_id corresponding to the group_name
            c.execute("SELECT group_id FROM groups WHERE group_name = ?", (group_name,))
            group_row = c.fetchone()

            # If the group doesn't exist, return a message saying so
            if group_row is None:
                return f"Group '{group_name}' does not exist."

            group_id = group_row[0]

            # Check if the token is in the group
            c.execute("SELECT 1 FROM group_members WHERE group_id = ? AND auth_token = ?", (group_id, auth_token))
            if c.fetchone() is None:
                # If the token is not in the group, return a message saying so
                return f"Token does not exist in group '{group_name}'."

            # If the token is in the group, proceed to delete it
            c.execute("DELETE FROM group_members WHERE group_id = ? AND auth_token = ?", (group_id, auth_token))
            conn.commit()

            # Return a success message
            return f"Token successfully removed from group '{group_name}'."

            
    def get_groups(self) -> List[str]:
        """Get all group names."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT group_name FROM groups")
            return [row[0] for row in c.fetchall()]
        
    def set_swipe_routine_settings(self, start_hour: int, end_hour: int, likes_per_day: int, left_swipe_percentage: float):
        """Set global swipe routine settings, including left swipe percentage."""
        with self.connect() as conn:
            c = conn.cursor()
            # Update the single row with new settings
            c.execute('''
                UPDATE swipe_settings
                SET start_hour = ?, end_hour = ?, likes_per_day = ?, left_swipe_percentage = ?
                WHERE id = 1
            ''', (start_hour, end_hour, likes_per_day, left_swipe_percentage))
            conn.commit()


    def get_swipe_routine_settings(self) -> Dict[str, int]:
        """Retrieve global swipe routine settings, including left swipe percentage."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT start_hour, end_hour, likes_per_day, left_swipe_percentage FROM swipe_settings WHERE id = 1')
            settings = c.fetchone()
            if settings:
                return {
                    'start_hour': settings[0],
                    'end_hour': settings[1],
                    'likes_per_day': settings[2],
                    'left_swipe_percentage': settings[3]  # Assuming settings[3] is the left_swipe_percentage
                }
            return {}

    def fetch_auth_tokens_by_group(self, group_name: str) -> List[str]:
        """Fetch all auth tokens associated with a specific group."""
        with self.connect() as conn:
            c = conn.cursor()

            # First, find the group_id corresponding to the group_name
            c.execute("SELECT group_id FROM groups WHERE group_name = ?", (group_name,))
            group_row = c.fetchone()

            # If the group doesn't exist, return an empty list
            if group_row is None:
                return []

            group_id = group_row[0]

            # Fetch all auth tokens associated with the group_id
            c.execute("SELECT auth_token FROM group_members WHERE group_id = ?", (group_id,))
            tokens = [row[0] for row in c.fetchall()]

            return tokens
