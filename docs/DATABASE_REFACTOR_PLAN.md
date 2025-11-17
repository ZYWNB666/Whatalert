# 数据库重构方案

## 当前问题分析

1. **时间戳类型混乱**: BaseModel 使用 Integer(Unix时间戳),但 SQL 脚本使用 DATETIME
2. **created_at/updated_at 不一致**: 部分表使用 DATETIME,部分应该用 BIGINT
3. **项目隔离不彻底**: 很多 API 还没有实现项目级过滤

## 重构方案

### 方案 A: 统一使用 Unix 时间戳 (推荐)

**优点**:
- 跨时区友好
- 存储空间小(INT/BIGINT)
- 计算方便
- Python 代码已使用此方案

**缺点**:
- 可读性较差(需要转换)

### 方案 B: 统一使用 DATETIME

**优点**:
- 可读性好
- 数据库自带时区处理

**缺点**:
- 跨时区复杂
- Python 代码需要大改

## 推荐方案: 方案 A (统一 Unix 时间戳)

### 核心改动

1. **所有表的时间字段改为 BIGINT**
   ```sql
   `created_at` BIGINT NOT NULL DEFAULT 0 COMMENT '创建时间戳',
   `updated_at` BIGINT NOT NULL DEFAULT 0 COMMENT '更新时间戳',
   ```

2. **BaseModel 保持当前实现**
   ```python
   created_at = Column(Integer, default=lambda: int(time.time()), nullable=False)
   updated_at = Column(Integer, default=lambda: int(time.time()), onupdate=lambda: int(time.time()), nullable=False)
   ```

3. **初始数据使用 Unix 时间戳**
   ```sql
   INSERT INTO tenant (name, domain, is_active, created_at, updated_at) 
   VALUES ('默认租户', 'default.local', TRUE, UNIX_TIMESTAMP(), UNIX_TIMESTAMP());
   ```

### 重构步骤

1. **备份现有数据**
2. **生成新的 init_database_v2.sql**
3. **创建数据迁移脚本**
4. **测试验证**
5. **切换到新库**

## 实施计划

是否需要我执行以下操作:

1. ✅ 生成新的 init_database_v2.sql (统一使用 BIGINT 时间戳)
2. ✅ 创建数据迁移脚本 (从当前库迁移到新库)
3. ✅ 更新所有 Model 确保一致性
4. ✅ 提供完整的迁移指南

请确认是否继续?
