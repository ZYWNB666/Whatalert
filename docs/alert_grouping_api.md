# 告警分组显示 API 文档

## 概述

新增了两个分组API，用于按规则名称折叠显示告警，每页默认显示10个分组。

## API 接口

### 1. 当前告警分组查询

**接口**: `GET /api/v1/alert-rules/events/current/grouped`

**参数**:
- `page`: 页码（默认: 1）
- `page_size`: 每页分组数（默认: 10，最大: 100）

**响应示例**:
```json
{
  "total": 25,
  "page": 1,
  "page_size": 10,
  "total_pages": 3,
  "groups": [
    {
      "rule_name": "DiskSpaceUsage97",
      "rule_id": 1,
      "count": 5,
      "severity": "critical",
      "status": "firing",
      "latest_started_at": 1762334258,
      "alerts": [
        {
          "id": 1,
          "fingerprint": "f15f385f94bd769560fdfc5cb9f0693c",
          "rule_name": "DiskSpaceUsage97",
          "rule_id": 1,
          "status": "firing",
          "severity": "critical",
          "started_at": 1762334258,
          "last_eval_at": 1762334258,
          "last_sent_at": 0,
          "value": 73.82,
          "labels": {
            "alert_group": "aigc",
            "instance": "10.197.74.193:6101",
            "labrador_project": "AIGC",
            "nodename": "ff-hadoop340"
          },
          "annotations": {},
          "expr": "max by(instance, alert_group, hostname, labrador_project) (...)"
        }
        // ... 更多告警
      ]
    }
    // ... 更多分组
  ]
}
```

**字段说明**:
- `total`: 总分组数
- `page`: 当前页码
- `page_size`: 每页分组数
- `total_pages`: 总页数
- `groups`: 分组列表
  - `rule_name`: 规则名称（分组依据）
  - `rule_id`: 规则ID
  - `count`: 该规则下的告警数量
  - `severity`: 最新告警的等级
  - `status`: 最新告警的状态
  - `latest_started_at`: 最新触发时间
  - `alerts`: 该分组下的所有告警详情

### 2. 历史告警分组查询

**接口**: `GET /api/v1/alert-rules/events/history/grouped`

**参数**:
- `page`: 页码（默认: 1）
- `page_size`: 每页分组数（默认: 10，最大: 100）

**响应示例**:
```json
{
  "total": 15,
  "page": 1,
  "page_size": 10,
  "total_pages": 2,
  "groups": [
    {
      "rule_name": "CPUUsageHigh",
      "rule_id": 2,
      "count": 8,
      "severity": "warning",
      "latest_resolved_at": 1762334500,
      "total_duration": 3600,
      "avg_duration": 450,
      "alerts": [
        {
          "id": 10,
          "fingerprint": "abc123...",
          "rule_name": "CPUUsageHigh",
          "rule_id": 2,
          "status": "resolved",
          "severity": "warning",
          "started_at": 1762334000,
          "resolved_at": 1762334500,
          "duration": 500,
          "value": 85.5,
          "labels": {
            "instance": "server01",
            "job": "node-exporter"
          },
          "annotations": {
            "summary": "CPU usage is high"
          },
          "expr": "cpu_usage > 80"
        }
        // ... 更多历史告警
      ]
    }
    // ... 更多分组
  ]
}
```

**字段说明**:
- `total_duration`: 该规则下所有告警的总持续时间（秒）
- `avg_duration`: 平均持续时间（秒）
- `latest_resolved_at`: 最新恢复时间

## 前端集成示例

### Vue 3 + Element Plus

#### API 函数
```javascript
// src/api/alertRules.js
export const getCurrentAlertsGrouped = (params) => {
  return request({
    url: '/api/v1/alert-rules/events/current/grouped',
    method: 'get',
    params
  })
}

export const getAlertHistoryGrouped = (params) => {
  return request({
    url: '/api/v1/alert-rules/events/history/grouped',
    method: 'get',
    params
  })
}
```

#### 当前告警折叠显示组件

```vue
<template>
  <div class="current-alerts-grouped">
    <!-- 统计信息 -->
    <el-card class="stats-card">
      <el-statistic title="告警分组数" :value="groupData.total" />
      <el-statistic 
        title="总告警数" 
        :value="totalAlertCount" 
        style="margin-left: 20px" 
      />
    </el-card>

    <!-- 分组折叠面板 -->
    <el-collapse v-model="activeGroups" class="alert-collapse">
      <el-collapse-item
        v-for="group in groupData.groups"
        :key="group.rule_name"
        :name="group.rule_name"
      >
        <template #title>
          <div class="group-header">
            <el-tag :type="getSeverityType(group.severity)" size="large">
              {{ group.severity }}
            </el-tag>
            <span class="rule-name">{{ group.rule_name }}</span>
            <el-badge :value="group.count" class="badge" type="danger" />
            <span class="time">
              最新触发: {{ formatTime(group.latest_started_at) }}
            </span>
          </div>
        </template>

        <!-- 该分组下的告警列表 -->
        <el-table :data="group.alerts" border stripe>
          <el-table-column prop="fingerprint" label="指纹" width="120" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="当前值" width="100" />
          <el-table-column label="标签">
            <template #default="{ row }">
              <el-tag
                v-for="(value, key) in row.labels"
                :key="key"
                size="small"
                style="margin: 2px"
              >
                {{ key }}: {{ value }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="触发时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.started_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button
                type="primary"
                size="small"
                @click="showDetail(row)"
              >
                详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-collapse-item>
    </el-collapse>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="groupData.total"
      :page-sizes="[10, 20, 50]"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="loadData"
      @current-change="loadData"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getCurrentAlertsGrouped } from '@/api/alertRules'
import dayjs from 'dayjs'

const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const groupData = ref({
  total: 0,
  groups: []
})
const activeGroups = ref([])

// 计算总告警数
const totalAlertCount = computed(() => {
  return groupData.value.groups.reduce((sum, group) => sum + group.count, 0)
})

const loadData = async () => {
  loading.value = true
  try {
    const data = await getCurrentAlertsGrouped({
      page: currentPage.value,
      page_size: pageSize.value
    })
    groupData.value = data
    // 默认展开第一个分组
    if (data.groups.length > 0) {
      activeGroups.value = [data.groups[0].rule_name]
    }
  } catch (error) {
    console.error('加载失败:', error)
  } finally {
    loading.value = false
  }
}

const getSeverityType = (severity) => {
  const map = {
    'critical': 'danger',
    'warning': 'warning',
    'info': 'info'
  }
  return map[severity] || ''
}

const getStatusType = (status) => {
  const map = {
    'firing': 'danger',
    'pending': 'warning',
    'resolved': 'success'
  }
  return map[status] || ''
}

const formatTime = (timestamp) => {
  return dayjs.unix(timestamp).format('YYYY-MM-DD HH:mm:ss')
}

const showDetail = (alert) => {
  // 显示详情逻辑
  console.log('显示告警详情:', alert)
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.current-alerts-grouped {
  padding: 20px;
}

.stats-card {
  margin-bottom: 20px;
  display: flex;
  gap: 20px;
}

.alert-collapse {
  margin-bottom: 20px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 0;
}

.rule-name {
  font-size: 16px;
  font-weight: bold;
  flex: 1;
}

.badge {
  margin-left: auto;
}

.time {
  color: #909399;
  font-size: 14px;
  margin-left: 10px;
}
</style>
```

#### 历史告警折叠显示组件

```vue
<template>
  <div class="alert-history-grouped">
    <!-- 统计信息 -->
    <el-card class="stats-card">
      <el-statistic title="历史分组数" :value="groupData.total" />
    </el-card>

    <!-- 分组折叠面板 -->
    <el-collapse v-model="activeGroups">
      <el-collapse-item
        v-for="group in groupData.groups"
        :key="group.rule_name"
        :name="group.rule_name"
      >
        <template #title>
          <div class="group-header">
            <el-tag :type="getSeverityType(group.severity)" size="large">
              {{ group.severity }}
            </el-tag>
            <span class="rule-name">{{ group.rule_name }}</span>
            <el-badge :value="group.count" class="badge" />
            <span class="stats">
              平均持续: {{ formatDuration(group.avg_duration) }}
            </span>
            <span class="time">
              最新恢复: {{ formatTime(group.latest_resolved_at) }}
            </span>
          </div>
        </template>

        <!-- 该分组下的历史告警列表 -->
        <el-table :data="group.alerts" border stripe>
          <el-table-column prop="fingerprint" label="指纹" width="120" />
          <el-table-column label="等级" width="100">
            <template #default="{ row }">
              <el-tag :type="getSeverityType(row.severity)">
                {{ row.severity }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="持续时间" width="120">
            <template #default="{ row }">
              {{ formatDuration(row.duration) }}
            </template>
          </el-table-column>
          <el-table-column label="触发时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.started_at) }}
            </template>
          </el-table-column>
          <el-table-column label="恢复时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.resolved_at) }}
            </template>
          </el-table-column>
          <el-table-column label="标签">
            <template #default="{ row }">
              <el-tag
                v-for="(value, key) in row.labels"
                :key="key"
                size="small"
                style="margin: 2px"
              >
                {{ key }}: {{ value }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-collapse-item>
    </el-collapse>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="groupData.total"
      :page-sizes="[10, 20, 50]"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="loadData"
      @current-change="loadData"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAlertHistoryGrouped } from '@/api/alertRules'
import dayjs from 'dayjs'

const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const groupData = ref({
  total: 0,
  groups: []
})
const activeGroups = ref([])

const loadData = async () => {
  loading.value = true
  try {
    const data = await getAlertHistoryGrouped({
      page: currentPage.value,
      page_size: pageSize.value
    })
    groupData.value = data
  } catch (error) {
    console.error('加载失败:', error)
  } finally {
    loading.value = false
  }
}

const getSeverityType = (severity) => {
  const map = {
    'critical': 'danger',
    'warning': 'warning',
    'info': 'info'
  }
  return map[severity] || ''
}

const formatTime = (timestamp) => {
  return dayjs.unix(timestamp).format('YYYY-MM-DD HH:mm:ss')
}

const formatDuration = (seconds) => {
  if (!seconds) return '0秒'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  const parts = []
  if (hours > 0) parts.push(`${hours}小时`)
  if (minutes > 0) parts.push(`${minutes}分钟`)
  if (secs > 0) parts.push(`${secs}秒`)
  
  return parts.join('') || '0秒'
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.alert-history-grouped {
  padding: 20px;
}

.stats-card {
  margin-bottom: 20px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 0;
}

.rule-name {
  font-size: 16px;
  font-weight: bold;
  flex: 1;
}

.badge {
  margin-left: auto;
}

.stats {
  color: #409eff;
  font-size: 14px;
  margin-left: 10px;
}

.time {
  color: #909399;
  font-size: 14px;
  margin-left: 10px;
}
</style>
```

## 特性说明

### 1. 分组逻辑
- 按 `rule_name`（规则名称）分组
- 同一规则下的所有告警折叠在一起显示

### 2. 分页逻辑
- 分页基于**分组数**，不是告警数
- 默认每页显示 **10 个分组**
- 可以调整为 20、50 个分组

### 3. 排序逻辑
- **当前告警**: 按最新触发时间倒序
- **历史告警**: 按最新恢复时间倒序

### 4. 显示信息
- 分组头部：规则名称、告警数量、等级、状态、时间
- 展开后：该规则下所有告警的详细信息

## 优势

1. **减少页面高度**: 大量同规则告警被折叠，页面更简洁
2. **提高浏览效率**: 快速定位到特定规则
3. **分页更合理**: 每页10个分组，包含所有相关告警
4. **性能优化**: 后端一次性查询并分组，前端无需额外处理

## 注意事项

1. 原有的平铺API仍然保留，可以兼容旧前端
2. 分组API会一次性加载所有告警进行分组，数据量大时可能较慢
3. 建议在数据库层面添加索引优化查询性能：
   ```sql
   CREATE INDEX idx_alert_event_tenant_rule_started ON alert_event(tenant_id, rule_name, started_at DESC);
   CREATE INDEX idx_alert_history_tenant_rule_resolved ON alert_event_history(tenant_id, rule_name, resolved_at DESC);
   ```

