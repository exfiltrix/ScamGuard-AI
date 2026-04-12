from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.models.database import Base
from backend.config import get_settings

settings = get_settings()

# Convert sqlite:/// to sqlite+aiosqlite:///
database_url = settings.database_url.replace('sqlite:///', 'sqlite+aiosqlite:///')

engine = create_async_engine(
    database_url,
    echo=settings.debug,
    future=True
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
