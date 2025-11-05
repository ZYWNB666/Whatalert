"""审计日志 Schema"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AuditLogCreate(BaseModel):
    """创建审计日志"""
    action: str = Field(..., description="操作类型")
    resource_type: str = Field(..., description="资源类型")
    resource_id: Optional[int] = Field(None, description="资源ID")
    resource_name: Optional[str] = Field(None, description="资源名称")
    user_id: Optional[int] = Field(None, description="用户ID")
    username: Optional[str] = Field(None, description="用户名")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="User Agent")
    request_method: Optional[str] = Field(None, description="请求方法")
    request_path: Optional[str] = Field(None, description="请求路径")
    changes: Optional[Dict[str, Any]] = Field(None, description="变更内容")
    status: str = Field("success", description="状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    tenant_id: Optional[int] = Field(None, description="租户ID")


class AuditLogResponse(BaseModel):
    """审计日志响应"""
    id: int
    action: str
    resource_type: str
    resource_id: Optional[int]
    resource_name: Optional[str]
    user_id: Optional[int]
    username: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_method: Optional[str]
    request_path: Optional[str]
    changes: Optional[Dict[str, Any]]
    status: str
    error_message: Optional[str]
    timestamp: int
    tenant_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogQuery(BaseModel):
    """审计日志查询参数"""
    action: Optional[str] = None
    resource_type: Optional[str] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    status: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

