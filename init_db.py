import sqlite3
from datetime import datetime

def init_db():
    """Initialize the database with required tables and schema."""
    conn = None
    try:
        conn = sqlite3.connect('mental_health.db')
        c = conn.cursor()
        
        # Create users table (if not already existing)
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create assessments table with FIXED schema
        c.execute('''
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                assessment_type TEXT CHECK(assessment_type IN ('phq9', 'gad7')) NOT NULL,
                score INTEGER NOT NULL CHECK(score >= 0),
                recommendation TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Create mood_entries table with FIXED schema
        c.execute('''
            CREATE TABLE IF NOT EXISTS mood_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mood INTEGER NOT NULL CHECK(mood BETWEEN 1 AND 5),
                notes TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Add indexes
        c.execute('CREATE INDEX IF NOT EXISTS idx_assessments_user ON assessments (user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_mood_user ON mood_entries (user_id)')
        
        conn.commit()
        print(f"Database initialized successfully at {datetime.now()}!")
        
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    init_db()