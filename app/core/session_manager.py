"""基于 Redis 的会话管理（多租户支持）"""
import json
import time
from typing import Optional, Dict, Any
from loguru import logger
import redis.asyncio as redis


class SessionManager:
    """Redis 会话管理器"""
    
    def __init__(self, redis_client: redis.Redis, prefix: str = "session", default_ttl: int = 86400):
        """
        初始化会话管理器
        
        Args:
            redis_client: Redis 客户端
            prefix: 会话键前缀
            default_ttl: 默认过期时间（秒），默认 24 小时
        """
        self.redis = redis_client
        self.prefix = prefix
        self.default_ttl = default_ttl
    
    def _get_key(self, session_id: str) -> str:
        """生成会话键"""
        return f"{self.prefix}:{session_id}"
    
    async def create_session(
        self, 
        session_id: str, 
        user_id: int,
        tenant_id: int,
        username: str,
        additional_data: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        创建会话
        
        Args:
            session_id: 会话 ID（通常是 JWT token 或其他唯一标识）
            user_id: 用户 ID
            tenant_id: 租户 ID
            username: 用户名
            additional_data: 额外数据
            ttl: 过期时间（秒）
        
        Returns:
            是否创建成功
        """
        session_data = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "username": username,
            "created_at": int(time.time()),
            "last_access": int(time.time())
        }
        
        if additional_data:
            session_data.update(additional_data)
        
        try:
            key = self._get_key(session_id)
            await self.redis.setex(
                key,
                ttl or self.default_ttl,
                json.dumps(session_data)
            )
            logger.debug(f"创建会话: session_id={session_id}, user_id={user_id}, tenant_id={tenant_id}")
            return True
        except Exception as e:
            logger.error(f"创建会话失败: session_id={session_id}, error={str(e)}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话数据
        
        Args:
            session_id: 会话 ID
        
        Returns:
            会话数据或 None
        """
        try:
            key = self._get_key(session_id)
            data = await self.redis.get(key)
            
            if data:
                session_data = json.loads(data)
                # 更新最后访问时间
                session_data["last_access"] = int(time.time())
                await self.redis.setex(key, self.default_ttl, json.dumps(session_data))
                return session_data
            
            return None
        except Exception as e:
            logger.error(f"获取会话失败: session_id={session_id}, error={str(e)}")
            return None
    
    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        更新会话数据
        
        Args:
            session_id: 会话 ID
            data: 要更新的数据
        
        Returns:
            是否更新成功
        """
        try:
            session_data = await self.get_session(session_id)
            if session_data is None:
                return False
            
            session_data.update(data)
            session_data["last_access"] = int(time.time())
            
            key = self._get_key(session_id)
            await self.redis.setex(key, self.default_ttl, json.dumps(session_data))
            return True
        except Exception as e:
            logger.error(f"更新会话失败: session_id={session_id}, error={str(e)}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话 ID
        
        Returns:
            是否删除成功
        """
        try:
            key = self._get_key(session_id)
            result = await self.redis.delete(key)
            logger.debug(f"删除会话: session_id={session_id}")
            return result > 0
        except Exception as e:
            logger.error(f"删除会话失败: session_id={session_id}, error={str(e)}")
            return False
    
    async def refresh_session(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """
        刷新会话过期时间
        
        Args:
            session_id: 会话 ID
            ttl: 新的过期时间（秒）
        
        Returns:
            是否刷新成功
        """
        try:
            key = self._get_key(session_id)
            result = await self.redis.expire(key, ttl or self.default_ttl)
            return result
        except Exception as e:
            logger.error(f"刷新会话失败: session_id={session_id}, error={str(e)}")
            return False
    
    async def get_user_sessions(self, user_id: int) -> list:
        """
        获取用户的所有会话（通过扫描）
        
        Args:
            user_id: 用户 ID
        
        Returns:
            会话 ID 列表
        """
        try:
            pattern = f"{self.prefix}:*"
            sessions = []
            
            async for key in self.redis.scan_iter(match=pattern, count=100):
                data = await self.redis.get(key)
                if data:
                    session_data = json.loads(data)
                    if session_data.get("user_id") == user_id:
                        session_id = key.replace(f"{self.prefix}:", "")
                        sessions.append(session_id)
            
            return sessions
        except Exception as e:
            logger.error(f"获取用户会话失败: user_id={user_id}, error={str(e)}")
            return []
    
    async def delete_user_sessions(self, user_id: int) -> int:
        """
        删除用户的所有会话
        
        Args:
            user_id: 用户 ID
        
        Returns:
            删除的会话数量
        """
        try:
            sessions = await self.get_user_sessions(user_id)
            count = 0
            for session_id in sessions:
                if await self.delete_session(session_id):
                    count += 1
            
            logger.info(f"删除用户所有会话: user_id={user_id}, count={count}")
            return count
        except Exception as e:
            logger.error(f"删除用户会话失败: user_id={user_id}, error={str(e)}")
            return 0
    
    async def get_tenant_active_sessions(self, tenant_id: int) -> int:
        """
        获取租户的活跃会话数
        
        Args:
            tenant_id: 租户 ID
        
        Returns:
            活跃会话数
        """
        try:
            pattern = f"{self.prefix}:*"
            count = 0
            
            async for key in self.redis.scan_iter(match=pattern, count=100):
                data = await self.redis.get(key)
                if data:
                    session_data = json.loads(data)
                    if session_data.get("tenant_id") == tenant_id:
                        count += 1
            
            return count
        except Exception as e:
            logger.error(f"获取租户活跃会话数失败: tenant_id={tenant_id}, error={str(e)}")
            return 0

