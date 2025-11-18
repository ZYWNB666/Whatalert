"""统一异常处理模块

提供项目级别的自定义异常类和错误码定义，用于规范化错误处理。
"""
from typing import Any, Dict, Optional
from fastapi import status


class AlertSystemException(Exception):
    """告警系统基础异常类
    
    所有自定义异常都应继承此类，提供统一的错误处理接口。
    
    Attributes:
        message: 错误消息
        code: 错误代码
        status_code: HTTP 状态码
        details: 额外的错误详情
    """
    
    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于 API 响应"""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }


class ResourceNotFoundException(AlertSystemException):
    """资源未找到异常"""
    
    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            message=f"{resource_type} not found",
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={
                "resource_type": resource_type,
                "resource_id": str(resource_id)
            }
        )


class PermissionDeniedException(AlertSystemException):
    """权限拒绝异常"""
    
    def __init__(self, resource: str, action: str):
        super().__init__(
            message=f"Permission denied for {action} on {resource}",
            code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
            details={
                "resource": resource,
                "action": action
            }
        )


class ValidationException(AlertSystemException):
    """数据验证异常"""
    
    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation failed for field '{field}': {message}",
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={
                "field": field,
                "validation_message": message
            }
        )


class DatabaseException(AlertSystemException):
    """数据库操作异常"""
    
    def __init__(self, operation: str, message: str):
        super().__init__(
            message=f"Database {operation} failed: {message}",
            code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                "operation": operation
            }
        )


class ExternalServiceException(AlertSystemException):
    """外部服务调用异常"""
    
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service '{service}' error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={
                "service": service
            }
        )


class ConfigurationException(AlertSystemException):
    """配置错误异常"""
    
    def __init__(self, config_key: str, message: str):
        super().__init__(
            message=f"Configuration error for '{config_key}': {message}",
            code="CONFIGURATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                "config_key": config_key
            }
        )


class RateLimitException(AlertSystemException):
    """速率限制异常"""
    
    def __init__(self, limit: str, retry_after: Optional[int] = None):
        super().__init__(
            message=f"Rate limit exceeded: {limit}",
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={
                "limit": limit,
                "retry_after": retry_after
            }
        )


class DuplicateResourceException(AlertSystemException):
    """资源重复异常"""
    
    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            message=f"{resource_type} with identifier '{identifier}' already exists",
            code="DUPLICATE_RESOURCE",
            status_code=status.HTTP_409_CONFLICT,
            details={
                "resource_type": resource_type,
                "identifier": identifier
            }
        )


class TenantIsolationException(AlertSystemException):
    """租户隔离违规异常"""
    
    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            message=f"Access denied: {resource_type} belongs to different tenant",
            code="TENANT_ISOLATION_VIOLATION",
            status_code=status.HTTP_403_FORBIDDEN,
            details={
                "resource_type": resource_type,
                "resource_id": str(resource_id)
            }
        )