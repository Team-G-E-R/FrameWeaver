from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
from collections.abc import AsyncGenerator


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gagen:gagen@postgres:5432/gagen"

    class Config:
        env_file = ".env"
        extra = "ignore"
        
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

settings = Settings()

engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)