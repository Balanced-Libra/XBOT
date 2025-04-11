import sqlite3
import os
import logging
import ast
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Database")
DB_PATH = os.path.join(DB_DIR, "memories.db")

def init_setup_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS credentials (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            api_type TEXT,  -- Can be NULL now, as we rely on api_keys table
            api_key TEXT,   -- Can be NULL now
            last_updated TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS personalities (
            preset_name TEXT PRIMARY KEY,
            settings TEXT NOT NULL,
            last_updated TEXT NOT NULL
        )''')
        # New table for API keys
        c.execute('''CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            custom_name TEXT NOT NULL,
            api_type TEXT NOT NULL,
            api_key TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            UNIQUE(username, custom_name),
            FOREIGN KEY(username) REFERENCES credentials(username)
        )''')
        conn.commit()

def save_api_key(username, custom_name, api_type, api_key):
    """Save a new API key with a custom name for the user."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO api_keys (username, custom_name, api_type, api_key, last_updated)
                     VALUES (?, ?, ?, ?, ?)''',
                  (username, custom_name, api_type, api_key, datetime.now().isoformat()))
        conn.commit()
    logging.info(f"Saved API key '{custom_name}' ({api_type}) for user '{username}'")

def load_api_keys(username):
    """Load all API keys for a given username."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT custom_name, api_type, api_key FROM api_keys WHERE username = ? ORDER BY last_updated DESC", (username,))
        return [{"custom_name": row[0], "api_type": row[1], "api_key": row[2]} for row in c.fetchall()]

def delete_api_key(username, custom_name):
    """Delete an API key by custom name for a user."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM api_keys WHERE username = ? AND custom_name = ?", (username, custom_name))
        conn.commit()
    logging.info(f"Deleted API key '{custom_name}' for user '{username}'")

# Update save_credentials to not require api_type and api_key initially
def save_credentials(username, credentials):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO credentials (username, password, email, api_type, api_key, last_updated)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (username, credentials['password'], credentials['email'], 
                   credentials.get('api_type'), credentials.get('api_key'), datetime.now().isoformat()))
        conn.commit()

def load_credentials(username):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT password, email, api_type, api_key FROM credentials WHERE username = ?", (username,))
        row = c.fetchone()
        if row:
            return {
                'username': username,
                'password': row[0],
                'email': row[1],
                'api_type': row[2],
                'api_key': row[3]
            }
        return None

def load_personality(preset_name):
    init_setup_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT settings FROM personalities WHERE preset_name = ?", (preset_name,))
    row = c.fetchone()
    conn.close()
    if row:
        settings = ast.literal_eval(row[0])
        if 'engagement_style' in settings:
            del settings['engagement_style']  # Remove engagement_style after loading
        settings.setdefault('language', 'English')
        settings.setdefault('autodetect_language', False)
        logging.info(f"Loaded personality preset '{preset_name}'")
        return settings
    logging.warning(f"No preset found with name '{preset_name}'")
    return None

def get_all_usernames():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT username FROM credentials ORDER BY last_updated DESC")
        return [row[0] for row in c.fetchall()]

def get_all_personality_presets():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT preset_name FROM personalities ORDER BY last_updated DESC")
        return [row[0] for row in c.fetchall()]

def delete_personality(preset_name):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM personalities WHERE preset_name = ?", (preset_name,))
        conn.commit()

def save_personality(preset_name, settings):
    init_setup_db()
    if 'engagement_style' in settings:
        del settings['engagement_style']
    settings.setdefault('language', 'English')
    settings.setdefault('autodetect_language', False)
    settings_str = str(settings)
    timestamp = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO personalities (preset_name, settings, last_updated) VALUES (?, ?, ?)',
              (preset_name, settings_str, timestamp))
    conn.commit()
    conn.close()
    logging.info(f"Saved personality preset '{preset_name}'")

if __name__ == "__main__":
    init_setup_db()
    test_credentials = {
        "username": "test_user",
        "password": "test_pass",
        "email": "test@example.com",
    }
    test_personality = {
        "personality_description": "Test personality",
        "tone_keywords": ["funny", "light"],
        "custom_phrases": ["LOL", "Nice one!"],
        "engagement_style": "Witty",
        "self_update_topics": ["tech", "memes"]
    }
    save_credentials("test_user", test_credentials)
    save_api_key("test_user", "MyOpenAI", "openai", "test_openai_key")
    save_api_key("test_user", "MyGemini", "gemini", "test_gemini_key")
    print("Saved test data")
    print("Loaded credentials:", load_credentials("test_user"))
    print("Loaded API keys:", load_api_keys("test_user"))
    print("Loaded personality:", load_personality("TestPreset"))
    print("All usernames:", get_all_usernames())
    print("All presets:", get_all_personality_presets())