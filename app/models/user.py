"""用户、角色、权限模型"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.models.project import project_user


# 用户-角色关联表
user_roles = Table(
    'user_roles',
    BaseModel.metadata,
    Column('user_id', Integer, ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('role.id', ondelete='CASCADE'), primary_key=True),
)

# 角色-权限关联表
role_permissions = Table(
    'role_permissions',
    BaseModel.metadata,
    Column('role_id', Integer, ForeignKey('role.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permission.id', ondelete='CASCADE'), primary_key=True),
)


class User(BaseModel):
    """用户模型"""
    __tablename__ = "user"

    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, index=True, comment="邮箱")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    full_name = Column(String(100), comment="姓名")
    phone = Column(String(20), comment="手机号")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    is_superuser = Column(Boolean, default=False, nullable=False, comment="是否超级管理员")
    
    # 多租户支持
    tenant_id = Column(Integer, ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True, comment="租户ID")
    
    # 关系
    tenant = relationship("Tenant", back_populates="users")
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    projects = relationship("Project", secondary=project_user, back_populates="users")

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


class Role(BaseModel):
    """角色模型"""
    __tablename__ = "role"

    name = Column(String(50), nullable=False, comment="角色名称")
    code = Column(String(50), nullable=False, index=True, comment="角色代码")
    description = Column(String(200), comment="描述")
    tenant_id = Column(Integer, ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True, comment="租户ID")
    
    # 关系
    tenant = relationship("Tenant", back_populates="roles")
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

    def __repr__(self):
        return f"<Role(name='{self.name}', code='{self.code}')>"


class Permission(BaseModel):
    """权限模型"""
    __tablename__ = "permission"

    name = Column(String(50), nullable=False, comment="权限名称")
    code = Column(String(100), unique=True, nullable=False, index=True, comment="权限代码")
    resource = Column(String(50), nullable=False, comment="资源类型")  # alert_rule, datasource, etc.
    action = Column(String(20), nullable=False, comment="操作类型")    # create, read, update, delete
    description = Column(String(200), comment="描述")
    
    # 关系
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    def __repr__(self):
        return f"<Permission(code='{self.code}', resource='{self.resource}', action='{self.action}')>"

