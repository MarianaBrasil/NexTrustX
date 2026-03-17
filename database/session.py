import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Lê a URL da variável de ambiente injetada pelo Docker
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://dark_admin:nexus_secret_v2_777@nexus-db-v2:5432/darkpay_nexus_v2")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
