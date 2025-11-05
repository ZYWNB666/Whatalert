"""用户相关 Schema"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., description="用户名", min_length=3, max_length=50)
    email: EmailStr = Field(..., description="邮箱")
    full_name: Optional[str] = Field(None, description="姓名", max_length=100)
    phone: Optional[str] = Field(None, description="手机号", max_length=20)
    is_active: bool = Field(True, description="是否激活")
    is_superuser: bool = Field(False, description="是否超级管理员")


class UserCreate(UserBase):
    """创建用户"""
    password: str = Field(..., description="密码", min_length=6, max_length=50)
    role_ids: List[int] = Field(default_factory=list, description="角色ID列表")


class UserUpdate(BaseModel):
    """更新用户"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    role_ids: Optional[List[int]] = None


class UserPasswordUpdate(BaseModel):
    """修改密码"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., description="新密码", min_length=6, max_length=50)


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    is_active: bool
    is_superuser: bool
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserWithRolesResponse(UserResponse):
    """用户响应(含角色)"""
    role_names: List[str] = Field(default_factory=list, description="角色名称列表")
    
    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    """角色基础模型"""
    name: str = Field(..., description="角色名称", max_length=50)
    code: str = Field(..., description="角色代码", max_length=50)
    description: Optional[str] = Field(None, description="描述", max_length=200)


class RoleCreate(RoleBase):
    """创建角色"""
    permission_ids: List[int] = Field(default_factory=list, description="权限ID列表")


class RoleUpdate(BaseModel):
    """更新角色"""
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None


class RoleResponse(RoleBase):
    """角色响应"""
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    """权限响应"""
    id: int
    name: str
    code: str
    resource: str
    action: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

