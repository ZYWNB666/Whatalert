# 数据库重构迁移指南

## 📋 概述

本文档指导你完成从 V1 (DATETIME) 到 V2 (Unix 时间戳) 的数据库迁移。

### 主要变更

- **时间字段统一**: 所有 `created_at` 和 `updated_at` 从 `DATETIME` 改为 `BIGINT` (Unix 时间戳)
- **项目隔离完善**: 所有资源表添加 `project_id` (非空)
- **JSON 字段默认值**: `project.settings` 设置默认值 `{}`
- **索引优化**: 为时间戳字段添加索引

## ⚠️ 迁移前准备

### 1. 安装依赖

```bash
pip install aiomysql
```

### 2. 停止应用程序

```bash
# 停止后端服务
# 方式1: 如果使用 Ctrl+C 可以直接停止
# 方式2: 查找并停止进程
Get-Process | Where-Object {$_.ProcessName -eq 'python' -and $_.CommandLine -like '*uvicorn*'} | Stop-Process -Force

# 停止前端服务 (如果运行)
# 在前端目录按 Ctrl+C
```

### 3. 备份当前数据库

```bash
# 使用 mysqldump 备份
mysqldump -u root -p whatalert > backup_manual_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql
```

### 4. 修改迁移脚本配置

编辑 `scripts/migrate_to_v2.py`:

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'your_password',  # ⚠️ 修改为你的数据库密码
    'db': 'whatalert',
    'charset': 'utf8mb4'
}
```

## 🚀 执行迁移

### 方法一: 自动迁移 (推荐)

```bash
# 进入项目根目录
cd E:\python\github\Whatalert

# 执行迁移脚本
python scripts/migrate_to_v2.py
```

迁移过程:
1. ✅ 导出所有现有数据
2. ✅ 保存 JSON 备份到 `backups/backup_YYYYMMDD_HHMMSS.json`
3. ✅ 删除并重建数据库
4. ✅ 执行 V2 初始化脚本
5. ✅ 恢复数据 (时间自动转换为 Unix 时间戳)

### 方法二: 手动迁移 (全新安装)

如果不需要保留现有数据:

```bash
# 1. 登录 MySQL
mysql -u root -p

# 2. 删除旧数据库
DROP DATABASE IF EXISTS whatalert;

# 3. 创建新数据库
CREATE DATABASE whatalert CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 4. 退出 MySQL
exit

# 5. 导入 V2 脚本
mysql -u root -p whatalert < scripts/init_database_v2.sql
```

默认管理员账号:
- 用户名: `admin`
- 密码: `admin123`

## ✅ 验证迁移

### 1. 检查表结构

```sql
-- 登录 MySQL
mysql -u root -p whatalert

-- 检查时间字段类型
SHOW COLUMNS FROM tenant LIKE '%_at';
SHOW COLUMNS FROM user LIKE '%_at';
SHOW COLUMNS FROM alert_event LIKE '%_at';

-- 应该看到: Type = bigint
```

### 2. 检查数据

```sql
-- 检查租户数据
SELECT id, name, created_at, updated_at FROM tenant;

-- 检查用户数据
SELECT id, username, created_at, updated_at FROM user;

-- 检查项目数据
SELECT id, name, settings, created_at FROM project;

-- 时间戳应该是类似 1700000000 这样的数字
```

### 3. 启动应用测试

```bash
# 启动后端
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 在另一个终端启动前端
cd web
npm run dev
```

访问 http://localhost:5173 测试:
- ✅ 登录功能
- ✅ 项目切换
- ✅ 创建告警规则
- ✅ 创建数据源
- ✅ 查看告警历史

## 🔄 回滚方案

### 方案一: 使用自动备份恢复

迁移脚本会在 `backups/` 目录保存 JSON 备份。如果需要回滚:

```bash
# 使用提供的恢复脚本
python scripts/restore_from_backup.py backups/backup_20231117_120000.json
```

### 方案二: 使用手动备份恢复

如果在迁移前执行了 mysqldump:

```bash
# 1. 登录 MySQL
mysql -u root -p

# 2. 删除新数据库
DROP DATABASE whatalert;

# 3. 创建数据库
CREATE DATABASE whatalert CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 4. 退出
exit

# 5. 恢复备份
mysql -u root -p whatalert < backup_manual_20231117_120000.sql
```

### 方案三: 重新使用 V1 脚本

如果没有备份但要回到 V1:

```bash
# 1. 使用 V1 脚本 (重命名当前的 init_database.sql)
mysql -u root -p

DROP DATABASE whatalert;
CREATE DATABASE whatalert CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit

mysql -u root -p whatalert < scripts/init_database.sql

# 2. 恢复 base.py 的 DateTime 类型
# 编辑 app/models/base.py 将 Integer 改回 DateTime
```

## 📊 迁移检查清单

在迁移完成后，逐一检查:

- [ ] 数据库所有表的 `created_at` 和 `updated_at` 字段类型为 `BIGINT`
- [ ] 所有现有数据已成功迁移
- [ ] 时间戳值合理 (1700000000 左右)
- [ ] `project.settings` 不为 NULL
- [ ] 所有资源表有 `project_id` 字段
- [ ] 应用程序能正常启动
- [ ] 用户能正常登录
- [ ] 项目切换功能正常
- [ ] 可以创建新的告警规则、数据源
- [ ] 告警历史查询正常
- [ ] 审计日志记录正常

## ⚡ 常见问题

### Q1: 迁移脚本报错 "Duplicate column name"

**原因**: 数据库已经是 V2 版本或部分迁移。

**解决**: 
```bash
# 完全删除并重建
mysql -u root -p
DROP DATABASE whatalert;
CREATE DATABASE whatalert CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit

# 然后重新执行迁移
```

### Q2: 时间显示不正确

**原因**: 前端未正确处理 Unix 时间戳。

**检查**: 
- 后端返回的是秒级时间戳 (10位)
- 前端 `new Date(timestamp * 1000)` 乘以 1000 转换为毫秒

### Q3: project.settings 为 NULL

**原因**: 旧数据未设置默认值。

**修复**:
```sql
UPDATE project SET settings = '{}' WHERE settings IS NULL;
```

### Q4: 迁移后无法登录

**可能原因**:
1. 用户数据未正确迁移
2. JWT token 需要重新生成

**解决**:
- 清除浏览器 localStorage
- 使用默认管理员账号登录: admin / admin123
- 如果默认账号不存在，重新执行 V2 初始化脚本

## 📞 技术支持

如果遇到问题:

1. 查看迁移日志输出
2. 检查 `backups/` 目录的备份文件
3. 查看应用程序日志 (`logs/`)
4. 使用手动备份回滚

## 📝 迁移后维护

### 新增表或字段

以后如需新增表，确保:
- 时间字段使用 `BIGINT` 类型
- 添加时间索引: `INDEX idx_xxx_created_at (created_at)`
- 设置注释: `COMMENT '创建时间戳'`

### Model 定义

继承 `BaseModel` 即可自动获得 `created_at` 和 `updated_at`:

```python
from app.models.base import BaseModel

class MyModel(BaseModel):
    # BaseModel 自动提供:
    # - id: Integer (主键)
    # - created_at: Integer (Unix 时间戳)
    # - updated_at: Integer (Unix 时间戳)
    pass
```

### 时间处理

在代码中使用:

```python
import time

# 获取当前时间戳
current_timestamp = int(time.time())

# 格式化显示
from datetime import datetime
dt = datetime.fromtimestamp(current_timestamp)
formatted = dt.strftime('%Y-%m-%d %H:%M:%S')
```

## 🎉 完成

恭喜!数据库已成功迁移到 V2 版本,时间戳类型统一,项目隔离完善。

记得删除临时的迁移脚本和清理工具。
