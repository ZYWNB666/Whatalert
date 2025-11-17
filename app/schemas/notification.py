"""通知渠道 Schema"""
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class NotificationChannelBase(BaseModel):
    """通知渠道基础模型"""
    name: str = Field(..., description="渠道名称")
    type: str = Field(..., description="渠道类型")  # feishu, dingtalk, wechat, email, webhook
    description: Optional[str] = Field(None, description="描述")
    config: Dict[str, Any] = Field(..., description="渠道配置")
    filter_config: Dict[str, Any] = Field(default_factory=dict, description="过滤配置")
    is_enabled: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否默认渠道")
    project_id: Optional[int] = Field(None, description="项目ID")


class NotificationChannelCreate(NotificationChannelBase):
    """创建通知渠道"""
    pass


class NotificationChannelUpdate(BaseModel):
    """更新通知渠道"""
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    filter_config: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None


class NotificationChannelResponse(NotificationChannelBase):
    """通知渠道响应"""
    id: int
    tenant_id: int
    project_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

