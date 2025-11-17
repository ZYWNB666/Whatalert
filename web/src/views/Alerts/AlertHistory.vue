<template>
  <div class="alert-history">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>历史告警</span>
          <div class="header-actions">
            <el-switch
              v-model="groupByRule"
              active-text="按规则分组"
              inactive-text="平铺显示"
              style="margin-right: 10px"
              @change="handleGroupChange"
            />
            <el-button @click="loadAlerts" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 查询条件 -->
      <el-form :model="queryForm" inline style="margin-bottom: 20px;">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="timeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            style="width: 360px"
            @change="handleTimeRangeChange"
          />
        </el-form-item>
        
        <el-form-item label="告警等级">
          <el-select v-model="queryForm.severity" placeholder="全部" clearable style="width: 120px">
            <el-option label="全部" value="" />
            <el-option label="Critical" value="critical" />
            <el-option label="Warning" value="warning" />
            <el-option label="Info" value="info" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="标签键">
          <el-input 
            v-model="queryForm.label_key" 
            placeholder="如: instance" 
            clearable 
            style="width: 150px"
          />
        </el-form-item>
        
        <el-form-item label="标签值">
          <el-input 
            v-model="queryForm.label_value" 
            placeholder="如: prod-server-1" 
            clearable 
            style="width: 150px"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleQuery">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      
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
              </div>
            </template>
            <el-table :data="group" style="width: 100%">
              <el-table-column prop="duration" label="持续时间" width="120">
                <template #default="{ row }">
                  {{ formatDuration(row.duration) }}
                </template>
              </el-table-column>
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
              <el-table-column prop="resolved_at" label="恢复时间" width="180">
                <template #default="{ row }">
                  {{ formatTime(row.resolved_at) }}
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
        <el-table-column prop="duration" label="持续时间" width="120">
          <template #default="{ row }">
            {{ formatDuration(row.duration) }}
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="触发时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="resolved_at" label="恢复时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.resolved_at) }}
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
    
    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="历史告警详情"
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
          <el-descriptions-item label="当前值">
            {{ currentAlert.value }}
          </el-descriptions-item>
          <el-descriptions-item label="持续时间">
            {{ formatDuration(currentAlert.duration) }}
          </el-descriptions-item>
          <el-descriptions-item label="触发时间" :span="2">
            {{ formatTime(currentAlert.started_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="恢复时间" :span="2">
            {{ formatTime(currentAlert.resolved_at) }}
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
import { ref, computed, onMounted } from 'vue'
import { getAlertHistory } from '@/api/alertRules'
import { Refresh } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const loading = ref(false)
const alerts = ref([])
const detailVisible = ref(false)
const currentAlert = ref(null)
const groupByRule = ref(true)
const activeGroups = ref([])
const isFirstLoad = ref(true)  // 标记是否首次加载

// 查询条件
const timeRange = ref([])
const queryForm = ref({
  severity: '',
  label_key: '',
  label_value: '',
  start_time: null,
  end_time: null
})

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

const handleTimeRangeChange = (value) => {
  if (value && value.length === 2) {
    queryForm.value.start_time = Math.floor(value[0].getTime() / 1000)
    queryForm.value.end_time = Math.floor(value[1].getTime() / 1000)
  } else {
    queryForm.value.start_time = null
    queryForm.value.end_time = null
  }
}

const handleQuery = () => {
  loadAlerts()
}

const handleReset = () => {
  timeRange.value = []
  queryForm.value = {
    severity: '',
    label_key: '',
    label_value: '',
    start_time: null,
    end_time: null
  }
  loadAlerts()
}

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
    
    // 构建查询参数
    const params = { limit: 100 }
    if (queryForm.value.severity) {
      params.severity = queryForm.value.severity
    }
    if (queryForm.value.start_time) {
      params.start_time = queryForm.value.start_time
    }
    if (queryForm.value.end_time) {
      params.end_time = queryForm.value.end_time
    }
    if (queryForm.value.label_key) {
      params.label_key = queryForm.value.label_key
    }
    if (queryForm.value.label_value) {
      params.label_value = queryForm.value.label_value
    }
    
    alerts.value = await getAlertHistory(params)
    
    // 只在首次加载时展开所有分组
    if (groupByRule.value && isFirstLoad.value) {
      activeGroups.value = Object.keys(groupedAlerts.value)
      isFirstLoad.value = false
    } else if (groupByRule.value) {
      // 刷新时保持之前的展开状态
      const currentGroups = Object.keys(groupedAlerts.value)
      activeGroups.value = previousActiveGroups.filter(group => 
        currentGroups.includes(group)
      )
    }
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

const showDetail = (row) => {
  currentAlert.value = row
  detailVisible.value = true
}

onMounted(() => {
  loadAlerts()
})
</script>

<style scoped lang="scss">
.alert-history {
  :deep(.el-form--inline .el-form-item) {
    margin-bottom: 10px;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .header-actions {
    display: flex;
    align-items: center;
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

