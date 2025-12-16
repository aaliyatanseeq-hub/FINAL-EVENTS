# init_tables.py
import sys
import os

print("🚀 Initializing Event Intelligence Platform Database...")

# Add parent directory (Backend/) to Python path so we can import database module
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # Backend/ directory
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    # Import database modules
    from database.database import Base, engine, init_database
    # Import models to register them with Base.metadata
    # Use absolute import when run directly, relative import when imported as module
    try:
        from . import models  # noqa: F401 - Relative import (when imported as module)
    except ImportError:
        from database import models  # noqa: F401 - Absolute import (when run directly)
    
    print("🔗 Creating database tables...")
    
    # Initialize database
    init_database()
    
    print("✅ Database tables created successfully!")
    
    # List created tables
    print("\n📊 Tables created:")
    tables = list(Base.metadata.tables.keys())
    for table in tables:
        print(f"  • {table}")
    
    print(f"\n📈 Total: {len(tables)} tables")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\n💡 Make sure you have:")
    print("   1. Created the 'database' folder")
    print("   2. Created all database files")
    print("   3. Installed requirements: pip install sqlalchemy psycopg2-binary")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n🔧 Common issues:")
    print("   1. PostgreSQL not running")
    print("   2. Wrong database URL in .env file")
    print("   3. Missing database or user permissions")
    print("\n💡 Run these checks:")
    print("   Get-Service -Name 'postgresql-x64-18'")
    print("   psql -U postgres -c '\\l'")