from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from querio_backend.bridge_config import DATABASE_URL

# Without connect_timeout, psycopg on Windows waits forever when Postgres is down (the refused
# non-blocking connect is never noticed), so every /chat hung after the chatbot had already
# answered. Query logging is best-effort and must not block the response.
DB_CONNECT_TIMEOUT_SECONDS = 2

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": DB_CONNECT_TIMEOUT_SECONDS})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
