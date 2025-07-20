from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy import text
import time
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@postgres:5432/kinopoisk")
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10},
    echo=True
)


def wait_for_db():
    max_retries = 10
    retry_delay = 3

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempt {attempt}/{max_retries}: Connecting to DB...")
            with Session(engine) as session:
                result = session.execute(text("SELECT version()")).first()
                logger.info(f"Connected to PostgreSQL: {result[0]}")
                if not engine.dialect.has_table(engine, "film"):
                    SQLModel.metadata.create_all(engine)
                    logger.info("Database tables created")
                return
        except Exception as e:
            logger.error(f"Connection failed: {type(e).__name__}: {str(e)}")
            if attempt == max_retries:
                raise RuntimeError(f"Failed to connect to DB after {max_retries} attempts")
            time.sleep(retry_delay)


def get_session():
    with Session(engine) as session:
        yield session