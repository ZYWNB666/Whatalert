"""
Redis 高级缓存服务

包含以下高级特性：
1. 缓存预热 (Cache Warming)
2. 缓存穿透保护 (Cache Penetration Protection)
3. 缓存雪崩防护 (Cache Avalanche Protection)
4. 热点数据识别 (Hot Data Detection)
5. 分布式锁 (Distributed Lock)
6. 消息队列 (Message Queue)
7. 实时统计 (Real-time Statistics)
8. 布隆过滤器 (Bloom Filter)
"""

import asyncio
import hashlib
import json
import random
import time
from typing import Any, Dict, List, Optional, Callable
from loguru import logger
from app.db.redis_client import get_redis


class AdvancedCacheService:
    """高级缓存服务"""
    
    # 热点数据阈值（访问次数）
    HOT_DATA_THRESHOLD = 100
    
    # 布隆过滤器配置
    BLOOM_FILTER_KEY = "bloom:filter:exists"
    BLOOM_FILTER_SIZE = 10000000  # 1000万
    BLOOM_FILTER_HASH_COUNT = 7
    
    @staticmethod
    async def get_with_protection(
        key: str,
        fetch_func: Callable,
        ttl: int = 300,
        empty_ttl: int = 60
    ) -> Optional[Any]:
        """
        带缓存穿透保护的获取
        
        Args:
            key: 缓存键
            fetch_func: 数据获取函数（异步）
            ttl: 正常数据的TTL（秒）
            empty_ttl: 空数据的TTL（秒）
        
        Returns:
            缓存数据或None
        """
        redis = await get_redis()
        start_time = time.time()
        
        # 1. 先检查布隆过滤器（快速判断数据是否可能存在）
        exists_in_bloom = await AdvancedCacheService._bloom_check(key)
        if not exists_in_bloom:
            logger.warning(f"布隆过滤器判断数据不存在: {key}")
            # 缓存空结果，防止缓存穿透
            await redis.setex(f"{key}:empty", empty_ttl, "1")
            return None
        
        # 2. 尝试从缓存获取
        cached = await redis.get(key)
        if cached is not None:
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"缓存命中（带保护）: {key} (耗时: {elapsed:.2f}ms)")
            
            # 记录访问次数（用于热点数据识别）
            await AdvancedCacheService._record_access(key)
            
            # 检查是否是空值标记
            if cached == b"__EMPTY__":
                return None
            
            try:
                return json.loads(cached)
            except:
                return cached.decode('utf-8')
        
        # 3. 检查是否已标记为空
        is_empty = await redis.get(f"{key}:empty")
        if is_empty:
            logger.info(f"命中空值缓存: {key}")
            return None
        
        # 4. 使用分布式锁防止缓存击穿
        lock_key = f"lock:{key}"
        lock_acquired = await AdvancedCacheService._acquire_lock(lock_key, timeout=10)
        
        if lock_acquired:
            try:
                # 再次检查缓存（双重检查）
                cached = await redis.get(key)
                if cached is not None:
                    if cached == b"__EMPTY__":
                        return None
                    try:
                        return json.loads(cached)
                    except:
                        return cached.decode('utf-8')
                
                # 从数据库获取数据
                logger.info(f"缓存未命中，从数据库获取: {key}")
                data = await fetch_func()
                
                if data is None:
                    # 缓存空结果（防止缓存穿透）
                    await redis.setex(key, empty_ttl, "__EMPTY__")
                    logger.info(f"缓存空结果: {key} (TTL: {empty_ttl}s)")
                else:
                    # 添加随机TTL，防止缓存雪崩
                    random_ttl = ttl + random.randint(-30, 30)
                    
                    # 缓存数据
                    cache_value = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
                    await redis.setex(key, random_ttl, cache_value)
                    
                    # 添加到布隆过滤器
                    await AdvancedCacheService._bloom_add(key)
                    
                    logger.info(f"缓存设置成功（带保护）: {key} (TTL: {random_ttl}s)")
                
                return data
                
            finally:
                # 释放锁
                await AdvancedCacheService._release_lock(lock_key)
        else:
            # 获取锁失败，等待一小段时间后重试
            await asyncio.sleep(0.1)
            cached = await redis.get(key)
            if cached is not None and cached != b"__EMPTY__":
                try:
                    return json.loads(cached)
                except:
                    return cached.decode('utf-8')
            return None
    
    @staticmethod
    async def _acquire_lock(key: str, timeout: int = 10) -> bool:
        """
        获取分布式锁
        
        Args:
            key: 锁的键
            timeout: 锁的超时时间（秒）
        
        Returns:
            是否成功获取锁
        """
        redis = await get_redis()
        lock_value = f"{time.time()}:{random.randint(1000, 9999)}"
        
        # 使用 SET NX EX 原子操作
        result = await redis.set(key, lock_value, ex=timeout, nx=True)
        return result is not None
    
    @staticmethod
    async def _release_lock(key: str):
        """释放分布式锁"""
        redis = await get_redis()
        await redis.delete(key)
    
    @staticmethod
    async def _bloom_add(key: str):
        """添加到布隆过滤器"""
        redis = await get_redis()
        
        # 使用多个哈希函数
        for i in range(AdvancedCacheService.BLOOM_FILTER_HASH_COUNT):
            hash_value = int(hashlib.md5(f"{key}:{i}".encode()).hexdigest(), 16)
            bit_position = hash_value % AdvancedCacheService.BLOOM_FILTER_SIZE
            await redis.setbit(AdvancedCacheService.BLOOM_FILTER_KEY, bit_position, 1)
    
    @staticmethod
    async def _bloom_check(key: str) -> bool:
        """检查布隆过滤器"""
        redis = await get_redis()
        
        # 检查所有哈希位置
        for i in range(AdvancedCacheService.BLOOM_FILTER_HASH_COUNT):
            hash_value = int(hashlib.md5(f"{key}:{i}".encode()).hexdigest(), 16)
            bit_position = hash_value % AdvancedCacheService.BLOOM_FILTER_SIZE
            bit = await redis.getbit(AdvancedCacheService.BLOOM_FILTER_KEY, bit_position)
            if bit == 0:
                return False
        
        return True
    
    @staticmethod
    async def _record_access(key: str):
        """记录访问次数（用于热点数据识别）"""
        redis = await get_redis()
        access_key = f"access:count:{key}"
        
        # 增加访问计数
        count = await redis.incr(access_key)
        
        # 设置过期时间（1小时）
        if count == 1:
            await redis.expire(access_key, 3600)
        
        # 如果是热点数据，记录到热点集合
        if count >= AdvancedCacheService.HOT_DATA_THRESHOLD:
            await redis.zadd("hot:data", {key: count})
            logger.warning(f"检测到热点数据: {key} (访问次数: {count})")
    
    @staticmethod
    async def get_hot_data(limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取热点数据列表
        
        Args:
            limit: 返回数量
        
        Returns:
            热点数据列表
        """
        redis = await get_redis()
        
        # 从有序集合获取访问次数最多的键
        hot_keys = await redis.zrevrange("hot:data", 0, limit - 1, withscores=True)
        
        result = []
        for key, score in hot_keys:
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            result.append({
                "key": key,
                "access_count": int(score)
            })
        
        return result
    
    @staticmethod
    async def warmup_cache(warmup_tasks: List[Dict[str, Any]]):
        """
        缓存预热
        
        Args:
            warmup_tasks: 预热任务列表，每个任务包含 key, fetch_func, ttl
        
        Example:
            await AdvancedCacheService.warmup_cache([
                {
                    "key": "alert_rule:list:tenant:1",
                    "fetch_func": lambda: get_alert_rules(),
                    "ttl": 300
                }
            ])
        """
        logger.info(f"开始缓存预热，任务数: {len(warmup_tasks)}")
        redis = await get_redis()
        
        success_count = 0
        fail_count = 0
        
        for task in warmup_tasks:
            try:
                key = task["key"]
                fetch_func = task["fetch_func"]
                ttl = task.get("ttl", 300)
                
                # 检查缓存是否已存在
                exists = await redis.exists(key)
                if exists:
                    logger.info(f"缓存已存在，跳过: {key}")
                    continue
                
                # 获取数据
                data = await fetch_func()
                
                if data is not None:
                    # 缓存数据
                    cache_value = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
                    await redis.setex(key, ttl, cache_value)
                    
                    # 添加到布隆过滤器
                    await AdvancedCacheService._bloom_add(key)
                    
                    success_count += 1
                    logger.info(f"预热成功: {key}")
                else:
                    fail_count += 1
                    logger.warning(f"预热失败（数据为空）: {key}")
                
            except Exception as e:
                fail_count += 1
                logger.error(f"预热失败: {task.get('key', 'unknown')} - {str(e)}")
        
        logger.info(f"缓存预热完成，成功: {success_count}, 失败: {fail_count}")
    
    @staticmethod
    async def publish_message(channel: str, message: Dict[str, Any]):
        """
        发布消息到Redis频道
        
        Args:
            channel: 频道名称
            message: 消息内容
        """
        redis = await get_redis()
        message_str = json.dumps(message)
        await redis.publish(channel, message_str)
        logger.info(f"消息已发布到频道 {channel}: {message_str[:100]}")
    
    @staticmethod
    async def subscribe_messages(channel: str, callback: Callable):
        """
        订阅Redis频道消息
        
        Args:
            channel: 频道名称
            callback: 消息处理回调函数
        """
        redis = await get_redis()
        pubsub = redis.pubsub()
        
        await pubsub.subscribe(channel)
        logger.info(f"已订阅频道: {channel}")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await callback(data)
                    except Exception as e:
                        logger.error(f"处理消息失败: {str(e)}")
        finally:
            await pubsub.unsubscribe(channel)
    
    @staticmethod
    async def add_to_queue(queue_name: str, item: Dict[str, Any]):
        """
        添加任务到队列
        
        Args:
            queue_name: 队列名称
            item: 任务数据
        """
        redis = await get_redis()
        item_str = json.dumps(item)
        await redis.rpush(f"queue:{queue_name}", item_str)
        logger.info(f"任务已添加到队列 {queue_name}")
    
    @staticmethod
    async def get_from_queue(queue_name: str, timeout: int = 0) -> Optional[Dict[str, Any]]:
        """
        从队列获取任务
        
        Args:
            queue_name: 队列名称
            timeout: 阻塞超时时间（秒），0表示非阻塞
        
        Returns:
            任务数据或None
        """
        redis = await get_redis()
        
        if timeout > 0:
            result = await redis.blpop(f"queue:{queue_name}", timeout=timeout)
            if result:
                _, item_str = result
                return json.loads(item_str)
        else:
            item_str = await redis.lpop(f"queue:{queue_name}")
            if item_str:
                return json.loads(item_str)
        
        return None
    
    @staticmethod
    async def get_queue_length(queue_name: str) -> int:
        """获取队列长度"""
        redis = await get_redis()
        return await redis.llen(f"queue:{queue_name}")
    
    @staticmethod
    async def increment_counter(key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """
        增加计数器
        
        Args:
            key: 计数器键
            amount: 增加量
            ttl: 过期时间（秒）
        
        Returns:
            新的计数值
        """
        redis = await get_redis()
        new_value = await redis.incrby(key, amount)
        
        if ttl and new_value == amount:
            await redis.expire(key, ttl)
        
        return new_value
    
    @staticmethod
    async def get_counter(key: str) -> int:
        """获取计数器值"""
        redis = await get_redis()
        value = await redis.get(key)
        return int(value) if value else 0
    
    @staticmethod
    async def get_statistics() -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计数据
        """
        redis = await get_redis()
        
        # Redis 信息
        info = await redis.info()
        
        # 热点数据
        hot_data = await AdvancedCacheService.get_hot_data(10)
        
        # 缓存键统计
        all_keys = await redis.keys("*")
        key_stats = {}
        for key in all_keys:
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            
            prefix = key.split(":")[0] if ":" in key else "other"
            key_stats[prefix] = key_stats.get(prefix, 0) + 1
        
        return {
            "redis_version": info.get("redis_version"),
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_keys": len(all_keys),
            "key_stats": key_stats,
            "hot_data": hot_data,
            "uptime_days": info.get("uptime_in_days")
        }
    
    @staticmethod
    async def clear_hot_data():
        """清除热点数据记录"""
        redis = await get_redis()
        await redis.delete("hot:data")
        
        # 清除所有访问计数
        access_keys = await redis.keys("access:count:*")
        if access_keys:
            await redis.delete(*access_keys)
        
        logger.info("热点数据记录已清除")
    
    @staticmethod
    async def rebuild_bloom_filter(keys: List[str]):
        """
        重建布隆过滤器
        
        Args:
            keys: 需要添加到布隆过滤器的键列表
        """
        redis = await get_redis()
        
        # 删除旧的布隆过滤器
        await redis.delete(AdvancedCacheService.BLOOM_FILTER_KEY)
        
        # 添加所有键
        for key in keys:
            await AdvancedCacheService._bloom_add(key)
        
        logger.info(f"布隆过滤器重建完成，添加了 {len(keys)} 个键")