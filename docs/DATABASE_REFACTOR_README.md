# 数据库重构 V2 - 文档索引

## 📚 快速导航

### 🚀 立即开始
- **[快速执行指南](./MIGRATION_QUICKSTART.md)** ⭐ 推荐首先阅读
  - 5 分钟了解两种迁移方案
  - 快速回滚方法
  - 常见问题速查

### 📖 详细文档
- **[完整迁移指南](./DATABASE_MIGRATION_GUIDE.md)**
  - 迁移前准备
  - 详细步骤说明
  - 验证和测试
  - 三种回滚方案
  - 问题排查
  - 迁移后维护

- **[重构方案说明](./DATABASE_REFACTOR_PLAN.md)**
  - 问题分析
  - 两种方案对比
  - 最终选择的方案
  - 影响范围评估

- **[完成报告](./DATABASE_REFACTOR_SUMMARY.md)**
  - 交付物清单
  - 数据库对比
  - 验证清单
  - 优势分析

---

## 🎯 我应该读哪个文档?

### 如果你想立即执行迁移
👉 阅读 **[快速执行指南](./MIGRATION_QUICKSTART.md)**

### 如果你想了解完整流程
👉 阅读 **[完整迁移指南](./DATABASE_MIGRATION_GUIDE.md)**

### 如果你想了解重构原因和方案
👉 阅读 **[重构方案说明](./DATABASE_REFACTOR_PLAN.md)**

### 如果你想了解交付内容
👉 阅读 **[完成报告](./DATABASE_REFACTOR_SUMMARY.md)**

---

## 🛠️ 工具脚本

### 数据库脚本
- `scripts/init_database_v2.sql` - V2 数据库初始化脚本

### 迁移工具
- `scripts/migrate_to_v2.py` - 自动迁移工具 (保留数据)
- `scripts/restore_from_backup.py` - 备份恢复工具

### 使用方法
```bash
# 自动迁移 (保留数据)
python scripts/migrate_to_v2.py

# 从备份恢复
python scripts/restore_from_backup.py backups/backup_YYYYMMDD_HHMMSS.json
```

---

## ⚡ 核心变更

### 时间字段统一
```
V1: DATETIME                  V2: BIGINT (Unix 时间戳)
-----------------------------------------------------
created_at DATETIME     →     created_at BIGINT
updated_at DATETIME     →     updated_at BIGINT

示例值:
'2023-11-17 12:30:00'   →     1700201400
```

### 项目隔离完善
- 所有资源表添加 `project_id NOT NULL`
- 添加外键约束和级联删除
- `project.settings` 设置默认值 `{}`

---

## ✅ 迁移前检查清单

- [ ] 已阅读快速执行指南
- [ ] 已安装 `aiomysql`: `pip install aiomysql`
- [ ] 已修改迁移脚本中的数据库密码
- [ ] 已停止应用程序服务
- [ ] 已手动备份数据库 (可选但推荐)

---

## 🎉 迁移方式选择

### 方案 A: 保留数据迁移
**适用**: 生产环境,需要保留所有数据

**时间**: 约 5-10 分钟

**步骤**:
```bash
python scripts/migrate_to_v2.py
```

### 方案 B: 全新安装
**适用**: 开发/测试环境,不需要保留数据

**时间**: 约 1 分钟

**步骤**:
```bash
mysql -u root -p
DROP DATABASE whatalert;
CREATE DATABASE whatalert CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit

mysql -u root -p whatalert < scripts/init_database_v2.sql
```

---

## 📞 需要帮助?

### 常见问题
查看 [快速执行指南 - 常见问题](./MIGRATION_QUICKSTART.md#-%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98%E9%80%9F%E6%9F%A5)

### 详细问题排查
查看 [完整迁移指南 - 常见问题](./DATABASE_MIGRATION_GUIDE.md#-%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98)

---

## 📝 相关文档

- [项目隔离计划](./PROJECT_ISOLATION_PLAN.md)
- [项目隔离状态](./PROJECT_ISOLATION_STATUS.md)
- [架构文档](./ARCHITECTURE.md)
- [权限系统](./PERMISSIONS.md)
