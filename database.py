import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./todo.db")

# SQLAlchemy 1.4+ requires postgresql:// instead of postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite requires check_same_thread: False, but other databases like PostgreSQL do not support it
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

def run_migrations():
    """
    Ensures that any existing SQLite database gets the new 'category' column added
    dynamically without needing external migration scripts or dropping existing tables.
    """
    try:
        with engine.connect() as conn:
            # Check existing columns in the todos table
            res = conn.execute(text("PRAGMA table_info(todos)"))
            columns = [row[1] for row in res.fetchall()]
            if columns and "category" not in columns:
                conn.execute(text("ALTER TABLE todos ADD COLUMN category TEXT"))
                conn.commit()
                print("Database migration: Successfully added 'category' column to 'todos' table.")
    except Exception as e:
        print(f"Database migration warning: Could not verify/alter table columns: {e}")

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()