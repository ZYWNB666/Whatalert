-- ============================================================================
-- Whatalert 监控告警系统 - 数据库初始化脚本
-- ============================================================================
-- 版本: 1.0.0
-- 描述: 完整的数据库表结构和初始数据（16张表）
-- 
-- 【首次部署使用方法】
-- 
-- 第一步：创建数据库
--   CREATE DATABASE whatalert CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 
-- 第二步：导入此脚本（三选一）
--   方式1 - 命令行:
--     mysql -u root -p whatalert < init_database.sql
--   方式2 - MySQL命令行客户端:
--     use whatalert;
--     source /path/to/init_database.sql;
--   方式3 - 可视化工具（Navicat/DBeaver等）:
--     打开whatalert数据库，运行SQL文件
-- 
-- 第三步：配置应用程序
--   编辑 .env 文件，设置数据库连接:
--     DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/whatalert
-- 
-- 第四步：启动应用
--   cd alert_system
--   uvicorn app.main:app --host 0.0.0.0 --port 8000
-- 
-- 第五步：登录系统
--   默认管理员账号: admin
--   默认密码: admin123
--   ⚠️ 首次登录后请立即修改密码！
-- 
-- 【数据库说明】
--   - 共 16 张表
--   - 表命名使用 snake_case 规范
--   - 包含完整的外键约束和索引
--   - 已插入必要的初始数据
-- ============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================================
-- 1. 用户权限管理表（6个表）
-- ============================================================================

-- 1.1 租户表
DROP TABLE IF EXISTS `tenant`;
CREATE TABLE `tenant` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(100) NOT NULL COMMENT '租户名称',
  `domain` VARCHAR(100) UNIQUE COMMENT '域名',
  `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否激活',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_tenant_domain` (`domain`),
  INDEX `idx_tenant_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户表';

-- 1.2 用户表
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
  `email` VARCHAR(100) NOT NULL UNIQUE COMMENT '邮箱',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希',
  `full_name` VARCHAR(100) COMMENT '全名',
  `phone` VARCHAR(20) COMMENT '手机号',
  `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否激活',
  `is_superuser` BOOLEAN DEFAULT FALSE COMMENT '是否超级管理员',
  `tenant_id` INT NOT NULL COMMENT '租户ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_user_username` (`username`),
  INDEX `idx_user_email` (`email`),
  INDEX `idx_user_tenant_id` (`tenant_id`),
  FOREIGN KEY (`tenant_id`) REFERENCES `tenant`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 1.3 角色表
DROP TABLE IF EXISTS `role`;
CREATE TABLE `role` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(50) NOT NULL COMMENT '角色名称',
  `code` VARCHAR(50) NOT NULL COMMENT '角色代码',
  `description` VARCHAR(200) COMMENT '描述',
  `tenant_id` INT NOT NULL COMMENT '租户ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_role_code` (`code`),
  INDEX `idx_role_tenant_id` (`tenant_id`),
  FOREIGN KEY (`tenant_id`) REFERENCES `tenant`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色表';

-- 1.4 权限表
DROP TABLE IF EXISTS `permission`;
CREATE TABLE `permission` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(50) NOT NULL COMMENT '权限名称',
  `code` VARCHAR(100) NOT NULL UNIQUE COMMENT '权限代码',
  `resource` VARCHAR(50) NOT NULL COMMENT '资源类型',
  `action` VARCHAR(20) NOT NULL COMMENT '操作类型',
  `description` VARCHAR(200) COMMENT '描述',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_permission_code` (`code`),
  INDEX `idx_permission_resource` (`resource`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='权限表';

-- 1.5 用户角色关联表
DROP TABLE IF EXISTS `user_roles`;
CREATE TABLE `user_roles` (
  `user_id` INT NOT NULL,
  `role_id` INT NOT NULL,
  PRIMARY KEY (`user_id`, `role_id`),
  FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`role_id`) REFERENCES `role`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户角色关联表';

-- 1.6 角色权限关联表
DROP TABLE IF EXISTS `role_permissions`;
CREATE TABLE `role_permissions` (
  `role_id` INT NOT NULL,
  `permission_id` INT NOT NULL,
  PRIMARY KEY (`role_id`, `permission_id`),
  FOREIGN KEY (`role_id`) REFERENCES `role`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`permission_id`) REFERENCES `permission`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色权限关联表';

-- ============================================================================
-- 2. 数据源管理表（1个表）
-- ============================================================================

-- 2.1 数据源表
DROP TABLE IF EXISTS `datasource`;
CREATE TABLE `datasource` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(100) NOT NULL COMMENT '数据源名称',
  `type` VARCHAR(50) NOT NULL COMMENT '类型',
  `url` VARCHAR(500) NOT NULL COMMENT 'URL',
  `description` TEXT COMMENT '描述',
  `auth_config` JSON COMMENT '认证配置',
  `http_config` JSON COMMENT 'HTTP配置',
  `extra_labels` JSON COMMENT '额外标签',
  `is_enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
  `is_default` BOOLEAN DEFAULT FALSE COMMENT '是否默认',
  `tenant_id` INT NOT NULL COMMENT '租户ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_datasource_tenant_id` (`tenant_id`),
  INDEX `idx_datasource_type` (`type`),
  FOREIGN KEY (`tenant_id`) REFERENCES `tenant`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据源表';

-- ============================================================================
-- 3. 告警规则和事件表（4个表）
-- ============================================================================

-- 3.1 告警规则表
DROP TABLE IF EXISTS `alert_rule`;
CREATE TABLE `alert_rule` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(200) NOT NULL COMMENT '规则名称',
  `expr` TEXT NOT NULL COMMENT 'PromQL表达式',
  `severity` VARCHAR(20) NOT NULL DEFAULT 'warning' COMMENT '严重程度',
  `for_duration` INT DEFAULT 60 COMMENT '持续时间(秒)',
  `eval_interval` INT DEFAULT 60 COMMENT '评估间隔(秒)',
  `labels` JSON COMMENT '标签',
  `annotations` JSON COMMENT '注释',
  `route_config` JSON COMMENT '路由配置',
  `description` TEXT COMMENT '描述',
  `is_enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
  `datasource_id` INT NOT NULL COMMENT '数据源ID',
  `tenant_id` INT NOT NULL COMMENT '租户ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_alert_rule_tenant_id` (`tenant_id`),
  INDEX `idx_alert_rule_datasource_id` (`datasource_id`),
  INDEX `idx_alert_rule_is_enabled` (`is_enabled`),
  FOREIGN KEY (`tenant_id`) REFERENCES `tenant`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`datasource_id`) REFERENCES `datasource`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='告警规则表';

-- 3.2 告警事件表（当前活跃告警）
DROP TABLE IF EXISTS `alert_event`;
CREATE TABLE `alert_event` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `fingerprint` VARCHAR(100) NOT NULL UNIQUE COMMENT '指纹',
  `rule_id` INT NOT NULL COMMENT '规则ID',
  `rule_name` VARCHAR(200) NOT NULL COMMENT '规则名称',
  `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态',
  `severity` VARCHAR(20) NOT NULL COMMENT '严重程度',
  `labels` JSON COMMENT '标签',
  `annotations` JSON COMMENT '注释',
  `expr` TEXT COMMENT '查询表达式',
  `value` FLOAT COMMENT '值',
  `started_at` BIGINT NOT NULL COMMENT '开始时间戳',
  `last_eval_at` BIGINT NOT NULL COMMENT '最后评估时间戳',
  `last_sent_at` BIGINT DEFAULT 0 COMMENT '最后发送时间戳',
  `tenant_id` INT NOT NULL COMMENT '租户ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_alert_event_rule_id` (`rule_id`),
  INDEX `idx_alert_event_fingerprint` (`fingerprint`),
  INDEX `idx_alert_event_status` (`status`),
  INDEX `idx_alert_event_tenant_id` (`tenant_id`),
  INDEX `idx_alert_event_started_at` (`started_at`),
  FOREIGN KEY (`tenant_id`) REFERENCES `tenant`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`rule_id`) REFERENCES `alert_rule`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='告警事件表';

-- 3.3 历史告警事件表
DROP TABLE IF EXISTS `alert_event_history`;
CREATE TABLE `alert_event_history` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `fingerprint` VARCHAR(100) NOT NULL COMMENT '指纹',
  `rule_id` INT COMMENT '规则ID',
  `rule_name` VARCHAR(200) COMMENT '规则名称',
  `status` VARCHAR(20) COMMENT '状态',
  `severity` VARCHAR(20) COMMENT '严重程度',
  `labels` JSON COMMENT '标签',
  `annotations` JSON COMMENT '注释',
  `expr` TEXT COMMENT '查询表达式',
  `value` FLOAT COMMENT '值',
  `started_at` BIGINT COMMENT '开始时间戳',
  `resolved_at` BIGINT COMMENT '恢复时间戳',
  `duration` BIGINT COMMENT '持续时间(秒)',
  `tenant_id` INT NOT NULL COMMENT '租户ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_alert_event_history_fingerprint` (`fingerprint`),
  INDEX `idx_alert_event_history_tenant_id` (`tenant_id`),
  INDEX `idx_alert_event_history_started_at` (`started_at`),
  FOREIGN KEY (`tenant_id`) REFERENCES `tenant`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='历史告警事件';

-- 3.4 告警规则通知渠道关联表
DROP TABLE IF EXISTS `alert_rule_notification_channels`;
CREATE TABLE `alert_rule_notification_channels` (
  `alert_rule_id` INT NOT NULL,
  `notification_channel_id` INT NOT NULL,
  PRIMARY KEY (`alert_rule_id`, `notification_channel_id`),
  FOREIGN KEY (`alert_rule_id`) REFERENCES `alert_rule`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`notification_channel_id`) REFERENCES `notification_channel`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='告警规则通知渠道关联表';

-- ============================================================================
-- 4. 通知渠道表（2个表）
-- ============================================================================

-- 4.1 通知渠道表
DROP TABLE IF EXISTS `notification_channel`;
CREATE TABLE `notification_channel` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(100) NOT NULL COMMENT '渠道名称',
  `type` VARCHAR(50) NOT NULL COMMENT '类型',
  `config` JSON NOT NULL COMMENT '配置',
  `filter_config` JSON COMMENT '过滤配置',
  `description` TEXT COMMENT '描述',
  `is_enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
  `is_default` BOOLEAN DEFAULT FALSE COMMENT '是否默认',
  `tenant_id` INT NOT NULL COMMENT '租户ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_notification_channel_tenant_id` (`tenant_id`),
  INDEX `idx_notification_channel_type` (`type`),
  FOREIGN KEY (`tenant_id`) REFERENCES `tenant`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知渠道表';

-- 4.2 通知记录表
DROP TABLE IF EXISTS `notification_record`;
CREATE TABLE `notification_record` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `channel_id` INT COMMENT '渠道ID',
  `channel_name` VARCHAR(100) COMMENT '渠道名称',
  `channel_type` VARCHAR(50) COMMENT '渠道类型',
  `alert_fingerprint` VARCHAR(100) COMMENT '告警指纹',
  `alert_name` VARCHAR(200) COMMENT '告警名称',
  `severity` VARCHAR(20) COMMENT '严重程度',
  `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
  `error_message` TEXT COMMENT '错误信息',
  `content` JSON COMMENT '发送内容',
  `sent_at` BIGINT COMMENT '发送时间戳',
  `tenant_id` INT NOT NULL COMMENT '租户ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_notification_record_channel_id` (`channel_id`),
  INDEX `idx_notification_record_alert_fingerprint` (`alert_fingerprint`),
  INDEX `idx_notification_record_tenant_id` (`tenant_id`),
  FOREIGN KEY (`channel_id`) REFERENCES `notification_channel`(`id`) ON DELETE SET NULL,
  FOREIGN KEY (`tenant_id`) REFERENCES `tenant`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知记录';

-- ============================================================================
-- 5. 辅助功能表（3个表）
-- ============================================================================

-- 5.1 静默规则表
DROP TABLE IF EXISTS `silence_rule`;
CREATE TABLE `silence_rule` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(200) NOT NULL COMMENT '规则名称',
  `description` TEXT COMMENT '描述',
  `matchers` JSON NOT NULL COMMENT '匹配器',
  `starts_at` BIGINT NOT NULL COMMENT '开始时间戳',
  `ends_at` BIGINT NOT NULL COMMENT '结束时间戳',
  `is_enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
  `created_by` VARCHAR(100) COMMENT '创建者',
  `comment` TEXT COMMENT '备注',
  `tenant_id` INT NOT NULL COMMENT '租户ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_silence_rule_tenant_id` (`tenant_id`),
  INDEX `idx_silence_rule_is_enabled` (`is_enabled`),
  INDEX `idx_silence_rule_time` (`starts_at`, `ends_at`),
  FOREIGN KEY (`tenant_id`) REFERENCES `tenant`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='静默规则';

-- 5.2 系统设置表
DROP TABLE IF EXISTS `system_settings`;
CREATE TABLE `system_settings` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `key` VARCHAR(100) NOT NULL UNIQUE COMMENT '设置键',
  `value` JSON NOT NULL COMMENT '设置值',
  `description` VARCHAR(500) COMMENT '描述',
  `category` VARCHAR(50) COMMENT '分类',
  `tenant_id` INT COMMENT '租户ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_system_settings_key` (`key`),
  INDEX `idx_system_settings_category` (`category`),
  INDEX `idx_system_settings_tenant_id` (`tenant_id`),
  FOREIGN KEY (`tenant_id`) REFERENCES `tenant`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统设置';

-- 5.3 审计日志表
DROP TABLE IF EXISTS `audit_log`;
CREATE TABLE `audit_log` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `action` VARCHAR(50) NOT NULL COMMENT '操作类型',
  `resource_type` VARCHAR(50) NOT NULL COMMENT '资源类型',
  `resource_id` INT COMMENT '资源ID',
  `resource_name` VARCHAR(200) COMMENT '资源名称',
  `user_id` INT COMMENT '用户ID',
  `username` VARCHAR(50) COMMENT '用户名',
  `ip_address` VARCHAR(50) COMMENT 'IP地址',
  `user_agent` VARCHAR(500) COMMENT 'User Agent',
  `request_method` VARCHAR(10) COMMENT '请求方法',
  `request_path` VARCHAR(500) COMMENT '请求路径',
  `changes` JSON COMMENT '变更内容',
  `status` VARCHAR(20) DEFAULT 'success' COMMENT '状态',
  `error_message` TEXT COMMENT '错误信息',
  `timestamp` BIGINT NOT NULL COMMENT '时间戳',
  `tenant_id` INT COMMENT '租户ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  INDEX `idx_audit_log_user_id` (`user_id`),
  INDEX `idx_audit_log_resource_type` (`resource_type`),
  INDEX `idx_audit_log_action` (`action`),
  INDEX `idx_audit_log_timestamp` (`timestamp`),
  INDEX `idx_audit_log_tenant_id` (`tenant_id`),
  FOREIGN KEY (`tenant_id`) REFERENCES `tenant`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志';

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- 6. 插入初始数据
-- ============================================================================

-- 6.1 插入默认租户
INSERT INTO `tenant` (`name`, `domain`, `is_active`) VALUES
('默认租户', 'default', TRUE);

SET @tenant_id = LAST_INSERT_ID();

-- 6.2 插入权限数据
INSERT INTO `permission` (`name`, `code`, `resource`, `action`, `description`) VALUES
-- 告警规则权限
('查看告警规则', 'alert_rule.read', 'alert_rule', 'read', '可以查看告警规则列表和详情'),
('创建告警规则', 'alert_rule.create', 'alert_rule', 'create', '可以创建新的告警规则'),
('更新告警规则', 'alert_rule.update', 'alert_rule', 'update', '可以修改现有告警规则'),
('删除告警规则', 'alert_rule.delete', 'alert_rule', 'delete', '可以删除告警规则'),

-- 数据源权限
('查看数据源', 'datasource.read', 'datasource', 'read', '可以查看数据源列表和详情'),
('创建数据源', 'datasource.create', 'datasource', 'create', '可以创建新的数据源'),
('更新数据源', 'datasource.update', 'datasource', 'update', '可以修改现有数据源'),
('删除数据源', 'datasource.delete', 'datasource', 'delete', '可以删除数据源'),

-- 通知渠道权限
('查看通知渠道', 'notification.read', 'notification', 'read', '可以查看通知渠道列表和详情'),
('创建通知渠道', 'notification.create', 'notification', 'create', '可以创建新的通知渠道'),
('更新通知渠道', 'notification.update', 'notification', 'update', '可以修改现有通知渠道'),
('删除通知渠道', 'notification.delete', 'notification', 'delete', '可以删除通知渠道'),

-- 用户管理权限
('查看用户', 'user.read', 'user', 'read', '可以查看用户列表和详情'),
('创建用户', 'user.create', 'user', 'create', '可以创建新用户'),
('更新用户', 'user.update', 'user', 'update', '可以修改用户信息'),
('删除用户', 'user.delete', 'user', 'delete', '可以删除用户'),

-- 系统设置权限
('查看系统设置', 'settings.read', 'settings', 'read', '可以查看系统设置'),
('修改系统设置', 'settings.update', 'settings', 'update', '可以修改系统设置'),

-- 审计日志权限
('查看审计日志', 'audit.read', 'audit', 'read', '可以查看审计日志');

-- 6.3 插入角色数据
INSERT INTO `role` (`name`, `code`, `description`, `tenant_id`) VALUES
('管理员', 'admin', '系统管理员，拥有所有权限', @tenant_id);
SET @admin_role_id = LAST_INSERT_ID();

INSERT INTO `role` (`name`, `code`, `description`, `tenant_id`) VALUES
('运维人员', 'operator', '运维人员，可以管理告警和通知', @tenant_id);
SET @operator_role_id = LAST_INSERT_ID();

INSERT INTO `role` (`name`, `code`, `description`, `tenant_id`) VALUES
('查看者', 'viewer', '只读用户，只能查看信息', @tenant_id);
SET @viewer_role_id = LAST_INSERT_ID();

-- 6.4 分配权限给角色
-- 管理员拥有所有权限
INSERT INTO `role_permissions` (`role_id`, `permission_id`)
SELECT @admin_role_id, `id` FROM `permission`;

-- 运维人员权限
INSERT INTO `role_permissions` (`role_id`, `permission_id`)
SELECT @operator_role_id, `id` FROM `permission`
WHERE `code` IN (
    'alert_rule.read', 'alert_rule.create', 'alert_rule.update', 'alert_rule.delete',
    'datasource.read',
    'notification.read', 'notification.create', 'notification.update', 'notification.delete',
    'audit.read'
);

-- 查看者权限
INSERT INTO `role_permissions` (`role_id`, `permission_id`)
SELECT @viewer_role_id, `id` FROM `permission`
WHERE `code` IN (
    'alert_rule.read',
    'datasource.read',
    'notification.read'
);

-- 6.5 创建默认管理员用户
-- 密码: admin123 (BCrypt加密后的哈希)
INSERT INTO `user` (`username`, `email`, `password_hash`, `full_name`, `is_active`, `is_superuser`, `tenant_id`) VALUES
('admin', 'admin@example.com', '$2b$12$cpLHuqRo2MqsW/CNjTLKPOJkG8ofG6mD3fUCMaOMA05zf3ap8rnUy', '系统管理员', TRUE, TRUE, @tenant_id);

SET @admin_user_id = LAST_INSERT_ID();

-- 6.6 分配角色给管理员用户
INSERT INTO `user_roles` (`user_id`, `role_id`) VALUES
(@admin_user_id, @admin_role_id);

-- ============================================================================
-- 完成
-- ============================================================================

SELECT '数据库初始化完成！' AS message;
SELECT CONCAT('默认管理员账号: admin') AS info;
SELECT CONCAT('默认管理员密码: admin123') AS info;
SELECT CONCAT('租户ID: ', @tenant_id) AS info;
SELECT CONCAT('管理员用户ID: ', @admin_user_id) AS info;
SELECT '请及时修改默认密码！' AS warning;
