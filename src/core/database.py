from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


from src.core.settings import settings


class DatabaseManager:
    def __init__(self):
        self.engine = create_async_engine(
            settings.database_url,
            echo=False, 
            pool_size=20,
            max_overflow=10
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def get_session(self) -> AsyncSession:
        return self.session_factory()

    async def close(self):
        await self.engine.dispose()


db_manager = DatabaseManager()