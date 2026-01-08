"""
Migration script to add user_id column to attendees table
Run this script to add the user_id column for storing Twitter user IDs
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import database modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import engine
from sqlalchemy import text

def add_user_id_column():
    """Add user_id column to attendees table"""
    try:
        with engine.connect() as conn:
            # Check if column already exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'attendees' 
                AND column_name = 'user_id'
            """)
            result = conn.execute(check_query)
            if result.fetchone():
                print("✅ Column 'user_id' already exists in attendees table")
                return True
            
            # Add the column
            alter_query = text("""
                ALTER TABLE attendees 
                ADD COLUMN user_id VARCHAR(100) NULL
            """)
            conn.execute(alter_query)
            
            # Create index
            index_query = text("""
                CREATE INDEX IF NOT EXISTS idx_attendees_user_id 
                ON attendees(user_id)
            """)
            conn.execute(index_query)
            
            conn.commit()
            print("✅ Successfully added 'user_id' column to attendees table")
            print("✅ Created index on 'user_id' column")
            return True
            
    except Exception as e:
        print(f"❌ Error adding user_id column: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("🔧 Adding user_id column to attendees table")
    print("=" * 70)
    success = add_user_id_column()
    if success:
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed. Please check the error above.")
        sys.exit(1)

