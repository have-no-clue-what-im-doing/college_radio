import sqlite3

conn = sqlite3.connect('college_radio.db', timeout=10)
c = conn.cursor()
c.execute(
            '''
            CREATE TABLE IF NOT EXISTS test (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                epoch INTEGER,
                entry_date TEXT,
                college TEXT,
                artist TEXT,
                title TEXT,
                album TEXT,
                genre TEXT,
                release_date INTEGER,
                popularity INTEGER,
                album_art TEXT
            )
            '''
        )
c.close()
conn.close()