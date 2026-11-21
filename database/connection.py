
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Project root: D:\CAP2_SDT
BASE_DIR = Path(__file__).resolve().parent.parent

# Database directory
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# SQLite database file
DATABASE_PATH = DATABASE_DIR / "tourism.db"

DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

# SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Declarative base
Base = declarative_base()


def get_db():
    """
    Dependency cung cấp database session cho FastAPI.
    Tự động đóng session sau khi xử lý request.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Khởi tạo toàn bộ bảng database.
    Import models trước khi gọi hàm này để SQLAlchemy
    nhận diện đầy đủ các model.
    """
    from database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
    print(f"Database location: {DATABASE_PATH}")
