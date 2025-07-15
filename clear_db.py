#!/usr/bin/env python3
"""
Database Clear Utility for Development
======================================

This script provides options to clear different parts of the database during development:
- Clear all surveillance data (tracks and events)
- Clear only events
- Clear only tracks
- Clear all data except users (tracks, events, network config)
- Reset database completely (preserves default user)

Usage:
    python clear_db.py [option]

Options:
    --all-data          Clear all data except users (tracks, events, network config)
    --surveillance      Clear only surveillance data (tracks and events) [DEFAULT]
    --tracks            Clear only tracks
    --events            Clear only events
    --reset             Drop all tables and recreate them (preserves default user)
    --help              Show this help message
"""

import sys
import os
from sqlalchemy import text

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_init import app, db
from models import User, Track, Event, NetworkConfig

def clear_surveillance_data():
    """Clear tracks and events (surveillance data only)"""
    with app.app_context():
        try:
            # Clear in order (events first due to potential foreign key relationships)
            events_deleted = db.session.query(Event).delete()
            tracks_deleted = db.session.query(Track).delete()
            
            # Also clear the track integrator's tracks table
            calculated_tracks_deleted = 0
            try:
                result = db.session.execute(text("DELETE FROM tracks"))
                calculated_tracks_deleted = result.rowcount if hasattr(result, 'rowcount') else 0
            except Exception as e:
                print(f"Note: Could not clear calculated tracks table: {e}")
            
            db.session.commit()
            print(f"✓ Cleared {events_deleted} events, {tracks_deleted} tracks, and {calculated_tracks_deleted} calculated tracks")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error clearing surveillance data: {e}")
            return False

def clear_tracks_only():
    """Clear only tracks"""
    with app.app_context():
        try:
            tracks_deleted = db.session.query(Track).delete()
            
            # Also clear the track integrator's tracks table
            calculated_tracks_deleted = 0
            try:
                result = db.session.execute(text("DELETE FROM tracks"))
                calculated_tracks_deleted = result.rowcount if hasattr(result, 'rowcount') else 0
            except Exception as e:
                print(f"Note: Could not clear calculated tracks table: {e}")
            
            db.session.commit()
            print(f"✓ Cleared {tracks_deleted} tracks and {calculated_tracks_deleted} calculated tracks")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error clearing tracks: {e}")
            return False

def clear_events_only():
    """Clear only events"""
    with app.app_context():
        try:
            events_deleted = db.session.query(Event).delete()
            db.session.commit()
            print(f"✓ Cleared {events_deleted} events")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error clearing events: {e}")
            return False

def clear_all_data():
    """Clear all data except users (tracks, events, network config)"""
    with app.app_context():
        try:
            # Clear in order (events first due to potential foreign key relationships)
            events_deleted = db.session.query(Event).delete()
            tracks_deleted = db.session.query(Track).delete()
            config_deleted = db.session.query(NetworkConfig).delete()
            
            # Also clear the track integrator's tracks table
            calculated_tracks_deleted = 0
            try:
                result = db.session.execute(text("DELETE FROM tracks"))
                calculated_tracks_deleted = result.rowcount if hasattr(result, 'rowcount') else 0
            except Exception as e:
                print(f"Note: Could not clear calculated tracks table: {e}")
            
            db.session.commit()
            print(f"✓ Cleared {events_deleted} events, {tracks_deleted} tracks, {calculated_tracks_deleted} calculated tracks, {config_deleted} network configs")
            print("✓ Users preserved")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error clearing data: {e}")
            return False

def reset_database():
    """Drop all tables and recreate them (preserves default user)"""
    with app.app_context():
        try:
            # Get existing users before dropping tables
            existing_users = []
            try:
                users = db.session.query(User).all()
                for user in users:
                    existing_users.append({
                        'username': user.username,
                        'password_hash': user.password_hash,
                        'created_at': user.created_at,
                        'last_login': user.last_login
                    })
            except:
                pass  # Tables might not exist yet
            
            # Drop all tables
            db.drop_all()
            print("✓ Dropped all tables")
            
            # Recreate all tables
            db.create_all()
            print("✓ Recreated all tables")
            
            # Restore existing users or create default user
            if existing_users:
                for user_data in existing_users:
                    user = User()
                    user.username = user_data['username']
                    user.password_hash = user_data['password_hash']
                    user.created_at = user_data['created_at']
                    user.last_login = user_data['last_login']
                    db.session.add(user)
                db.session.commit()
                print(f"✓ Restored {len(existing_users)} existing users")
            else:
                # Create default user if no users existed
                from app_init import create_default_user
                create_default_user()
                print("✓ Created default user (username: user, password: pass)")
            
            return True
        except Exception as e:
            print(f"✗ Error resetting database: {e}")
            return False

def show_current_stats():
    """Show current database statistics"""
    with app.app_context():
        try:
            tracks_count = db.session.query(Track).count()
            events_count = db.session.query(Event).count()
            users_count = db.session.query(User).count()
            config_count = db.session.query(NetworkConfig).count()
            
            # Count calculated tracks
            calculated_tracks_count = 0
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM tracks"))
                calculated_tracks_count = result.scalar()
            except Exception:
                pass  # Table might not exist yet
            
            print(f"\nCurrent Database Statistics:")
            print(f"  Tracks: {tracks_count}")
            print(f"  Calculated Tracks: {calculated_tracks_count}")
            print(f"  Events: {events_count}")
            print(f"  Users: {users_count}")
            print(f"  Network Configs: {config_count}")
            print()
        except Exception as e:
            print(f"✗ Error getting database statistics: {e}")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        option = sys.argv[1].lower()
    else:
        option = "--surveillance"  # Default option
    
    print("Database Clear Utility for Development")
    print("="*40)
    
    show_current_stats()
    
    if option in ["--help", "-h"]:
        print(__doc__)
        return
    
    # Confirm action
    if option == "--reset":
        confirm = input("⚠️  This will reset the database but preserve existing users. Are you sure? (yes/no): ")
    elif option == "--all-data":
        confirm = input("⚠️  This will clear all data except users. Are you sure? (yes/no): ")
    else:
        confirm = input(f"Clear database with option '{option}'? (yes/no): ")
    
    if confirm.lower() not in ['yes', 'y']:
        print("Operation cancelled.")
        return
    
    # Execute based on option
    success = False
    if option == "--surveillance":
        success = clear_surveillance_data()
    elif option == "--tracks":
        success = clear_tracks_only()
    elif option == "--events":
        success = clear_events_only()
    elif option == "--all-data":
        success = clear_all_data()
    elif option == "--reset":
        success = reset_database()
    else:
        print(f"Unknown option: {option}")
        print("Use --help for available options")
        return
    
    if success:
        print("\n" + "="*40)
        show_current_stats()
        print("Operation completed successfully!")
    else:
        print("\nOperation failed!")

if __name__ == "__main__":
    main()
