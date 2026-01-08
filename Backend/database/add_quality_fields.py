"""
Production-Grade Migration Script
Adds quality filtering fields to events table with comprehensive error handling
"""
import sys
import os
from pathlib import Path
from typing import Optional

# Production-grade path resolution
script_dir = Path(__file__).resolve().parent
parent_dir = script_dir.parent

# Add parent directory (Backend) to Python path if not already present
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import database modules with proper error handling
try:
    from database.database import engine, Base
    from database import models  # type: ignore[import-untyped]
    from sqlalchemy import text
except ImportError as e:
    # If import fails, try alternative path resolution
    print(f"⚠️ Initial import failed: {e}")
    print(f"   Attempting alternative path resolution...")
    
    # Try adding current script's parent to path
    if str(script_dir.parent) not in sys.path:
        sys.path.insert(0, str(script_dir.parent))
    
    try:
        from database.database import engine, Base
        from database import models  # type: ignore[import-untyped]
        from sqlalchemy import text
    except ImportError:
        print(f"❌ Failed to import database modules")
        print(f"   Script directory: {script_dir}")
        print(f"   Parent directory: {parent_dir}")
        print(f"   Python path: {sys.path[:3]}")
        raise

def add_quality_fields():
    """
    Production-grade migration: Add quality filtering fields to events table
    Includes comprehensive error handling, transaction management, and validation
    """
    conn = None
    try:
        # Establish database connection with proper error handling
        conn = engine.connect()
        
        # Begin transaction
        trans = conn.begin()
        
        try:
            # Check if columns already exist (idempotent operation)
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'events' 
                AND column_name = 'is_real_event'
                AND table_schema = 'public'
            """)
            
            result = conn.execute(check_query)
            existing_column = result.fetchone()
            
            if existing_column:
                print("✅ Quality fields already exist in events table")
                print("   Migration already completed - no changes needed")
                trans.rollback()  # No changes needed
                return
            
            # Add new columns with proper error handling
            print("📊 Adding quality filtering fields to events table...")
            print("   This may take a few seconds...")
            
            # Execute ALTER TABLE with comprehensive error handling
            alter_table_query = text("""
                ALTER TABLE events 
                ADD COLUMN IF NOT EXISTS is_real_event BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS quality_score FLOAT DEFAULT 1.0,
                ADD COLUMN IF NOT EXISTS clean_category VARCHAR(100),
                ADD COLUMN IF NOT EXISTS rejection_reasons JSON,
                ADD COLUMN IF NOT EXISTS quality_confidence FLOAT DEFAULT 1.0
            """)
            
            conn.execute(alter_table_query)
            print("   ✅ Columns added successfully")
            
            # Create indexes for performance (idempotent with IF NOT EXISTS)
            print("   📊 Creating indexes...")
            
            index_queries = [
                "CREATE INDEX IF NOT EXISTS idx_events_is_real_event ON events(is_real_event)",
                "CREATE INDEX IF NOT EXISTS idx_events_quality_score ON events(quality_score)"
            ]
            
            for idx_query in index_queries:
                conn.execute(text(idx_query))
            
            print("   ✅ Indexes created successfully")
            
            # Commit transaction
            trans.commit()
            
            # Verify migration success
            verify_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'events' 
                AND column_name IN ('is_real_event', 'quality_score', 'clean_category', 'rejection_reasons', 'quality_confidence')
                AND table_schema = 'public'
            """)
            
            verify_result = conn.execute(verify_query)
            verified_columns = [row[0] for row in verify_result.fetchall()]
            
            if len(verified_columns) == 5:
                print()
                print("✅ Quality fields added successfully!")
                print("   Verified columns:")
                print(f"   - is_real_event (boolean, indexed) {'✅' if 'is_real_event' in verified_columns else '❌'}")
                print(f"   - quality_score (float, indexed) {'✅' if 'quality_score' in verified_columns else '❌'}")
                print(f"   - clean_category (varchar) {'✅' if 'clean_category' in verified_columns else '❌'}")
                print(f"   - rejection_reasons (json) {'✅' if 'rejection_reasons' in verified_columns else '❌'}")
                print(f"   - quality_confidence (float) {'✅' if 'quality_confidence' in verified_columns else '❌'}")
            else:
                print(f"⚠️ Warning: Expected 5 columns, found {len(verified_columns)}")
                print(f"   Verified: {verified_columns}")
                
        except Exception as e:
            # Rollback transaction on error
            trans.rollback()
            raise
            
    except Exception as e:
        error_msg = str(e)
        
        # Provide specific error messages for common issues
        if "does not exist" in error_msg.lower() or "relation" in error_msg.lower():
            print(f"❌ Database table 'events' does not exist")
            print("   Please run database initialization first")
            print("   The events table should be created automatically on first run")
        elif "permission denied" in error_msg.lower() or "access denied" in error_msg.lower():
            print(f"❌ Permission denied: Database user lacks ALTER TABLE privileges")
            print("   Please grant ALTER TABLE permission to your database user")
            print("   SQL: GRANT ALTER ON TABLE events TO your_user;")
        elif "connection" in error_msg.lower() or "could not connect" in error_msg.lower():
            print(f"❌ Database connection failed")
            print("   Please check:")
            print("   1. PostgreSQL is running")
            print("   2. Database connection settings in .env file")
            print("   3. Database server is accessible")
        else:
            print(f"❌ Error adding quality fields: {error_msg}")
        
        import traceback
        print()
        print("Full error details:")
        traceback.print_exc()
        raise
        
    finally:
        # Ensure connection is properly closed
        if conn:
            try:
                conn.close()
            except:
                pass

if __name__ == "__main__":
    add_quality_fields()

