"""分布式锁实现"""
import asyncio
import uuid
from typing import Optional
from loguru import logger
import redis.asyncio as redis


class DistributedLock:
    """基于 Redis 的分布式锁"""
    
    def __init__(self, redis_client: redis.Redis, lock_name: str, timeout: int = 30, retry_interval: float = 0.1):
        """
        初始化分布式锁
        
        Args:
            redis_client: Redis 客户端
            lock_name: 锁名称
            timeout: 锁超时时间（秒）
            retry_interval: 重试间隔（秒）
        """
        self.redis = redis_client
        self.lock_name = f"lock:{lock_name}"
        self.timeout = timeout
        self.retry_interval = retry_interval
        self.lock_value = str(uuid.uuid4())  # 唯一标识，确保只有持锁者能释放
        self._locked = False
    
    async def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        获取锁
        
        Args:
            blocking: 是否阻塞等待
            timeout: 等待超时时间（秒），None 表示无限等待
        
        Returns:
            是否成功获取锁
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # 尝试设置锁（NX: 仅当键不存在时设置，EX: 设置过期时间）
            acquired = await self.redis.set(
                self.lock_name,
                self.lock_value,
                nx=True,
                ex=self.timeout
            )
            
            if acquired:
                self._locked = True
                logger.debug(f"获取分布式锁成功: {self.lock_name}")
                return True
            
            # 非阻塞模式直接返回
            if not blocking:
                return False
            
            # 检查是否超时
            if timeout is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    logger.warning(f"获取分布式锁超时: {self.lock_name}, timeout={timeout}s")
                    return False
            
            # 等待后重试
            await asyncio.sleep(self.retry_interval)
    
    async def release(self) -> bool:
        """
        释放锁（使用 Lua 脚本确保原子性）
        
        Returns:
            是否成功释放
        """
        if not self._locked:
            return False
        
        # Lua 脚本：只有持锁者才能释放锁
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        try:
            result = await self.redis.eval(lua_script, 1, self.lock_name, self.lock_value)
            if result:
                self._locked = False
                logger.debug(f"释放分布式锁成功: {self.lock_name}")
                return True
            else:
                logger.warning(f"释放分布式锁失败（锁不属于当前持有者）: {self.lock_name}")
                return False
        except Exception as e:
            logger.error(f"释放分布式锁异常: {self.lock_name}, error={str(e)}")
            return False
    
    async def extend(self, additional_time: int) -> bool:
        """
        延长锁的过期时间
        
        Args:
            additional_time: 额外的时间（秒）
        
        Returns:
            是否成功延长
        """
        if not self._locked:
            return False
        
        # Lua 脚本：只有持锁者才能延长锁
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        
        try:
            result = await self.redis.eval(
                lua_script, 
                1, 
                self.lock_name, 
                self.lock_value,
                self.timeout + additional_time
            )
            return bool(result)
        except Exception as e:
            logger.error(f"延长分布式锁失败: {self.lock_name}, error={str(e)}")
            return False
    
    async def is_locked(self) -> bool:
        """检查锁是否存在"""
        return await self.redis.exists(self.lock_name) > 0
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.release()


class AlertLockManager:
    """告警锁管理器 - 防止重复发送告警"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def get_alert_lock(self, fingerprint: str, timeout: int = 60) -> DistributedLock:
        """
        获取告警锁
        
        Args:
            fingerprint: 告警指纹
            timeout: 锁超时时间（秒）
        
        Returns:
            分布式锁对象
        """
        return DistributedLock(self.redis, f"alert:{fingerprint}", timeout=timeout)
    
    def get_group_lock(self, group_key: str, timeout: int = 30) -> DistributedLock:
        """
        获取分组锁
        
        Args:
            group_key: 分组键
            timeout: 锁超时时间（秒）
        
        Returns:
            分布式锁对象
        """
        return DistributedLock(self.redis, f"group:{group_key}", timeout=timeout)
    
    async def is_alert_sending(self, fingerprint: str) -> bool:
        """
        检查告警是否正在发送
        
        Args:
            fingerprint: 告警指纹
        
        Returns:
            是否正在发送
        """
        lock_key = f"lock:alert:{fingerprint}"
        return await self.redis.exists(lock_key) > 0

