<template>
  <div class="current-alerts">
    <!-- 规则列表视图 -->
    <el-card v-if="!selectedRule">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span>当前告警</span>
            <el-tag type="info" size="small" style="margin-left: 10px">总计: {{ totalCount }} 条</el-tag>
          </div>
          <div class="header-actions">
            <span class="refresh-config">
              <span class="label">自动刷新:</span>
              <el-select v-model="refreshInterval" size="small" style="width: 100px" @change="handleRefreshIntervalChange">
                <el-option label="关闭" :value="0" />
                <el-option label="5秒" :value="5" />
                <el-option label="10秒" :value="10" />
                <el-option label="15秒" :value="15" />
                <el-option label="30秒" :value="30" />
              </el-select>
            </span>
            <span class="last-update-time">上次更新: {{ lastUpdateTime }}</span>
            <el-button @click="loadAlerts" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 规则卡片列表 -->
      <div v-loading="loading" class="rule-cards">
        <el-card
          v-for="group in groupedAlerts"
          :key="group.rule_id"
          class="rule-card"
          shadow="hover"
          @click="openRuleDetail(group.rule_name, group)"
        >
          <div class="rule-card-content">
            <div class="rule-header">
              <span class="rule-name">{{ group.rule_name }}</span>
              <el-badge :value="group.count" class="badge" />
            </div>
            <div class="rule-info">
              <el-tag
                :type="getSeverityType(group.severity)"
                size="small"
              >
                {{ group.severity }}
              </el-tag>
              <el-tag
                :type="getStatusType(group.status)"
                size="small"
                style="margin-left: 8px"
              >
                {{ getStatusText(group.status) }}
              </el-tag>
              <span class="rule-time">
                最新触发: {{ formatTime(group.latest_started_at) }}
              </span>
            </div>
          </div>
        </el-card>
      </div>
    </el-card>
    
    <!-- 规则详情视图 -->
    <el-card v-else>
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-button text @click="backToList">
              <el-icon><ArrowLeft /></el-icon>
              返回
            </el-button>
            <span style="margin-left: 15px">{{ selectedRule }}</span>
            <el-tag type="info" size="small" style="margin-left: 10px">
              共 {{ ruleAlerts.length }} 条告警
            </el-tag>
          </div>
          <div class="header-actions">
            <span class="refresh-config">
              <span class="label">自动刷新:</span>
              <el-select v-model="refreshInterval" size="small" style="width: 100px" @change="handleRefreshIntervalChange">
                <el-option label="关闭" :value="0" />
                <el-option label="5秒" :value="5" />
                <el-option label="10秒" :value="10" />
                <el-option label="15秒" :value="15" />
                <el-option label="30秒" :value="30" />
              </el-select>
            </span>
            <el-button @click="loadAlerts" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 规则告警列表 -->
      <el-table :data="paginatedRuleAlerts" v-loading="loading" style="width: 100%">
        <el-table-column prop="value" label="当前值" width="120" />
        <el-table-column label="标签" min-width="250">
          <template #default="{ row }">
            <el-tag
              v-for="(value, key) in getDisplayLabels(row.labels)"
              :key="key"
              size="small"
              style="margin-right: 5px; margin-bottom: 5px"
            >
              {{ key }}: {{ value }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="触发时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 规则详情分页 -->
      <el-pagination
        v-model:current-page="ruleCurrentPage"
        v-model:page-size="rulePageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="ruleAlerts.length"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="handleRuleSizeChange"
        @current-change="handleRulePageChange"
      />
    </el-card>
    
    <el-dialog
      v-model="detailVisible"
      title="告警详情"
      width="700px"
    >
      <div v-if="currentAlert">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="规则名称">
            {{ currentAlert.rule_name }}
          </el-descriptions-item>
          <el-descriptions-item label="等级">
            <el-tag :type="getSeverityType(currentAlert.severity)">
              {{ currentAlert.severity }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentAlert.status)">
              {{ getStatusText(currentAlert.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="当前值">
            {{ currentAlert.value }}
          </el-descriptions-item>
          <el-descriptions-item label="触发时间" :span="2">
            {{ formatTime(currentAlert.started_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="指纹" :span="2">
            {{ currentAlert.fingerprint }}
          </el-descriptions-item>
        </el-descriptions>
        
        <el-divider />
        
        <h4>标签</h4>
        <el-tag
          v-for="(value, key) in currentAlert.labels"
          :key="key"
          style="margin: 5px"
        >
          {{ key }}: {{ value }}
        </el-tag>
        
        <el-divider />
        
        <h4>注释</h4>
        <el-descriptions :column="1" border>
          <el-descriptions-item
            v-for="(value, key) in currentAlert.annotations"
            :key="key"
            :label="key"
          >
            {{ value }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getCurrentAlerts, getCurrentAlertsGrouped } from '@/api/alertRules'
import { ArrowLeft } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const loading = ref(false)
const groupedAlerts = ref([])  // 从后端获取的分组数据
const totalCount = ref(0)
const detailVisible = ref(false)
const currentAlert = ref(null)
const lastUpdateTime = ref('--')
const refreshInterval = ref(10)  // 默认10秒
let refreshTimer = null

// 规则详情相关
const selectedRule = ref(null)
const selectedRuleId = ref(null)
const ruleAlerts = ref([])
const ruleCurrentPage = ref(1)
const rulePageSize = ref(10)

// 规则详情分页数据
const paginatedRuleAlerts = computed(() => {
  const start = (ruleCurrentPage.value - 1) * rulePageSize.value
  const end = start + rulePageSize.value
  return ruleAlerts.value.slice(start, end)
})

const loadAlerts = async () => {
  loading.value = true
  try {
    if (selectedRule.value) {
      // 在规则详情页，只获取该规则的告警
      await loadRuleAlerts()
    } else {
      // 在列表页，只获取统计数据（最多100条分组）
      const result = await getCurrentAlertsGrouped({ page: 1, page_size: 100 })
      groupedAlerts.value = result.groups || []
      totalCount.value = result.total || 0
    }
    
    // 更新最后刷新时间
    lastUpdateTime.value = dayjs().format('HH:mm:ss')
  } catch (error) {
    console.error('加载失败:', error)
  } finally {
    loading.value = false
  }
}

const loadRuleAlerts = async () => {
  try {
    const params = {
      rule_id: selectedRuleId.value,
      limit: 1000,
      skip: 0
    }
    
    const result = await getCurrentAlerts(params)
    if (Array.isArray(result)) {
      ruleAlerts.value = result
    } else {
      ruleAlerts.value = result.alerts || []
    }
  } catch (error) {
    console.error('加载规则告警失败:', error)
  }
}

const openRuleDetail = async (ruleName, group) => {
  selectedRule.value = ruleName
  selectedRuleId.value = group.rule_id
  ruleCurrentPage.value = 1
  
  // 加载该规则的所有告警
  loading.value = true
  await loadRuleAlerts()
  loading.value = false
}

const backToList = () => {
  selectedRule.value = null
  selectedRuleId.value = null
  ruleAlerts.value = []
  ruleCurrentPage.value = 1
  // 返回列表时重新加载统计数据
  loadAlerts()
}

const handleRulePageChange = () => {
  // v-model 会自动更新 ruleCurrentPage
}

const handleRuleSizeChange = () => {
  ruleCurrentPage.value = 1
}

const handleRefreshIntervalChange = () => {
  // 清除旧定时器
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  
  // 设置新定时器
  if (refreshInterval.value > 0) {
    refreshTimer = setInterval(loadAlerts, refreshInterval.value * 1000)
  }
}

const getDisplayLabels = (labels) => {
  // 过滤掉一些不需要显示的标签
  const { __name__, job, ...displayLabels } = labels || {}
  return displayLabels
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

const showDetail = (row) => {
  currentAlert.value = row
  detailVisible.value = true
}

onMounted(() => {
  loadAlerts()
  // 根据默认刷新间隔设置定时器
  if (refreshInterval.value > 0) {
    refreshTimer = setInterval(loadAlerts, refreshInterval.value * 1000)
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
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .header-left {
    display: flex;
    align-items: center;
  }
  
  .header-actions {
    display: flex;
    align-items: center;
    gap: 15px;
    
    .refresh-config {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .label {
        font-size: 14px;
        color: #606266;
      }
    }
    
    .last-update-time {
      font-size: 12px;
      color: #909399;
    }
  }
}

.rule-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 15px;
  
  .rule-card {
    cursor: pointer;
    transition: transform 0.2s;
    
    &:hover {
      transform: translateY(-2px);
    }
    
    .rule-card-content {
      .rule-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
        
        .rule-name {
          font-size: 16px;
          font-weight: 600;
          color: #303133;
        }
        
        .badge {
          :deep(.el-badge__content) {
            font-size: 14px;
          }
        }
      }
      
      .rule-info {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        
        .rule-time {
          font-size: 12px;
          color: #909399;
          margin-left: auto;
        }
      }
    }
  }
}
</style>

