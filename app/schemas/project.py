"""项目相关的 Schema"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class ProjectBase(BaseModel):
    """项目基础信息"""
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    code: str = Field(..., min_length=1, max_length=50, description="项目代码")
    description: Optional[str] = Field(None, description="项目描述")
    is_active: bool = Field(True, description="是否激活")
    settings: Dict[str, Any] = Field(default_factory=dict, description="项目设置")


class ProjectCreate(ProjectBase):
    """创建项目"""
    pass


class ProjectUpdate(BaseModel):
    """更新项目"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectResponse(ProjectBase):
    """项目响应"""
    id: int
    is_default: bool
    tenant_id: int
    created_at: int
    updated_at: int
    
    # 扩展信息
    member_count: Optional[int] = Field(None, description="成员数量")
    alert_rule_count: Optional[int] = Field(None, description="告警规则数量")
    user_role: Optional[str] = Field(None, description="当前用户在项目中的角色")
    
    class Config:
        from_attributes = True


class ProjectMemberAdd(BaseModel):
    """添加项目成员"""
    user_id: int = Field(..., description="用户ID")
    role: str = Field("viewer", description="角色: admin/maintainer/viewer")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ['admin', 'maintainer', 'viewer']
        if v not in allowed_roles:
            raise ValueError(f'角色必须是以下之一: {", ".join(allowed_roles)}')
        return v


class ProjectMemberUpdate(BaseModel):
    """更新项目成员角色"""
    role: str = Field(..., description="角色: admin/maintainer/viewer")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ['admin', 'maintainer', 'viewer']
        if v not in allowed_roles:
            raise ValueError(f'角色必须是以下之一: {", ".join(allowed_roles)}')
        return v


class ProjectMemberResponse(BaseModel):
    """项目成员响应"""
    user_id: int
    username: str
    email: Optional[str] = None
    role: str
    created_at: int
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    total: int
    projects: List[ProjectResponse]
