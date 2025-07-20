from sqlmodel import SQLModel, create_engine, Session
from fastapi import Depends
import os
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
import time

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@postgres:5432/kinopoisk")
engine = create_engine(DATABASE_URL)

def wait_for_db():
    retries = 5
    while retries:
        try:
            with Session(engine) as session:
                session.execute(text("SELECT 1"))
            SQLModel.metadata.create_all(engine)
            return
        except OperationalError:
            retries -= 1
            time.sleep(5)
    raise Exception("Failed to connect to DB")

def get_session():
    with Session(engine) as session:
        yield session