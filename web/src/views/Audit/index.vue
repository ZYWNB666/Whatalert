<template>
  <div class="audit-logs">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>审计日志</span>
        </div>
      </template>
      
      <!-- 搜索过滤 -->
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="操作类型">
          <el-select v-model="searchForm.action" clearable placeholder="全部" style="width: 120px">
            <el-option label="创建" value="create" />
            <el-option label="更新" value="update" />
            <el-option label="删除" value="delete" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="资源类型">
          <el-select v-model="searchForm.resource_type" clearable placeholder="全部" style="width: 140px">
            <el-option label="用户" value="user" />
            <el-option label="告警规则" value="alert_rule" />
            <el-option label="数据源" value="datasource" />
            <el-option label="通知渠道" value="notification" />
            <el-option label="静默规则" value="silence" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="用户名">
          <el-input v-model="searchForm.username" clearable placeholder="请输入用户名" style="width: 150px" />
        </el-form-item>
        
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" clearable placeholder="全部" style="width: 120px">
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      
      <el-table :data="logs" v-loading="loading" style="width: 100%">
        <el-table-column prop="action" label="操作" width="100">
          <template #default="{ row }">
            <el-tag :type="getActionType(row.action)" size="small">
              {{ getActionText(row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="resource_type" label="资源类型" width="120">
          <template #default="{ row }">
            {{ getResourceTypeText(row.resource_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="resource_name" label="资源名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="username" label="操作人" width="120" />
        <el-table-column prop="ip_address" label="IP地址" width="140" />
        <el-table-column label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadLogs"
          @current-change="loadLogs"
        />
      </div>
    </el-card>
    
    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="审计日志详情"
      width="700px"
    >
      <el-descriptions :column="2" border v-if="currentLog">
        <el-descriptions-item label="操作类型">
          <el-tag :type="getActionType(currentLog.action)" size="small">
            {{ getActionText(currentLog.action) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="资源类型">
          {{ getResourceTypeText(currentLog.resource_type) }}
        </el-descriptions-item>
        <el-descriptions-item label="资源ID">
          {{ currentLog.resource_id || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="资源名称">
          {{ currentLog.resource_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="操作人">
          {{ currentLog.username }}
        </el-descriptions-item>
        <el-descriptions-item label="用户ID">
          {{ currentLog.user_id }}
        </el-descriptions-item>
        <el-descriptions-item label="IP地址">
          {{ currentLog.ip_address }}
        </el-descriptions-item>
        <el-descriptions-item label="请求方法">
          {{ currentLog.request_method }}
        </el-descriptions-item>
        <el-descriptions-item label="请求路径" :span="2">
          {{ currentLog.request_path }}
        </el-descriptions-item>
        <el-descriptions-item label="时间" :span="2">
          {{ formatTime(currentLog.timestamp) }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="currentLog.status === 'success' ? 'success' : 'danger'" size="small">
            {{ currentLog.status === 'success' ? '成功' : '失败' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item v-if="currentLog.error_message" label="错误信息" :span="2">
          {{ currentLog.error_message }}
        </el-descriptions-item>
        <el-descriptions-item label="User Agent" :span="2">
          <div style="word-break: break-all;">{{ currentLog.user_agent || '-' }}</div>
        </el-descriptions-item>
        <el-descriptions-item v-if="currentLog.changes" label="变更内容" :span="2">
          <pre style="margin: 0; white-space: pre-wrap; word-break: break-all;">{{ JSON.stringify(currentLog.changes, null, 2) }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAuditLogs, getAuditLog } from '@/api/audit'

const loading = ref(false)
const logs = ref([])
const currentLog = ref(null)
const detailDialogVisible = ref(false)

const searchForm = ref({
  action: '',
  resource_type: '',
  username: '',
  status: ''
})

const pagination = ref({
  page: 1,
  page_size: 20,
  total: 0
})

const loadLogs = async () => {
  loading.value = true
  try {
    const params = {
      ...searchForm.value,
      page: pagination.value.page,
      page_size: pagination.value.page_size
    }
    
    const response = await getAuditLogs(params)
    logs.value = response.data
    pagination.value.total = response.total
  } catch (error) {
    console.error('加载失败:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.value.page = 1
  loadLogs()
}

const handleReset = () => {
  searchForm.value = {
    action: '',
    resource_type: '',
    username: '',
    status: ''
  }
  pagination.value.page = 1
  loadLogs()
}

const showDetail = async (row) => {
  try {
    currentLog.value = await getAuditLog(row.id)
    detailDialogVisible.value = true
  } catch (error) {
    console.error('加载详情失败:', error)
  }
}

const getActionType = (action) => {
  const map = {
    'create': 'success',
    'update': 'warning',
    'delete': 'danger'
  }
  return map[action] || ''
}

const getActionText = (action) => {
  const map = {
    'create': '创建',
    'update': '更新',
    'delete': '删除'
  }
  return map[action] || action
}

const getResourceTypeText = (type) => {
  const map = {
    'user': '用户',
    'alert_rule': '告警规则',
    'datasource': '数据源',
    'notification': '通知渠道',
    'silence': '静默规则',
    'settings': '系统设置'
  }
  return map[type] || type
}

const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

onMounted(() => {
  loadLogs()
})
</script>

<style scoped lang="scss">
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>

