#!/usr/bin/env python3
"""
Quick database check script
"""
import sqlite3
import os

def check_database():
    db_path = os.path.join('instance', 'surveillance.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tracks table
    print("=== TRACKS TABLE ===")
    cursor.execute("SELECT track_id, callsign, status, latitude, longitude, altitude FROM track ORDER BY track_id LIMIT 10")
    tracks = cursor.fetchall()
    
    if tracks:
        print(f"Found {len(tracks)} tracks:")
        for track in tracks:
            print(f"  {track[0]} | {track[1]} | {track[2]} | {track[3]:.6f}, {track[4]:.6f} | {track[5]}ft")
    else:
        print("No tracks found")
    
    # Check total count
    cursor.execute("SELECT COUNT(*) FROM track")
    track_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM track WHERE status = 'Active'")
    active_count = cursor.fetchone()[0]
    
    print(f"\nTotal tracks: {track_count}")
    print(f"Active tracks: {active_count}")
    
    # Check events table
    print("\n=== EVENTS TABLE ===")
    cursor.execute("SELECT COUNT(*) FROM event")
    event_count = cursor.fetchone()[0]
    print(f"Total events: {event_count}")
    
    cursor.execute("SELECT event_type, COUNT(*) FROM event GROUP BY event_type")
    event_types = cursor.fetchall()
    for event_type, count in event_types:
        print(f"  {event_type}: {count}")
    
    conn.close()

if __name__ == "__main__":
    check_database()
