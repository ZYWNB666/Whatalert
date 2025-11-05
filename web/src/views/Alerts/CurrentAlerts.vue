<template>
  <div class="current-alerts">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>当前告警</span>
          <div class="header-actions">
            <span class="last-update-time">上次更新: {{ lastUpdateTime }}</span>
            <el-switch
              v-model="groupByRule"
              active-text="按规则分组"
              inactive-text="平铺显示"
              style="margin-left: 10px; margin-right: 10px"
              @change="handleGroupChange"
            />
            <el-button @click="loadAlerts" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 分组显示模式 -->
      <div v-if="groupByRule" class="grouped-alerts">
        <el-collapse v-model="activeGroups">
          <el-collapse-item
            v-for="(group, ruleName) in groupedAlerts"
            :key="ruleName"
            :name="ruleName"
          >
            <template #title>
              <div class="group-title">
                <span class="rule-name">{{ ruleName }}</span>
                <el-badge :value="group.length" class="badge" />
                <el-tag
                  :type="getSeverityType(group[0].severity)"
                  size="small"
                  style="margin-left: 10px"
                >
                  {{ group[0].severity }}
                </el-tag>
                <el-tag
                  :type="getStatusType(group[0].status)"
                  size="small"
                  style="margin-left: 5px"
                >
                  {{ getStatusText(group[0].status) }}
                </el-tag>
              </div>
            </template>
            <el-table :data="group" style="width: 100%">
              <el-table-column prop="value" label="当前值" width="120" />
              <el-table-column label="标签" min-width="200">
                <template #default="{ row }">
                  <el-tag
                    v-for="(value, key) in getDisplayLabels(row.labels)"
                    :key="key"
                    size="small"
                    style="margin-right: 5px"
                  >
                    {{ key }}: {{ value }}
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
          </el-collapse-item>
        </el-collapse>
      </div>
      
      <!-- 平铺显示模式 -->
      <el-table v-else :data="alerts" v-loading="loading" style="width: 100%">
        <el-table-column prop="rule_name" label="规则名称" min-width="200" />
        <el-table-column prop="severity" label="等级" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small">
              {{ row.severity }}
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
        <el-table-column prop="value" label="当前值" width="120" />
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
import { getCurrentAlerts } from '@/api/alertRules'
import dayjs from 'dayjs'

const loading = ref(false)
const alerts = ref([])
const detailVisible = ref(false)
const currentAlert = ref(null)
const groupByRule = ref(true)
const activeGroups = ref([])
const lastUpdateTime = ref('--')
const isFirstLoad = ref(true)  // 标记是否首次加载
let refreshTimer = null

// 按规则分组
const groupedAlerts = computed(() => {
  const groups = {}
  alerts.value.forEach(alert => {
    if (!groups[alert.rule_name]) {
      groups[alert.rule_name] = []
    }
    groups[alert.rule_name].push(alert)
  })
  return groups
})

const handleGroupChange = () => {
  if (groupByRule.value) {
    // 切换到分组模式时，展开所有分组
    activeGroups.value = Object.keys(groupedAlerts.value)
  }
}

const loadAlerts = async () => {
  loading.value = true
  try {
    // 保存当前展开的分组状态
    const previousActiveGroups = [...activeGroups.value]
    
    alerts.value = await getCurrentAlerts()
    
    // 只在首次加载时展开所有分组
    if (groupByRule.value && isFirstLoad.value) {
      activeGroups.value = Object.keys(groupedAlerts.value)
      isFirstLoad.value = false
    } else if (groupByRule.value) {
      // 刷新时保持之前的展开状态
      // 如果有新分组出现，可以选择是否自动展开（这里选择不展开）
      const currentGroups = Object.keys(groupedAlerts.value)
      activeGroups.value = previousActiveGroups.filter(group => 
        currentGroups.includes(group)
      )
    }
    
    // 更新最后刷新时间
    lastUpdateTime.value = dayjs().format('HH:mm:ss')
  } catch (error) {
    console.error('加载失败:', error)
  } finally {
    loading.value = false
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
  // 每10秒自动刷新，提升实时性
  refreshTimer = setInterval(loadAlerts, 10000)
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
  
  .header-actions {
    display: flex;
    align-items: center;
  }
  
  .last-update-time {
    color: #909399;
    font-size: 14px;
  }
}

.grouped-alerts {
  .group-title {
    display: flex;
    align-items: center;
    flex: 1;
    
    .rule-name {
      font-weight: 500;
      margin-right: 10px;
    }
    
    .badge {
      margin-left: auto;
      margin-right: 10px;
    }
  }
  
  :deep(.el-collapse-item__header) {
    height: auto;
    padding: 10px 0;
  }
  
  :deep(.el-collapse-item__content) {
    padding-bottom: 15px;
  }
}
</style>

