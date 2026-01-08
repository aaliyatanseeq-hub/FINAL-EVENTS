"""
Production-Grade Migration Runner
Adds quality filtering fields to events table with comprehensive error handling
Works from any directory - automatically resolves Backend directory path
"""
import sys
import os
from pathlib import Path
from typing import Optional

def find_backend_directory() -> Path:
    """
    Production-grade directory resolution
    Handles all edge cases: case sensitivity, symlinks, different execution contexts
    """
    script_path = Path(__file__).resolve()
    current_dir = script_path.parent
    
    # Strategy 1: Check if we're already in Backend directory (case-insensitive)
    if current_dir.name.lower() == 'backend':
        # Verify it's actually Backend by checking for database subdirectory
        if (current_dir / 'database').exists() and (current_dir / 'database' / 'add_quality_fields.py').exists():
            return current_dir
    
    # Strategy 2: Look for Backend directory in parent (case-insensitive search)
    parent_dir = current_dir.parent
    possible_names = ['Backend', 'backend', 'BACKEND']
    
    for name in possible_names:
        possible_path = parent_dir / name
        if possible_path.exists() and possible_path.is_dir():
            # Verify it's the correct Backend directory
            if (possible_path / 'database').exists() and (possible_path / 'database' / 'add_quality_fields.py').exists():
                return possible_path
    
    # Strategy 3: Search recursively up the directory tree (max 3 levels)
    search_dir = current_dir
    for _ in range(3):
        search_dir = search_dir.parent
        for name in possible_names:
            possible_path = search_dir / name
            if possible_path.exists() and possible_path.is_dir():
                if (possible_path / 'database').exists() and (possible_path / 'database' / 'add_quality_fields.py').exists():
                    return possible_path
    
    # Strategy 4: Check if current directory contains database folder (we might be in Backend)
    if (current_dir / 'database').exists() and (current_dir / 'database' / 'add_quality_fields.py').exists():
        return current_dir
    
    # If all strategies fail, return current directory as fallback
    return current_dir

def setup_environment(backend_dir: Path) -> None:
    """Setup Python path and working directory with proper error handling"""
    # Add Backend to Python path (only if not already present)
    backend_str = str(backend_dir)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)
    
    # Change to Backend directory for relative imports
    try:
        if backend_dir.exists() and backend_dir.is_dir():
            os.chdir(backend_dir)
    except (OSError, PermissionError) as e:
        # Log warning but continue - path setup might be enough
        print(f"⚠️ Warning: Could not change to Backend directory: {e}")
        print(f"   Continuing with path-based imports...")

def main():
    """Main migration execution with comprehensive error handling"""
    add_quality_fields = None
    
    try:
        # Find Backend directory
        backend_dir = find_backend_directory()
        
        if not backend_dir.exists():
            raise FileNotFoundError(f"Backend directory not found: {backend_dir}")
        
        print(f"📁 Resolved Backend directory: {backend_dir}")
        
        # Setup environment
        setup_environment(backend_dir)
        
        # Import migration function
        try:
            from database.add_quality_fields import add_quality_fields  # type: ignore
        except ImportError as e:
            print(f"❌ Failed to import migration module")
            print(f"   Error: {e}")
            print(f"   Backend directory: {backend_dir}")
            print(f"   Current working directory: {os.getcwd()}")
            print(f"   Python path (first 3 entries): {sys.path[:3]}")
            print(f"   Database module path: {backend_dir / 'database'}")
            raise
        
        # Execute migration
        print("=" * 60)
        print("🚀 Running Database Migration")
        print("=" * 60)
        print()
        
        if add_quality_fields:
            add_quality_fields()
        else:
            raise ImportError("Failed to import add_quality_fields function")
        
        print()
        print("=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print()
        print("You can now store events without database errors.")
        return 0
        
    except FileNotFoundError as e:
        print()
        print("=" * 60)
        print(f"❌ Migration failed: Directory not found")
        print("=" * 60)
        print(f"   Error: {e}")
        print()
        print("Please ensure:")
        print("1. You're running from the project root (FIX6) or Backend directory")
        print("2. The Backend directory exists and contains 'database' subdirectory")
        return 1
        
    except ImportError as e:
        print()
        print("=" * 60)
        print(f"❌ Migration failed: Import error")
        print("=" * 60)
        print(f"   Error: {e}")
        print()
        print("Please check:")
        print("1. All required Python packages are installed (pip install -r requirements.txt)")
        print("2. Database module exists in Backend/database/")
        return 1
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Migration failed: Unexpected error")
        print("=" * 60)
        print(f"   Error: {e}")
        print()
        print("Please check:")
        print("1. PostgreSQL is running")
        print("2. Database connection is configured in .env")
        print("3. You have permissions to alter the events table")
        print("4. Database user has ALTER TABLE privileges")
        import traceback
        print()
        print("Full traceback:")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
