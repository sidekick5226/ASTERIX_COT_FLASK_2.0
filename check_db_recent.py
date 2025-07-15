import sqlite3
import os

# Connect to database
db_path = 'instance/surveillance.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check events from last 5 minutes
    cursor.execute("SELECT * FROM event WHERE timestamp > datetime('now', '-5 minutes') ORDER BY timestamp DESC LIMIT 20;")
    events = cursor.fetchall()
    print(f'Found {len(events)} events in last 5 minutes:')
    for event in events:
        print(f'  - {event}')
    
    # Check all tracks
    cursor.execute("SELECT * FROM track ORDER BY last_updated DESC;")
    tracks = cursor.fetchall()
    print(f'\nFound {len(tracks)} total tracks:')
    for track in tracks:
        print(f'  - {track}')
    
    conn.close()
else:
    print('Database file not found')
