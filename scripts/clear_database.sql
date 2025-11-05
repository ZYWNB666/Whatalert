-- ============================================================================
-- Whatalert 监控告警系统 - 清空数据库脚本
-- ============================================================================
-- 版本: 1.0.0
-- 描述: 清空所有表数据，保留表结构
-- 
-- ⚠️  警告：此操作不可逆！执行前请确认！
-- 
-- 使用场景：
--   - 清理测试数据
--   - 重置系统到初始状态
--   - 开发环境数据清理
-- 
-- 使用方法：
--   方式1 - 命令行:
--     mysql -u root -p whatalert < clear_database.sql
--   方式2 - MySQL命令行客户端:
--     use whatalert;
--     source /path/to/clear_database.sql;
-- 
-- 注意：
--   1. 清空数据后需要重新运行 init_database.sql 初始化默认用户和权限
--   2. 或者使用 init_db.py 脚本初始化默认数据
-- ============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- 清空审计日志
TRUNCATE TABLE `audit_log`;

-- 清空通知相关
TRUNCATE TABLE `notification_record`;
TRUNCATE TABLE `alert_rule_notification_channels`;
TRUNCATE TABLE `notification_channel`;

-- 清空静默规则
TRUNCATE TABLE `silence_rule`;

-- 清空系统设置
TRUNCATE TABLE `system_settings`;

-- 清空告警相关
TRUNCATE TABLE `alert_event_history`;
TRUNCATE TABLE `alert_event`;
TRUNCATE TABLE `alert_rule`;

-- 清空数据源
TRUNCATE TABLE `datasource`;

-- 清空权限和角色
TRUNCATE TABLE `user_roles`;
TRUNCATE TABLE `role_permissions`;
TRUNCATE TABLE `permission`;
TRUNCATE TABLE `role`;

-- 清空用户和租户
TRUNCATE TABLE `user`;
TRUNCATE TABLE `tenant`;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- 完成
-- ============================================================================

SELECT '所有表数据已清空！' AS message;
SELECT '请运行 init_database.sql 或 init_db.py 重新初始化默认数据' AS info;

