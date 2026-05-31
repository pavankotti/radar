from sqlmodel import Session
from app.database import get_session

# Simple alias for injecting the database session
def get_db():
    yield from get_session()
