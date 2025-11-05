# Redis 集成说明

## 概述

告警系统现已完全集成 Redis，支持分布式部署、分布式锁和多租户会话管理。

## 功能特性

### 1. 分布式告警分组

- **Redis 分组器** (`RedisAlertGrouper`)：使用 Redis 存储告警分组，支持多实例部署
- **自动降级**：当 Redis 不可用时，自动切换到内存分组器
- **跨实例共享**：多个告警服务实例可以共享同一个分组状态

### 2. 分布式锁

- **防止重复发送**：通过分布式锁确保同一告警不会被多个实例重复发送
- **原子操作**：使用 Lua 脚本保证锁的获取和释放的原子性
- **自动过期**：锁自动过期，防止死锁

### 3. 会话管理

- **多租户支持**：每个租户的会话独立存储
- **分布式会话**：支持多实例共享用户会话
- **自动续期**：会话访问时自动续期

## 配置

### config.yaml

```yaml
# Redis 配置
redis:
  host: "redis.mysql.netwebs.top"
  port: 7891
  password: "zhangyouwei@123"
  db: 3

# 日志配置
logging:
  level: "INFO"  # 可选: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 架构设计

### 核心组件

1. **RedisClient** (`app/db/redis_client.py`)
   - Redis 连接池管理
   - 单例模式，全局共享连接
   - 自动重连机制

2. **DistributedLock** (`app/core/distributed_lock.py`)
   - 基于 Redis 的分布式锁
   - 支持阻塞和非阻塞模式
   - 自动延长锁时间

3. **SessionManager** (`app/core/session_manager.py`)
   - 会话 CRUD 操作
   - 租户隔离
   - 会话统计

4. **RedisAlertGrouper** (`app/services/redis_alert_grouper.py`)
   - 分布式告警分组
   - 自动过期清理
   - 支持 firing 和 recovery 两种分组

5. **AlertManager** 集成
   - 自动选择 Redis 或内存分组器
   - 分布式锁保护告警发送
   - 兼容现有 API

## 使用示例

### 1. 使用分布式锁

```python
from app.db.redis_client import get_redis
from app.core.distributed_lock import DistributedLock

redis_client = await get_redis()
lock = DistributedLock(redis_client, "my_lock", timeout=30)

# 方式 1：异步上下文管理器
async with lock:
    # 执行需要锁保护的操作
    pass

# 方式 2：手动获取和释放
if await lock.acquire(blocking=True, timeout=10):
    try:
        # 执行操作
        pass
    finally:
        await lock.release()
```

### 2. 使用会话管理

```python
from app.db.redis_client import get_redis
from app.core.session_manager import SessionManager

redis_client = await get_redis()
session_manager = SessionManager(redis_client)

# 创建会话
await session_manager.create_session(
    session_id="user_token_123",
    user_id=1,
    tenant_id=1,
    username="admin",
    additional_data={"role": "admin"}
)

# 获取会话
session_data = await session_manager.get_session("user_token_123")

# 删除会话
await session_manager.delete_session("user_token_123")
```

### 3. 告警分组（自动）

告警管理器会自动使用 Redis 分组器（如果 Redis 可用）：

```python
# 在 AlertManager 中自动选择合适的分组器
alert_manager = AlertManager(db, use_redis=True)

# 发送告警时自动使用分布式锁
await alert_manager.send_alert(alert, rule)
```

## 分布式部署

### 部署架构

```
                    ┌─────────────┐
                    │   Redis     │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────┴──────┐ ┌─────┴──────┐ ┌─────┴──────┐
    │  Instance 1 │ │ Instance 2 │ │ Instance 3 │
    │  (Node 1)   │ │  (Node 2)  │ │  (Node 3)  │
    └─────────────┘ └────────────┘ └────────────┘
```

### 多实例部署步骤

1. **确保 Redis 可访问**
   ```bash
   # 测试 Redis 连接
   redis-cli -h redis.mysql.netwebs.top -p 7891 -a zhangyouwei@123 ping
   ```

2. **在每个节点启动服务**
   ```bash
   # Node 1
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   
   # Node 2
   uvicorn app.main:app --host 0.0.0.0 --port 8001
   
   # Node 3
   uvicorn app.main:app --host 0.0.0.0 --port 8002
   ```

3. **配置负载均衡**
   ```nginx
   upstream alert_backend {
       server node1:8000;
       server node2:8001;
       server node3:8002;
   }
   ```

## 监控指标

### Redis 键命名规范

- 告警分组：`alert:group:firing:{group_key}` 或 `alert:group:recovery:{group_key}`
- 分布式锁：`lock:alert:{fingerprint}` 或 `lock:group:{group_key}`
- 会话：`session:{session_id}`

### 监控命令

```bash
# 查看所有告警分组
redis-cli KEYS "alert:group:*"

# 查看所有锁
redis-cli KEYS "lock:*"

# 查看所有会话
redis-cli KEYS "session:*"

# 查看分组统计
redis-cli --scan --pattern "alert:group:*" | wc -l
```

## 故障处理

### Redis 不可用

系统会自动降级到内存分组器，不影响核心功能：

```
⚠️  Redis 连接失败，将使用内存分组器: Connection refused
```

### 锁超时

分布式锁会自动过期（默认 60 秒），防止死锁。

### 会话丢失

会话存储在 Redis 中，Redis 重启会导致所有会话丢失，用户需要重新登录。

## 性能优化

1. **连接池**：使用连接池复用连接，减少连接开销
2. **Pipeline**：批量操作可以使用 pipeline 减少网络往返
3. **过期时间**：合理设置过期时间，避免内存泄漏
4. **索引优化**：使用 scan 而非 keys 避免阻塞

## 未来改进

- [ ] 使用 Redis Stream 实现告警事件流
- [ ] 使用 Redis Pub/Sub 实现实时通知
- [ ] 使用 Redis 缓存 Prometheus 查询结果
- [ ] 使用 Redis Sorted Set 实现告警优先级队列

