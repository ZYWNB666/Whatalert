"""审计日志中间件"""
import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from loguru import logger


class AuditMiddleware(BaseHTTPMiddleware):
    """审计日志中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # 需要记录审计日志的路径前缀
        self.audit_paths = [
            "/api/v1/users",
            "/api/v1/alert-rules",
            "/api/v1/datasources",
            "/api/v1/notifications",
            "/api/v1/silence",
            "/api/v1/settings",
        ]
        
        # 不记录审计日志的路径
        self.exclude_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/health",
            "/docs",
            "/openapi.json",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        path = request.url.path
        method = request.method
        
        # 判断是否需要记录审计日志
        should_audit = False
        for audit_path in self.audit_paths:
            if path.startswith(audit_path):
                should_audit = True
                break
        
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                should_audit = False
                break
        
        # GET 请求通常不记录（只读操作）
        if method == "GET":
            should_audit = False
        
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 记录审计日志
        if should_audit and response.status_code < 500:
            try:
                await self._create_audit_log(request, response, process_time)
            except Exception as e:
                logger.error(f"创建审计日志失败: {str(e)}")
        
        return response
    
    async def _create_audit_log(self, request: Request, response: Response, process_time: float):
        """创建审计日志"""
        from app.db.database import AsyncSessionLocal
        from app.api.audit import create_audit_log
        from app.core.security import decode_access_token
        from app.models.user import User
        from sqlalchemy import select
        
        # 获取用户信息
        user = getattr(request.state, "user", None)
        
        # 如果state中没有user，尝试从token解析
        if not user:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return
            
            token = auth_header.replace("Bearer ", "")
            payload = decode_access_token(token)
            if not payload:
                return
            
            username = payload.get("sub")
            if not username:
                return
            
            # 从数据库获取用户
            async with AsyncSessionLocal() as db:
                stmt = select(User).where(User.username == username)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                if not user:
                    return
        
        # 解析操作类型和资源类型
        action, resource_type = self._parse_action_and_resource(request.method, request.url.path)
        
        # 获取资源名称和ID
        resource_id = None
        resource_name = None
        
        # 尝试从路径中提取资源ID
        path_parts = request.url.path.strip('/').split('/')
        if len(path_parts) > 3 and path_parts[-1].isdigit():
            resource_id = int(path_parts[-1])
        
        # 获取IP地址
        ip_address = request.client.host if request.client else None
        if "x-forwarded-for" in request.headers:
            ip_address = request.headers["x-forwarded-for"].split(",")[0].strip()
        
        # 获取User Agent
        user_agent = request.headers.get("user-agent", "")
        
        # 判断状态
        status = "success" if response.status_code < 400 else "failed"
        
        # 创建日志
        async with AsyncSessionLocal() as db:
            await create_audit_log(
                db=db,
                action=action,
                resource_type=resource_type,
                user=user,
                resource_id=resource_id,
                resource_name=resource_name,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else None,
                request_method=request.method,
                request_path=request.url.path,
                changes=None,  # 如果需要记录变更内容，可以在这里实现
                status=status
            )
    
    def _parse_action_and_resource(self, method: str, path: str) -> tuple:
        """解析操作类型和资源类型"""
        # 从路径中提取资源类型
        resource_map = {
            "users": "user",
            "alert-rules": "alert_rule",
            "datasources": "datasource",
            "notifications": "notification",
            "silence": "silence",
            "settings": "settings",
        }
        
        resource_type = "unknown"
        for key, value in resource_map.items():
            if key in path:
                resource_type = value
                break
        
        # 从方法映射操作类型
        action_map = {
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
        }
        
        action = action_map.get(method, "unknown")
        
        return action, resource_type

