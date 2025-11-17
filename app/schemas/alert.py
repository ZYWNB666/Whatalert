"""告警相关 Schema"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class AlertRuleBase(BaseModel):
    """告警规则基础模型"""
    name: str = Field(..., description="规则名称")
    description: Optional[str] = Field(None, description="描述")
    expr: str = Field(..., description="PromQL表达式")
    eval_interval: int = Field(60, description="评估间隔(秒)")
    for_duration: int = Field(60, description="持续时间(秒)")
    repeat_interval: int = Field(1800, description="重复发送间隔(秒)")
    severity: str = Field("warning", description="告警等级")
    labels: Dict[str, Any] = Field(default_factory=dict, description="标签")
    annotations: Dict[str, str] = Field(default_factory=dict, description="注释")
    route_config: Dict[str, Any] = Field(default_factory=dict, description="路由配置")
    is_enabled: bool = Field(True, description="是否启用")
    datasource_id: int = Field(..., description="数据源ID")


class AlertRuleCreate(AlertRuleBase):
    """创建告警规则"""
    project_id: int = Field(..., description="项目ID")


class AlertRuleUpdate(AlertRuleBase):
    """更新告警规则"""
    name: Optional[str] = None
    expr: Optional[str] = None
    datasource_id: Optional[int] = None


class AlertRuleResponse(AlertRuleBase):
    """告警规则响应"""
    id: int
    tenant_id: int
    project_id: int
    created_at: int
    updated_at: int

    class Config:
        from_attributes = True


class AlertEventResponse(BaseModel):
    """告警事件响应"""
    id: int
    fingerprint: str
    rule_id: int
    rule_name: str
    status: str
    severity: str
    started_at: int
    last_eval_at: int
    last_sent_at: int
    value: Optional[float]
    labels: Dict[str, Any]
    annotations: Dict[str, str]
    expr: Optional[str]
    tenant_id: int

    class Config:
        from_attributes = True


class AlertEventHistoryResponse(BaseModel):
    """历史告警事件响应"""
    id: int
    fingerprint: str
    rule_id: Optional[int]
    rule_name: Optional[str]
    status: Optional[str]
    severity: Optional[str]
    started_at: Optional[int]
    resolved_at: Optional[int]
    duration: Optional[int]
    value: Optional[float]
    labels: Dict[str, Any]
    annotations: Dict[str, str]
    expr: Optional[str]
    tenant_id: int

    class Config:
        from_attributes = True

