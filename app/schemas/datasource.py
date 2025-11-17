"""数据源 Schema"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class DataSourceBase(BaseModel):
    """数据源基础模型"""
    name: str = Field(..., description="数据源名称")
    type: str = Field(..., description="数据源类型")  # prometheus, victoriametrics
    url: str = Field(..., description="数据源地址")
    description: Optional[str] = Field(None, description="描述")
    is_default: bool = Field(False, description="是否默认数据源")
    is_enabled: bool = Field(True, description="是否启用")
    auth_config: Dict[str, Any] = Field(default_factory=dict, description="认证配置")
    http_config: Dict[str, Any] = Field(default_factory=dict, description="HTTP配置")
    extra_labels: Dict[str, Any] = Field(default_factory=dict, description="额外标签")


class DataSourceCreate(DataSourceBase):
    """创建数据源"""
    project_id: int = Field(..., description="项目ID")


class DataSourceUpdate(BaseModel):
    """更新数据源"""
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    is_enabled: Optional[bool] = None
    auth_config: Optional[Dict[str, Any]] = None
    http_config: Optional[Dict[str, Any]] = None
    extra_labels: Optional[Dict[str, Any]] = None


class DataSourceResponse(DataSourceBase):
    """数据源响应"""
    id: int
    tenant_id: int
    project_id: int
    created_at: int
    updated_at: int

    class Config:
        from_attributes = True

