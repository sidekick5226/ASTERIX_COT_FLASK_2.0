import sqlite3
import os

# Connect to database
db_path = 'instance/surveillance.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check for events table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='event';")
    if cursor.fetchone():
        # Get recent events
        cursor.execute("SELECT * FROM event ORDER BY timestamp DESC LIMIT 10;")
        events = cursor.fetchall()
        print(f'Found {len(events)} events:')
        for event in events:
            print(f'  - {event}')
    else:
        print('No events table found')
    
    # Check for tracks table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='track';")
    if cursor.fetchone():
        cursor.execute("SELECT * FROM track ORDER BY last_updated DESC LIMIT 10;")
        tracks = cursor.fetchall()
        print(f'Found {len(tracks)} tracks:')
        for track in tracks:
            print(f'  - {track}')
    else:
        print('No tracks table found')
    
    conn.close()
else:
    print('Database file not found')
