# Technical Design

## Context

当前系统采用租户（Tenant）作为最顶层的数据隔离单位，但在实际使用中，许多企业需要在同一租户下管理多个项目（如微服务架构下的不同服务）。每个项目有独立的告警规则、数据源和通知配置。

同时，现有的静默规则和告警规则编辑体验有待改进。

## Goals

1. **项目隔离**：提供租户下的二级隔离机制，支持项目级别的数据和权限管理
2. **静默增强**：实现类似 Alertmanager 的灵活标签匹配
3. **规则测试**：提供即时测试功能，提升用户体验

## Non-Goals

- 不改变现有租户隔离机制
- 不引入复杂的项目层级（只支持一级项目）
- 不支持跨项目的告警规则引用

## Decisions

### 1. 项目模型设计

#### 数据模型
```python
class Project(BaseModel):
    """项目模型"""
    __tablename__ = "project"
    
    name = Column(String(100), nullable=False, comment="项目名称")
    code = Column(String(50), nullable=False, comment="项目代码")
    description = Column(Text, comment="描述")
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_default = Column(Boolean, default=False, comment="是否为默认项目")
    
    # 项目配置
    settings = Column(JSON, default={}, comment="项目设置")
    # 示例: {
    #   "alert_prefix": "PRJ-",  # 告警前缀
    #   "default_severity": "warning",
    #   "notification_settings": {}
    # }
    
    # 多租户
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False, index=True)
    
    # 关系
    tenant = relationship("Tenant", back_populates="projects")
    users = relationship("User", secondary="project_user", back_populates="projects")
    alert_rules = relationship("AlertRule", back_populates="project")
```

#### 项目-用户关联表
```python
project_user = Table('project_user', Base.metadata,
    Column('project_id', Integer, ForeignKey('project.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('role', String(50), default='member'),  # owner, admin, member, viewer
    Column('created_at', BigInteger)
)
```

#### 向后兼容策略
- 所有现有表添加 `project_id` 字段，默认 NULL
- 添加数据库约束：`project_id` 为 NULL 时使用租户的默认项目
- 迁移脚本：
  1. 为每个租户创建默认项目（name="默认项目", is_default=True）
  2. 将所有现有数据的 project_id 设置为默认项目 ID
  3. 为所有现有用户添加到默认项目的关联

### 2. 静默规则匹配逻辑

#### 当前 matchers 结构（保持不变）
```json
[
  {"label": "alertname", "operator": "=", "value": "HighCPU"},
  {"label": "severity", "operator": "=~", "value": "warning|critical"},
  {"label": "environment", "operator": "!=", "value": "production"}
]
```

#### 匹配算法
```python
import re
from typing import Dict, List

def check_silence_match(alert_labels: Dict[str, str], matchers: List[Dict]) -> bool:
    """
    检查告警标签是否匹配静默规则
    
    Args:
        alert_labels: 告警标签字典，如 {"alertname": "HighCPU", "severity": "critical"}
        matchers: 匹配器列表
    
    Returns:
        bool: 所有 matcher 都匹配返回 True，否则返回 False
    """
    for matcher in matchers:
        label_name = matcher['label']
        operator = matcher['operator']
        expected_value = matcher['value']
        
        # 获取告警中的标签值
        actual_value = alert_labels.get(label_name, '')
        
        # 执行匹配
        if operator == '=':
            if actual_value != expected_value:
                return False
        elif operator == '!=':
            if actual_value == expected_value:
                return False
        elif operator == '=~':
            if not re.match(expected_value, actual_value):
                return False
        elif operator == '!~':
            if re.match(expected_value, actual_value):
                return False
        else:
            # 未知操作符，不匹配
            return False
    
    # 所有 matcher 都匹配
    return True
```

#### 支持的操作符
- `=`: 精确匹配
- `!=`: 不等于
- `=~`: 正则表达式匹配
- `!~`: 正则表达式不匹配

### 3. 告警规则测试功能

#### API 设计
```python
POST /api/v1/alert-rules/test
Content-Type: application/json

Request:
{
  "datasource_id": 1,
  "expr": "up{job=\"prometheus\"} == 0",
  "for_duration": 60  # 可选，用于说明
}

Response (成功):
{
  "success": true,
  "result_count": 3,
  "results": [
    {
      "metric": {
        "job": "prometheus",
        "instance": "localhost:9090",
        "__name__": "up"
      },
      "value": [1732000000, "0"],
      "labels": {
        "job": "prometheus",
        "instance": "localhost:9090"
      }
    }
    // ... 最多 10 条
  ],
  "query_time": 0.123,  # 查询耗时（秒）
  "timestamp": 1732000000
}

Response (查询错误):
{
  "success": false,
  "error": "parse error: unexpected character: '!'",
  "error_type": "syntax"
}

Response (无数据):
{
  "success": true,
  "result_count": 0,
  "results": [],
  "message": "查询成功，但没有匹配到任何数据"
}
```

#### 实现逻辑
```python
from prometheus_api_client import PrometheusConnect

async def test_alert_rule(datasource_id: int, expr: str, db: AsyncSession):
    """测试告警规则"""
    # 1. 获取数据源
    datasource = await db.get(DataSource, datasource_id)
    if not datasource:
        raise HTTPException(404, "Data source not found")
    
    # 2. 创建 Prometheus 客户端
    prom = PrometheusConnect(
        url=datasource.url,
        headers=datasource.auth_config.get('headers', {}),
        disable_ssl=datasource.auth_config.get('disable_ssl', False)
    )
    
    # 3. 执行查询
    try:
        import time
        start_time = time.time()
        result = prom.custom_query(query=expr)
        query_time = time.time() - start_time
        
        # 4. 解析结果，最多返回 10 条
        results = []
        for item in result[:10]:
            results.append({
                'metric': item.get('metric', {}),
                'value': item.get('value', []),
                'labels': item.get('metric', {})
            })
        
        return {
            'success': True,
            'result_count': len(result),
            'results': results,
            'query_time': round(query_time, 3),
            'timestamp': int(time.time())
        }
        
    except Exception as e:
        # 解析错误类型
        error_msg = str(e)
        error_type = 'syntax' if 'parse error' in error_msg else 'execution'
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': error_type
        }
```

### 4. 前端交互设计

#### 告警规则测试 UI
```
┌─────────────────────────────────────────────────────┐
│ 编辑告警规则                                          │
├─────────────────────────────────────────────────────┤
│                                                       │
│ PromQL 表达式: [up{job="prometheus"} == 0        ]  │
│                                                       │
│ [更新] [取消] [测试]  ← 新增测试按钮                  │
│                                                       │
│ ┌─ 测试结果 ──────────────────────────────────┐    │
│ │ ✅ 查询成功，匹配到 3 条数据（耗时 0.123s）     │    │
│ │                                                 │    │
│ │ 1. job=prometheus, instance=localhost:9090      │    │
│ │    value: 0                                     │    │
│ │    时间: 2025-11-17 10:30:00                    │    │
│ │                                                 │    │
│ │ 2. job=prometheus, instance=192.168.1.100:9090  │    │
│ │    value: 0                                     │    │
│ │    时间: 2025-11-17 10:30:00                    │    │
│ │                                                 │    │
│ │ ... (共 3 条，显示前 10 条)                      │    │
│ └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

## Risks / Trade-offs

### 风险
1. **数据迁移风险**：现有数据需要迁移到新的项目结构
   - **缓解**：提供自动迁移脚本，创建默认项目
   - **回滚**：保留 tenant_id 字段，可回退到租户级别

2. **查询性能**：增加 project_id 过滤可能影响查询性能
   - **缓解**：添加 (tenant_id, project_id) 组合索引
   - **监控**：监控慢查询日志

3. **测试接口滥用**：频繁测试可能给 Prometheus 带来压力
   - **缓解**：添加速率限制（每分钟最多 10 次）
   - **缓解**：添加请求超时（5 秒）

### 权衡
1. **项目层级深度**：只支持一级项目，不支持子项目
   - **优点**：简化设计，降低复杂度
   - **缺点**：无法满足深层级组织结构
   - **决策**：大多数场景一级项目足够，未来可扩展

2. **默认项目行为**：允许 project_id 为 NULL vs 强制关联
   - **决策**：允许 NULL，兼容现有数据
   - **未来**：可添加数据库约束强制关联

## Migration Plan

### 数据库迁移步骤
```sql
-- Step 1: 创建 project 表
CREATE TABLE project (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  code VARCHAR(50) NOT NULL,
  description TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  is_default BOOLEAN DEFAULT FALSE,
  settings JSON,
  tenant_id INT NOT NULL,
  created_at BIGINT,
  updated_at BIGINT,
  FOREIGN KEY (tenant_id) REFERENCES tenant(id) ON DELETE CASCADE,
  INDEX idx_tenant_id (tenant_id),
  UNIQUE KEY uk_tenant_code (tenant_id, code)
);

-- Step 2: 为每个租户创建默认项目
INSERT INTO project (name, code, is_default, tenant_id, created_at, updated_at)
SELECT '默认项目', 'default', TRUE, id, UNIX_TIMESTAMP(), UNIX_TIMESTAMP()
FROM tenant;

-- Step 3: 添加 project_id 字段到相关表
ALTER TABLE alert_rule ADD COLUMN project_id INT NULL;
ALTER TABLE datasource ADD COLUMN project_id INT NULL;
ALTER TABLE notification_channel ADD COLUMN project_id INT NULL;
ALTER TABLE silence_rule ADD COLUMN project_id INT NULL;

-- Step 4: 更新现有数据关联到默认项目
UPDATE alert_rule ar
JOIN project p ON ar.tenant_id = p.tenant_id AND p.is_default = TRUE
SET ar.project_id = p.id;

UPDATE datasource ds
JOIN project p ON ds.tenant_id = p.tenant_id AND p.is_default = TRUE
SET ds.project_id = p.id;

UPDATE notification_channel nc
JOIN project p ON nc.tenant_id = p.tenant_id AND p.is_default = TRUE
SET nc.project_id = p.id;

UPDATE silence_rule sr
JOIN project p ON sr.tenant_id = p.tenant_id AND p.is_default = TRUE
SET sr.project_id = p.id;

-- Step 5: 添加外键约束和索引
ALTER TABLE alert_rule 
  ADD FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE,
  ADD INDEX idx_project_id (project_id);

-- 其他表类似...

-- Step 6: 创建项目-用户关联表
CREATE TABLE project_user (
  project_id INT NOT NULL,
  user_id INT NOT NULL,
  role VARCHAR(50) DEFAULT 'member',
  created_at BIGINT,
  PRIMARY KEY (project_id, user_id),
  FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Step 7: 将所有用户添加到租户的默认项目
INSERT INTO project_user (project_id, user_id, role, created_at)
SELECT p.id, u.id, 'admin', UNIX_TIMESTAMP()
FROM user u
JOIN project p ON u.tenant_id = p.tenant_id AND p.is_default = TRUE;
```

### 回滚计划
如果迁移失败，可以：
1. 删除 project_id 字段
2. 删除 project 和 project_user 表
3. 系统恢复到只使用 tenant_id 的状态

### 部署步骤
1. **备份数据库**
2. **部署新版本代码**（包含迁移脚本）
3. **运行迁移脚本**
4. **验证数据完整性**
5. **重启应用服务**
6. **前端更新**（用户刷新即可）

## Open Questions

1. **项目配额**：是否需要限制每个租户的项目数量？
   - **建议**：初期不限制，后续可添加到租户的 quota_config

2. **项目权限粒度**：是否需要更细粒度的项目内权限控制？
   - **建议**：初期使用简单的 owner/admin/member/viewer 角色
   - **后续**：可扩展为基于资源的权限

3. **跨项目查询**：是否允许某些用户查看多个项目的告警？
   - **建议**：支持，用户可以属于多个项目
   - **实现**：API 接口支持 project_id 参数，不传则返回所有有权限的项目数据

4. **测试接口安全性**：是否需要更严格的限流？
   - **建议**：基于用户 + IP 的限流，每分钟 10 次
   - **实现**：使用 Redis 计数器
