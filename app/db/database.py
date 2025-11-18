"""数据库连接和会话管理

提供数据库引擎、会话工厂和上下文管理器，用于统一管理数据库连接。
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from loguru import logger

from app.core.config import settings
from app.core.exceptions import DatabaseException


# 创建异步引擎
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,  # 生产环境建议关闭SQL日志
    future=True,
    pool_pre_ping=True,
    pool_size=20,  # 连接池大小
    max_overflow=10,  # 最大溢出连接数
    pool_recycle=3600,  # 连接回收时间（秒）
)

# 创建会话工厂
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（FastAPI 依赖注入）
    
    Yields:
        AsyncSession: 数据库会话对象
        
    Examples:
        >>> @app.get("/items")
        >>> async def get_items(db: AsyncSession = Depends(get_db)):
        >>>     result = await db.execute(select(Item))
        >>>     return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_service_session() -> AsyncGenerator[AsyncSession, None]:
    """获取服务层数据库会话（带自动提交/回滚）
    
    用于服务层代码，自动处理事务提交和回滚。
    
    Yields:
        AsyncSession: 数据库会话对象
        
    Raises:
        DatabaseException: 数据库操作失败时抛出
        
    Examples:
        >>> async with get_service_session() as db:
        >>>     user = User(username="test")
        >>>     db.add(user)
        >>>     # 自动提交
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Service session error: {str(e)}")
            raise DatabaseException("transaction", str(e))
        finally:
            await session.close()


class DatabaseSessionManager:
    """数据库会话管理器
    
    提供统一的会话管理接口，用于服务类中管理数据库会话。
    
    Attributes:
        session_factory: 会话工厂函数
        
    Examples:
        >>> class MyService:
        >>>     def __init__(self):
        >>>         self.db_manager = DatabaseSessionManager()
        >>>
        >>>     async def do_something(self):
        >>>         async with self.db_manager.session() as db:
        >>>             # 使用数据库会话
        >>>             pass
    """
    
    def __init__(self, session_factory=None):
        """初始化会话管理器
        
        Args:
            session_factory: 可选的会话工厂，默认使用 AsyncSessionLocal
        """
        self.session_factory = session_factory or AsyncSessionLocal
    
    @asynccontextmanager
    async def session(
        self,
        auto_commit: bool = True
    ) -> AsyncGenerator[AsyncSession, None]:
        """创建数据库会话上下文
        
        Args:
            auto_commit: 是否自动提交，默认 True
            
        Yields:
            AsyncSession: 数据库会话对象
            
        Examples:
            >>> async with self.db_manager.session() as db:
            >>>     result = await db.execute(select(User))
        """
        async with self.session_factory() as session:
            try:
                yield session
                if auto_commit:
                    await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {str(e)}")
                raise
            finally:
                await session.close()
    
    async def execute_in_session(self, func, *args, **kwargs):
        """在会话中执行函数
        
        Args:
            func: 要执行的异步函数，第一个参数必须是 db session
            *args: 函数的其他参数
            **kwargs: 函数的关键字参数
            
        Returns:
            函数的返回值
            
        Examples:
            >>> async def get_user(db, user_id):
            >>>     return await db.get(User, user_id)
            >>>
            >>> user = await db_manager.execute_in_session(get_user, 1)
        """
        async with self.session() as db:
            return await func(db, *args, **kwargs)

