<template>
  <div class="dashboard">
    <!-- 工具栏 -->
    <div class="toolbar">
      <el-space>
        <el-button :icon="Refresh" @click="loadData" :loading="loading">刷新</el-button>
        <span class="refresh-config">
          <span class="label">自动刷新:</span>
          <el-select v-model="refreshInterval" size="small" style="width: 100px" @change="handleRefreshIntervalChange">
            <el-option label="关闭" :value="0" />
            <el-option label="5秒" :value="5" />
            <el-option label="10秒" :value="10" />
            <el-option label="15秒" :value="15" />
            <el-option label="30秒" :value="30" />
            <el-option label="60秒" :value="60" />
          </el-select>
        </span>
        <span class="last-update-time">上次更新: {{ lastUpdateTime }}</span>
      </el-space>
    </div>
    
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card stat-card-danger" v-loading="loading">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon><Warning /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.firing }}</div>
              <div class="stat-label">告警中</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card stat-card-warning" v-loading="loading">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.pending }}</div>
              <div class="stat-label">待处理</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card stat-card-success" v-loading="loading">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.resolved }}</div>
              <div class="stat-label">24h已恢复</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card stat-card-info" v-loading="loading">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon><Bell /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.rules }}</div>
              <div class="stat-label">告警规则</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>最近告警（按规则分组）</span>
          </template>
          <el-table 
            :data="groupedRecentAlerts" 
            v-loading="loading" 
            style="width: 100%"
            :row-style="{ cursor: 'pointer' }"
            @row-click="handleRowClick"
          >
            <el-table-column prop="rule_name" label="规则名称" min-width="200" />
            <el-table-column prop="severity" label="等级" width="100">
              <template #default="{ row }">
                <el-tag
                  :type="getSeverityType(row.severity)"
                  size="small"
                >
                  {{ getSeverityText(row.severity) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag
                  :type="getStatusType(row.status)"
                  size="small"
                >
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="count" label="告警数量" width="100" align="center">
              <template #default="{ row }">
                <el-tag type="danger" size="small">{{ row.count }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="latest_started_at" label="触发时间" width="180">
              <template #default="{ row }">
                {{ formatTime(row.latest_started_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { getCurrentAlertsGrouped, getCurrentAlertsStats, countAlertHistory, getAlertRules } from '@/api/alertRules'
import dayjs from 'dayjs'

const router = useRouter()

const stats = ref({
  firing: 0,
  pending: 0,
  resolved: 0,
  rules: 0
})

const groupedRecentAlerts = ref([])
const loading = ref(false)
const lastUpdateTime = ref('--')
const refreshInterval = ref(15)
let refreshTimer = null

const loadData = async () => {
  loading.value = true
  try {
    // 获取当前告警统计 - 只获取数量，不获取详情
    const statsData = await getCurrentAlertsStats()
    stats.value.firing = statsData.firing || 0
    stats.value.pending = statsData.pending || 0
    
    // 获取最近24小时恢复的告警数量 - 直接统计，不获取数据
    const oneDayAgo = dayjs().subtract(24, 'hour').unix()
    const now = dayjs().unix()
    const historyCount = await countAlertHistory({ 
      start_time: oneDayAgo,
      end_time: now
    })
    stats.value.resolved = historyCount.count || 0
    
    // 获取告警规则总数
    const rules = await getAlertRules()
    stats.value.rules = Array.isArray(rules) ? rules.length : 0
    
    // 获取按规则分组的告警（每页10个分组）
    const groupedData = await getCurrentAlertsGrouped({ page: 1, page_size: 10 })
    groupedRecentAlerts.value = groupedData.groups || []
    
    // 更新最后刷新时间
    lastUpdateTime.value = dayjs().format('HH:mm:ss')
  } catch (error) {
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
}

const handleRowClick = (row) => {
  // 点击行跳转到当前告警页面
  router.push('/current-alerts')
}

const getSeverityType = (severity) => {
  const map = {
    'critical': 'danger',
    'warning': 'warning',
    'info': 'info'
  }
  return map[severity] || ''
}

const getSeverityText = (severity) => {
  const map = {
    'critical': '严重',
    'warning': '警告',
    'info': '信息'
  }
  return map[severity] || severity
}

const getStatusType = (status) => {
  const map = {
    'firing': 'danger',
    'pending': 'warning',
    'resolved': 'success'
  }
  return map[status] || ''
}

const getStatusText = (status) => {
  const map = {
    'firing': '告警中',
    'pending': '待触发',
    'resolved': '已恢复'
  }
  return map[status] || status
}

const formatTime = (timestamp) => {
  return dayjs.unix(timestamp).format('YYYY-MM-DD HH:mm:ss')
}

const handleRefreshIntervalChange = (value) => {
  // 清除旧的定时器
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }

  // 如果选择了刷新间隔，设置新的定时器
  if (value > 0) {
    refreshTimer = setInterval(() => {
      loadData()
    }, value * 1000)
  }
}

onMounted(() => {
  loadData()
  // 设置初始自动刷新（默认10秒）
  if (refreshInterval.value > 0) {
    refreshTimer = setInterval(() => {
      loadData()
    }, refreshInterval.value * 1000)
  }
})

onUnmounted(() => {
  // 清理定时器
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped lang="scss">
.dashboard {
  .toolbar {
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .refresh-config {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .label {
        color: #606266;
        font-size: 14px;
      }
    }
    
    .last-update-time {
      color: #909399;
      font-size: 14px;
    }
  }
  
  .stat-card {
    .stat-content {
      display: flex;
      align-items: center;
      gap: 20px;
    }
    
    .stat-icon {
      font-size: 48px;
      width: 64px;
      height: 64px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .stat-info {
      flex: 1;
    }
    
    .stat-value {
      font-size: 32px;
      font-weight: bold;
      line-height: 1;
      margin-bottom: 8px;
    }
    
    .stat-label {
      font-size: 14px;
      color: #999;
    }
    
    &.stat-card-danger {
      .stat-icon {
        background: #fef0f0;
        color: #f56c6c;
      }
      .stat-value {
        color: #f56c6c;
      }
    }
    
    &.stat-card-warning {
      .stat-icon {
        background: #fdf6ec;
        color: #e6a23c;
      }
      .stat-value {
        color: #e6a23c;
      }
    }
    
    &.stat-card-success {
      .stat-icon {
        background: #f0f9ff;
        color: #67c23a;
      }
      .stat-value {
        color: #67c23a;
      }
    }
    
    &.stat-card-info {
      .stat-icon {
        background: #f4f4f5;
        color: #909399;
      }
      .stat-value {
        color: #909399;
      }
    }
  }
  
  // 表格行悬停效果
  :deep(.el-table__row) {
    &:hover {
      background-color: #f5f7fa;
      cursor: pointer;
    }
  }
}
</style>

