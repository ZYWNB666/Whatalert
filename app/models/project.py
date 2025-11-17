"""项目模型"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, JSON, Text, Table
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, Base


# 项目-用户关联表
project_user = Table(
    'project_user',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('project.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    Column('role', String(50), default='member', comment='角色: owner/admin/member/viewer'),
    Column('created_at', Integer, comment='创建时间戳')
)


class Project(BaseModel):
    """项目模型 - 租户下的二级隔离单位"""
    __tablename__ = "project"

    name = Column(String(100), nullable=False, comment="项目名称")
    code = Column(String(50), nullable=False, comment="项目代码")
    description = Column(Text, comment="描述")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    is_default = Column(Boolean, default=False, nullable=False, comment="是否为默认项目")
    
    # 项目配置
    settings = Column(JSON, nullable=False, default=lambda: {}, comment="项目设置")
    # 示例: {
    #   "alert_prefix": "PRJ-",           # 告警前缀
    #   "default_severity": "warning",    # 默认告警级别
    #   "max_alert_rules": 100,           # 告警规则配额
    #   "max_datasources": 10,            # 数据源配额
    #   "notification_settings": {}       # 通知设置
    # }
    
    # 多租户
    tenant_id = Column(Integer, ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # 关系
    tenant = relationship("Tenant", back_populates="projects")
    users = relationship("User", secondary=project_user, back_populates="projects")
    alert_rules = relationship("AlertRule", back_populates="project", cascade="all, delete-orphan")
    datasources = relationship("DataSource", back_populates="project", cascade="all, delete-orphan")
    notification_channels = relationship("NotificationChannel", back_populates="project", cascade="all, delete-orphan")
    silence_rules = relationship("SilenceRule", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(name='{self.name}', code='{self.code}', tenant_id={self.tenant_id})>"
    
    def get_user_role(self, user_id: int) -> str:
        """获取用户在项目中的角色"""
        from sqlalchemy import select
        stmt = select(project_user.c.role).where(
            project_user.c.project_id == self.id,
            project_user.c.user_id == user_id
        )
        # 需要在异步上下文中执行
        return None  # 占位，实际需要通过 session 查询
    
    def check_quota(self, resource_type: str, current_count: int) -> bool:
        """检查配额限制"""
        quota_key = f"max_{resource_type}"
        max_count = self.settings.get(quota_key)
        
        if max_count is None:
            return True  # 无限制
        
        return current_count < max_count
