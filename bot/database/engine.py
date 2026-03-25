from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from bot.config import settings


def build_engine(url: str, echo: bool = False) -> AsyncEngine:
    return create_async_engine(
        url,
        echo=echo,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


engine = build_engine(settings.database_url)

session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
