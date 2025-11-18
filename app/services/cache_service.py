"""Redis缓存服务 - 提供统一的缓存管理"""
import json
import time
from typing import Optional, Any, Callable, List
from functools import wraps
import redis.asyncio as redis
from loguru import logger
from app.db.redis_client import get_redis


class CacheService:
    """缓存服务类"""
    
    # 缓存键前缀
    PREFIX_ALERT_RULE = "alert_rule"
    PREFIX_DATASOURCE = "datasource"
    PREFIX_NOTIFICATION = "notification"
    PREFIX_PROJECT = "project"
    PREFIX_USER = "user"
    PREFIX_SILENCE = "silence"
    
    # 默认过期时间（秒）
    DEFAULT_TTL = 300  # 5分钟
    LIST_TTL = 60      # 列表缓存1分钟
    DETAIL_TTL = 300   # 详情缓存5分钟
    
    @staticmethod
    def _make_key(prefix: str, *args) -> str:
        """生成缓存键"""
        parts = [prefix] + [str(arg) for arg in args if arg is not None]
        return ":".join(parts)
    
    @staticmethod
    def _make_list_key(prefix: str, tenant_id: int, project_id: Optional[int] = None) -> str:
        """生成列表缓存键"""
        if project_id is not None:
            return f"{prefix}:list:tenant:{tenant_id}:project:{project_id}"
        return f"{prefix}:list:tenant:{tenant_id}"
    
    @staticmethod
    async def get(key: str, redis_client: redis.Redis = None) -> Optional[Any]:
        """获取缓存"""
        try:
            if redis_client is None:
                redis_client = await get_redis()
            
            start_time = time.time()
            value = await redis_client.get(key)
            
            if value:
                data = json.loads(value)
                logger.info(f"缓存命中: {key} (耗时: {(time.time() - start_time)*1000:.2f}ms)")
                return data
            else:
                logger.info(f"缓存未命中: {key}")
                return None
        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {str(e)}")
            return None
    
    @staticmethod
    async def set(key: str, value: Any, ttl: int = DEFAULT_TTL, redis_client: redis.Redis = None):
        """设置缓存"""
        try:
            if redis_client is None:
                redis_client = await get_redis()
            
            start_time = time.time()
            serialized_value = json.dumps(value, ensure_ascii=False, default=str)
            await redis_client.setex(key, ttl, serialized_value)
            
            logger.info(f"缓存设置成功: {key} (TTL: {ttl}s, 耗时: {(time.time() - start_time)*1000:.2f}ms)")
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {str(e)}")
    
    @staticmethod
    async def delete(key: str, redis_client: redis.Redis = None):
        """删除缓存"""
        try:
            if redis_client is None:
                redis_client = await get_redis()
            
            await redis_client.delete(key)
        except Exception as e:
            logger.warning(f"删除缓存失败 {key}: {str(e)}")
    
    @staticmethod
    async def delete_pattern(pattern: str, redis_client: redis.Redis = None):
        """删除匹配模式的所有缓存"""
        try:
            if redis_client is None:
                redis_client = await get_redis()
            
            cursor = 0
            while True:
                cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
                if keys:
                    await redis_client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning(f"删除模式缓存失败 {pattern}: {str(e)}")
    
    @classmethod
    async def invalidate_list_cache(cls, prefix: str, tenant_id: int, project_id: Optional[int] = None):
        """使列表缓存失效"""
        # 删除特定项目的缓存
        if project_id is not None:
            key = cls._make_list_key(prefix, tenant_id, project_id)
            await cls.delete(key)
        
        # 删除租户级别的缓存（所有项目）
        key = cls._make_list_key(prefix, tenant_id, None)
        await cls.delete(key)
        
        # 删除所有相关的列表缓存
        pattern = f"{prefix}:list:tenant:{tenant_id}:*"
        await cls.delete_pattern(pattern)
    
    @classmethod
    async def invalidate_detail_cache(cls, prefix: str, item_id: int):
        """使详情缓存失效"""
        key = cls._make_key(prefix, "detail", item_id)
        await cls.delete(key)


def cache_list(prefix: str, ttl: int = CacheService.LIST_TTL):
    """列表缓存装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 提取租户ID和项目ID
            tenant_id = kwargs.get('tenant_id')
            project_id = kwargs.get('project_id')
            
            if tenant_id is None:
                # 如果没有tenant_id，直接执行函数
                return await func(*args, **kwargs)
            
            # 生成缓存键
            cache_key = CacheService._make_list_key(prefix, tenant_id, project_id)
            
            # 尝试从缓存获取
            cached_data = await CacheService.get(cache_key)
            if cached_data is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_data
            
            # 缓存未命中，执行函数
            logger.debug(f"缓存未命中: {cache_key}")
            result = await func(*args, **kwargs)
            
            # 存入缓存
            await CacheService.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


def cache_detail(prefix: str, ttl: int = CacheService.DETAIL_TTL):
    """详情缓存装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 提取ID参数
            item_id = kwargs.get('item_id') or (args[0] if args else None)
            
            if item_id is None:
                # 如果没有ID，直接执行函数
                return await func(*args, **kwargs)
            
            # 生成缓存键
            cache_key = CacheService._make_key(prefix, "detail", item_id)
            
            # 尝试从缓存获取
            cached_data = await CacheService.get(cache_key)
            if cached_data is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_data
            
            # 缓存未命中，执行函数
            logger.debug(f"缓存未命中: {cache_key}")
            result = await func(*args, **kwargs)
            
            # 存入缓存
            await CacheService.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator