from sqlmodel import create_engine, Session, SQLModel
from app.config import settings
from sqlalchemy import event

# Adjust connection arguments if using SQLite
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args
)

# Enable SQLite WAL (Write-Ahead Logging) mode on connection setup to prevent query locking
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

def init_db():
    """Create all tables in the database if they do not exist."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """FastAPI Dependency for database session injection."""
    with Session(engine) as session:
        yield session
