import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'vd_traffic.db')

def setup_database():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create traffic_records table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS traffic_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            vd_id TEXT NOT NULL,
            link_id TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            volume INTEGER NOT NULL,
            speed REAL NOT NULL
        )
    ''')
    
    # Create indices for faster filtering and aggregation
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON traffic_records(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_link_vehicle ON traffic_records(link_id, vehicle_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vd ON traffic_records(vd_id)')
    
    conn.commit()
    conn.close()
    print(f"Database initialized successfully at: {db_path}")

if __name__ == '__main__':
    setup_database()
