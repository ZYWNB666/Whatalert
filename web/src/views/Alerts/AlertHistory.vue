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
        <div v-if="Object.keys(paginatedGroups).length > 0">
          <el-collapse v-model="activeGroups">
            <el-collapse-item
              v-for="(group, ruleName) in paginatedGroups"
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
          
          <!-- 分页组件 -->
          <div style="margin-top: 20px; display: flex; justify-content: space-between; align-items: center;">
            <div style="color: #606266;">
              共 {{ alerts.length }} 条告警，分为 {{ totalGroups }} 个规则
            </div>
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[5, 10, 20, 50]"
              :total="totalGroups"
              layout="sizes, prev, pager, next, jumper"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </div>
        <el-empty v-else description="暂无数据" />
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
const activeGroups = ref([])  // 默认空数组，表示全部折叠

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)

// 默认时间范围：当前时间向前推1天
const now = new Date()
const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)

// 查询条件
const timeRange = ref([oneDayAgo, now])
const queryForm = ref({
  severity: '',
  label_key: '',
  label_value: '',
  start_time: Math.floor(oneDayAgo.getTime() / 1000),
  end_time: Math.floor(now.getTime() / 1000)
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

// 计算总分组数
const totalGroups = computed(() => {
  return Object.keys(groupedAlerts.value).length
})

// 当前页显示的分组
const paginatedGroups = computed(() => {
  const allGroups = groupedAlerts.value
  const groupNames = Object.keys(allGroups)
  
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  const currentGroupNames = groupNames.slice(start, end)
  
  const result = {}
  currentGroupNames.forEach(name => {
    result[name] = allGroups[name]
  })
  return result
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
  currentPage.value = 1  // 重置到第一页
  loadAlerts()
}

const handleReset = () => {
  // 重置为默认1天时间范围
  const now = new Date()
  const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  
  timeRange.value = [oneDayAgo, now]
  queryForm.value = {
    severity: '',
    label_key: '',
    label_value: '',
    start_time: Math.floor(oneDayAgo.getTime() / 1000),
    end_time: Math.floor(now.getTime() / 1000)
  }
  currentPage.value = 1  // 重置到第一页
  loadAlerts()
}

const handleGroupChange = () => {
  // 切换到分组模式时，保持折叠状态
  if (!groupByRule.value) {
    activeGroups.value = []
  }
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1  // 改变页大小时重置到第一页
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  // 切换页面时，保持折叠状态（不自动展开）
}

const loadAlerts = async () => {
  loading.value = true
  try {
    // 构建查询参数
    const params = { limit: 1000 }  // 加载更多数据以支持分页
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
    
    // 加载后保持折叠状态（不自动展开任何分组）
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

:deep(.el-pagination) {
  display: flex;
  justify-content: flex-end;
}
</style>

