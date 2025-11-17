"""告警规则测试相关的 Schema"""
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class AlertRuleTestRequest(BaseModel):
    """告警规则测试请求"""
    datasource_id: int = Field(..., description="数据源ID")
    expr: str = Field(..., min_length=1, description="PromQL 表达式")
    for_duration: Optional[int] = Field(None, description="持续时间（秒）")


class AlertRuleTestMetric(BaseModel):
    """测试结果中的指标"""
    metric: Dict[str, str] = Field(default_factory=dict, description="指标标签")
    value: List[Any] = Field(default_factory=list, description="[时间戳, 值]")


class AlertRuleTestResponse(BaseModel):
    """告警规则测试响应"""
    success: bool = Field(..., description="是否成功")
    result_count: int = Field(0, description="匹配结果总数")
    results: List[AlertRuleTestMetric] = Field(default_factory=list, description="前10条结果")
    query_time: Optional[float] = Field(None, description="查询耗时（秒）")
    timestamp: Optional[int] = Field(None, description="查询时间戳")
    error: Optional[str] = Field(None, description="错误信息")
    error_type: Optional[str] = Field(None, description="错误类型: syntax/connection/execution")
    message: Optional[str] = Field(None, description="提示消息")
