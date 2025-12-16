"""
PostgreSQL Database Configuration
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Database configuration - FIXED DEFAULT URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://event_user:event_password123@localhost:5432/event_intelligence")

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Initialize database tables"""
    print("📊 Initializing PostgreSQL database...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully")
