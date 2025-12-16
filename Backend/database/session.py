"""
Database session utilities
"""
from contextlib import contextmanager
from sqlalchemy.orm import Session
from .database import SessionLocal

@contextmanager
def get_db_session():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()