# 数据库重构 - 快速执行指南

## 🎯 适用场景

**方案 A: 保留现有数据 (生产环境)**
- 已有数据需要迁移
- 执行时间: 约 5-10 分钟

**方案 B: 全新安装 (开发/测试)**
- 不需要保留数据
- 执行时间: 约 1 分钟

---

## 方案 A: 迁移现有数据 (推荐生产环境)

### 1️⃣ 准备工作 (2分钟)

```bash
# 安装依赖
pip install aiomysql

# 编辑迁移脚本,修改数据库密码
# 文件: scripts/migrate_to_v2.py
# 修改: password: 'your_password'
```

### 2️⃣ 停止服务 (1分钟)

```bash
# 停止后端 (按 Ctrl+C 或执行以下命令)
Get-Process | Where-Object {$_.ProcessName -eq 'python'} | Stop-Process -Force

# 停止前端 (按 Ctrl+C)
```

### 3️⃣ 执行迁移 (5分钟)

```bash
# 在项目根目录执行
python scripts/migrate_to_v2.py

# 出现确认提示时输入: yes
```

**迁移过程**:
- ✅ 自动导出所有数据
- ✅ 保存备份到 `backups/` 目录
- ✅ 重建数据库 (V2 结构)
- ✅ 恢复数据 (时间自动转换)

### 4️⃣ 验证 (2分钟)

```bash
# 登录数据库检查
mysql -u root -p whatalert

# 检查时间字段类型
SHOW COLUMNS FROM user LIKE '%_at';
# 应该显示: bigint

# 检查数据
SELECT id, username, created_at FROM user;
# 时间戳应该是 10位数字,如: 1700123456

exit
```

### 5️⃣ 启动服务

```bash
# 启动后端
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端 (新终端)
cd web
npm run dev
```

访问 http://localhost:5173 测试登录和功能。

---

## 方案 B: 全新安装 (开发/测试)

### 1️⃣ 停止服务

```bash
Get-Process | Where-Object {$_.ProcessName -eq 'python'} | Stop-Process -Force
```

### 2️⃣ 重建数据库

```bash
# 登录 MySQL
mysql -u root -p

# 删除旧库,创建新库
DROP DATABASE IF EXISTS whatalert;
CREATE DATABASE whatalert CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit

# 导入 V2 脚本
mysql -u root -p whatalert < scripts/init_database_v2.sql
```

### 3️⃣ 启动服务

```bash
# 后端
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 前端 (新终端)
cd web
npm run dev
```

**默认账号**: admin / admin123

---

## ❌ 如果出现问题 - 快速回滚

### 使用自动备份回滚

```bash
# 查看备份文件
ls backups/

# 恢复最新备份 (修改脚本中的数据库密码后执行)
python scripts/restore_from_backup.py backups/backup_YYYYMMDD_HHMMSS.json
```

### 使用手动备份回滚

```bash
# 如果迁移前执行了 mysqldump
mysql -u root -p

DROP DATABASE whatalert;
CREATE DATABASE whatalert CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit

mysql -u root -p whatalert < backup_manual_YYYYMMDD_HHMMSS.sql
```

---

## ✅ 迁移成功检查清单

访问前端并测试:

- [ ] 登录成功
- [ ] 项目列表显示正常
- [ ] 可以切换项目
- [ ] 创建告警规则成功
- [ ] 创建数据源成功
- [ ] 告警历史查询正常
- [ ] 用户管理功能正常

数据库检查:

```sql
-- 所有时间字段应该是 bigint 类型
SHOW COLUMNS FROM tenant LIKE '%_at';
SHOW COLUMNS FROM user LIKE '%_at';
SHOW COLUMNS FROM alert_rule LIKE '%_at';

-- project.settings 不应该为 NULL
SELECT id, name, settings FROM project;
```

---

## 📞 常见问题速查

### Q: 迁移失败 "Duplicate column name 'project_id'"
```bash
# 完全删除数据库重试
mysql -u root -p
DROP DATABASE whatalert;
CREATE DATABASE whatalert CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit

python scripts/migrate_to_v2.py
```

### Q: 迁移后无法登录
```bash
# 清除浏览器缓存和 localStorage
# 使用默认账号: admin / admin123
```

### Q: 时间显示异常
检查前端是否正确处理时间戳:
```javascript
// 秒级时间戳需要 * 1000
new Date(timestamp * 1000)
```

### Q: 找不到迁移脚本
```bash
# 确保在项目根目录
cd E:\python\github\Whatalert

# 检查文件存在
ls scripts/migrate_to_v2.py
ls scripts/init_database_v2.sql
```

---

## 📚 详细文档

更多信息请参阅:
- 完整迁移指南: `docs/DATABASE_MIGRATION_GUIDE.md`
- 数据库重构方案: `docs/DATABASE_REFACTOR_PLAN.md`

---

## 🎉 迁移完成后

记得:
1. ✅ 删除临时清理脚本
2. ✅ 保留备份文件 (至少一周)
3. ✅ 更新团队文档
4. ✅ 通知团队成员
