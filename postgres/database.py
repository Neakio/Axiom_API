# ------------------------------ PACKAGES ------------------------------
# Independant packages
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# General packages
import logging
from dotenv import load_dotenv
from os import path, getenv

# Internal packages
from functions.utils import create_env, check_env
from functions.setup_postgresql import setup_db, check_db_status


# ------------------------------ INIT ------------------------------
# Initialize environment and database connection
check_db_status()
if not path.isfile(".env") or not check_env():
    create_env()
    setup_db()
load_dotenv()

DATABASE_URL = getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True, future=True)

Base = declarative_base()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_db() -> AsyncSession:
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session