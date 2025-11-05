"""Redis 客户端管理"""
import redis.asyncio as redis
from typing import Optional
from loguru import logger
from app.core.config import settings


class RedisClient:
    """Redis 客户端单例"""
    
    _instance: Optional[redis.Redis] = None
    _pool: Optional[redis.ConnectionPool] = None
    
    @classmethod
    async def get_client(cls) -> redis.Redis:
        """获取 Redis 客户端实例"""
        if cls._instance is None:
            await cls.initialize()
        return cls._instance
    
    @classmethod
    async def initialize(cls):
        """初始化 Redis 连接池"""
        if cls._pool is None:
            cls._pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=50,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            cls._instance = redis.Redis(connection_pool=cls._pool)
            
            # 测试连接
            try:
                await cls._instance.ping()
                logger.info(f"Redis 连接成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            except Exception as e:
                logger.error(f"Redis 连接失败: {str(e)}")
                raise
    
    @classmethod
    async def close(cls):
        """关闭 Redis 连接"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
        if cls._pool:
            await cls._pool.disconnect()
            cls._pool = None
            logger.info("Redis 连接已关闭")


async def get_redis() -> redis.Redis:
    """依赖注入：获取 Redis 客户端"""
    return await RedisClient.get_client()

