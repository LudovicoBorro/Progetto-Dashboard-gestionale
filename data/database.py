from contextlib import contextmanager
import os
from sqlmodel import create_engine, SQLModel, Session

# Database path
DB_FILE = "data/db.sqlite"
DATABASE_URL = f"sqlite:///{DB_FILE}"

# Create engine
# check_same_thread=False is needed for SQLite when used with multiple threads
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def init_db():
    """Initialize database and create all tables."""
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    SQLModel.metadata.create_all(engine)

@contextmanager
def get_session():
    """Provide a session for database operations."""
    with Session(engine) as session:
        yield session
