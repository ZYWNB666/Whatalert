<template>
  <div class="silence">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>静默规则</span>
          <el-button v-if="canCreate" type="primary" @click="openDialog()">
            <el-icon><Plus /></el-icon>
            创建静默
          </el-button>
        </div>
      </template>
      
      <el-table :data="rules" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column label="标签匹配器" min-width="250">
          <template #default="{ row }">
            <el-tag 
              v-for="(matcher, index) in row.matchers" 
              :key="index"
              size="small"
              style="margin-right: 4px; margin-bottom: 4px;"
            >
              {{ matcher.label }} {{ getOperatorSymbol(matcher.operator) }} {{ matcher.value }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="comment" label="备注" min-width="200" show-overflow-tooltip />
        <el-table-column prop="starts_at" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.starts_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="ends_at" label="结束时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.ends_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_enabled"
              :disabled="!canCreate"
              @change="handleToggleStatus(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewSilencedAlerts(row)">
              查看
            </el-button>
            <el-button v-if="canCreate" link type="primary" size="small" @click="openEditDialog(row)">
              编辑
            </el-button>
            <el-button v-if="canDelete" link type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑静默规则' : '创建静默规则'" width="700px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="请输入静默规则名称" />
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入描述" />
        </el-form-item>
        
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="timeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            style="width: 100%"
          />
        </el-form-item>
        
        <el-divider content-position="left">标签匹配器（Alertmanager 风格）</el-divider>
        
        <el-form-item label="匹配器">
          <div style="width: 100%;">
            <div 
              v-for="(matcher, index) in form.matchers" 
              :key="index"
              style="display: flex; margin-bottom: 8px; gap: 8px;"
            >
              <el-input 
                v-model="matcher.label" 
                placeholder="标签名，如: alertname"
                style="flex: 1;"
              />
              <el-select v-model="matcher.operator" style="width: 120px;">
                <el-option label="= (等于)" value="=" />
                <el-option label="!= (不等于)" value="!=" />
                <el-option label="=~ (正则匹配)" value="=~" />
                <el-option label="!~ (正则不匹配)" value="!~" />
              </el-select>
              <el-input 
                v-model="matcher.value" 
                placeholder="标签值，如: HighCPU"
                style="flex: 1;"
              />
              <el-button 
                type="danger" 
                :icon="Delete"
                @click="removeMatcher(index)"
                :disabled="form.matchers.length === 1"
              />
            </div>
            <el-button 
              type="primary" 
              :icon="Plus" 
              size="small"
              @click="addMatcher"
              style="width: 100%;"
            >
              添加匹配器
            </el-button>
          </div>
        </el-form-item>
        
        <el-alert 
          title="匹配器说明" 
          type="info" 
          :closable="false"
          style="margin-top: 10px;"
        >
          <ul style="margin: 0; padding-left: 20px;">
            <li><strong>=</strong>: 精确匹配，如 alertname = "HighCPU"</li>
            <li><strong>!=</strong>: 不等于，如 severity != "info"</li>
            <li><strong>=~</strong>: 正则表达式匹配，如 instance =~ "prod-.*"</li>
            <li><strong>!~</strong>: 正则表达式不匹配，如 job !~ "test-.*"</li>
          </ul>
          <div style="margin-top: 8px;">
            <strong>示例：</strong>alertname = "HighCPU" 且 severity =~ "(warning|critical)"
          </div>
        </el-alert>
        
        <el-form-item label="备注" style="margin-top: 16px;">
          <el-input v-model="form.comment" type="textarea" :rows="2" placeholder="可选：说明静默原因" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">{{ isEdit ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>
    
    <!-- 被静默的告警对话框 -->
    <el-dialog v-model="alertsDialogVisible" title="被静默的告警" width="900px">
      <div v-if="currentSilenceRule" style="margin-bottom: 16px;">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="规则名称">{{ currentSilenceRule.name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentSilenceRule.is_active ? 'success' : 'info'" size="small">
              {{ currentSilenceRule.is_active ? '生效中' : '未生效' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="告警数量">{{ silencedAlerts.length }}</el-descriptions-item>
        </el-descriptions>
      </div>
      
      <el-table :data="silencedAlerts" v-loading="alertsLoading" max-height="500">
        <el-table-column prop="rule_name" label="规则名称" min-width="150" />
        <el-table-column prop="severity" label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small">
              {{ row.severity }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标签" min-width="300">
          <template #default="{ row }">
            <el-tag 
              v-for="(value, key) in row.labels" 
              :key="key"
              size="small"
              style="margin-right: 4px; margin-bottom: 4px;"
            >
              {{ key }}={{ value }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
      </el-table>
      
      <template #footer>
        <el-button @click="alertsDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { getSilenceRules, createSilenceRule, updateSilenceRule, deleteSilenceRule, getSilencedAlerts } from '@/api/silence'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 权限检查 - 基于项目角色
const canCreate = computed(() => userStore.canCreate())
const canDelete = computed(() => userStore.canDelete())
import dayjs from 'dayjs'

const loading = ref(false)
const alertsLoading = ref(false)
const alertsDialogVisible = ref(false)
const currentSilenceRule = ref(null)
const silencedAlerts = ref([])
const rules = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const timeRange = ref([])

const form = ref({
  name: '',
  description: '',
  matchers: [
    { label: '', operator: '=', value: '' }
  ],
  comment: ''
})

const openDialog = () => {
  isEdit.value = false
  editingId.value = null
  form.value = {
    name: '',
    description: '',
    matchers: [
      { label: '', operator: '=', value: '' }
    ],
    comment: ''
  }
  timeRange.value = []
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  editingId.value = row.id
  form.value = {
    name: row.name,
    description: row.description || '',
    matchers: JSON.parse(JSON.stringify(row.matchers)),
    comment: row.comment || ''
  }
  timeRange.value = [
    new Date(row.starts_at * 1000),
    new Date(row.ends_at * 1000)
  ]
  dialogVisible.value = true
}

const addMatcher = () => {
  form.value.matchers.push({ label: '', operator: '=', value: '' })
}

const removeMatcher = (index) => {
  if (form.value.matchers.length > 1) {
    form.value.matchers.splice(index, 1)
  }
}

const getOperatorSymbol = (op) => {
  return op || '='
}

const loadRules = async () => {
  loading.value = true
  try {
    rules.value = await getSilenceRules()
  } catch (error) {
    console.error('加载失败:', error)
  } finally {
    loading.value = false
  }
}

const handleSubmit = async () => {
  if (!form.value.name) {
    ElMessage.error('请输入静默规则名称')
    return
  }
  
  if (!timeRange.value || timeRange.value.length !== 2) {
    ElMessage.error('请选择时间范围')
    return
  }
  
  // 验证匹配器
  for (const matcher of form.value.matchers) {
    if (!matcher.label || !matcher.value) {
      ElMessage.error('请填写完整的匹配器（标签名和值不能为空）')
      return
    }
  }
  
  const data = {
    name: form.value.name,
    description: form.value.description,
    matchers: form.value.matchers,
    starts_at: Math.floor(timeRange.value[0].getTime() / 1000),
    ends_at: Math.floor(timeRange.value[1].getTime() / 1000),
    comment: form.value.comment,
    is_enabled: true
  }
  
  try {
    if (isEdit.value) {
      await updateSilenceRule(editingId.value, data)
      ElMessage.success('更新成功')
    } else {
      await createSilenceRule(data)
      ElMessage.success('创建成功')
    }
    
    dialogVisible.value = false
    loadRules()
  } catch (error) {
    console.error('操作失败:', error)
    ElMessage.error(error.message || '操作失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除静默规则 "${row.name}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteSilenceRule(row.id)
    ElMessage.success('删除成功')
    loadRules()
  } catch (e) {
    if (e !== 'cancel') {
      console.error('删除失败:', e)
    }
  }
}

const handleToggleStatus = async (row) => {
  try {
    await updateSilenceRule(row.id, { is_enabled: row.is_enabled })
    ElMessage.success(`已${row.is_enabled ? '启用' : '禁用'}静默规则`)
  } catch (error) {
    // 失败时回滚状态
    row.is_enabled = !row.is_enabled
    console.error('更新状态失败:', error)
    ElMessage.error('更新状态失败')
  }
}

const viewSilencedAlerts = async (row) => {
  try {
    alertsLoading.value = true
    alertsDialogVisible.value = true
    const result = await getSilencedAlerts(row.id)
    currentSilenceRule.value = result.silence_rule
    silencedAlerts.value = result.alerts || []
  } catch (error) {
    console.error('获取被静默告警失败:', error)
    ElMessage.error('获取被静默告警失败')
  } finally {
    alertsLoading.value = false
  }
}

const getSeverityType = (severity) => {
  const types = {
    'critical': 'danger',
    'warning': 'warning',
    'info': 'info'
  }
  return types[severity] || 'info'
}

const getStatusType = (status) => {
  const types = {
    'firing': 'danger',
    'pending': 'warning',
    'resolved': 'success'
  }
  return types[status] || 'info'
}

const formatTime = (timestamp) => {
  return dayjs.unix(timestamp).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  loadRules()
})
</script>

<style scoped lang="scss">
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

