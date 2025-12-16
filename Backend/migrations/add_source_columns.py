"""Migration: Add source columns to events and attendees tables"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from database.database import engine

def add_source_columns():
    """Add source columns to events and attendees tables"""
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        try:
            # Check if source column exists in events table
            events_columns = [col['name'] for col in inspector.get_columns('events')]
            if 'source' not in events_columns:
                print("Adding source column to events table...")
                conn.execute(text("ALTER TABLE events ADD COLUMN source VARCHAR(50) DEFAULT 'unknown'"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)"))
                print("✅ Added source column to events table")
            else:
                print("✅ Source column already exists in events table")
            
            # Check if source column exists in attendees table
            attendees_columns = [col['name'] for col in inspector.get_columns('attendees')]
            if 'source' not in attendees_columns:
                print("Adding source column to attendees table...")
                conn.execute(text("ALTER TABLE attendees ADD COLUMN source VARCHAR(50) DEFAULT 'unknown'"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_attendees_source ON attendees(source)"))
                print("✅ Added source column to attendees table")
            else:
                print("✅ Source column already exists in attendees table")
            
            conn.commit()
            print("\n✅ Migration completed successfully!")
        except Exception as e:
            conn.rollback()
            print(f"❌ Error adding source columns: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    add_source_columns()

