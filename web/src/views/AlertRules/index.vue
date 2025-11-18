<template>
  <div class="alert-rules">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>告警规则列表</span>
          <el-button 
            v-if="canCreate" 
            type="primary" 
            @click="handleCreate"
          >
            <el-icon><Plus /></el-icon>
            创建规则
          </el-button>
        </div>
      </template>
      
      <el-table :data="rules" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="规则名称" min-width="200" />
        <el-table-column prop="severity" label="等级" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small">
              {{ row.severity }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expr" label="表达式" min-width="300" show-overflow-tooltip />
        <el-table-column prop="eval_interval" label="评估间隔" width="100">
          <template #default="{ row }">
            {{ row.eval_interval }}s
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_enabled"
              :disabled="!canUpdate"
              @change="handleToggleStatus(row)"
            />
          </template>
        </el-table-column>
        <el-table-column v-if="canUpdate || canDelete" label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="canUpdate"
              link 
              type="primary" 
              size="small" 
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-button 
              v-if="canDelete"
              link 
              type="danger" 
              size="small"
              :loading="row._deleting"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { getAlertRules, deleteAlertRule, updateAlertRule } from '@/api/alertRules'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const rules = ref([])

// 权限检查 - 基于项目角色
const canCreate = computed(() => userStore.canCreate())
const canUpdate = computed(() => userStore.canUpdate())
const canDelete = computed(() => userStore.canDelete())

const loadRules = async () => {
  loading.value = true
  try {
    rules.value = await getAlertRules()
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

const handleCreate = () => {
  router.push('/alert-rules/create')
}

const handleEdit = (row) => {
  router.push(`/alert-rules/edit/${row.id}`)
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除规则 "${row.name}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    // 立即显示加载状态
    row._deleting = true
    
    // 乐观更新：立即从列表中移除
    const index = rules.value.findIndex(r => r.id === row.id)
    if (index > -1) {
      rules.value.splice(index, 1)
    }
    
    // 显示删除中的提示
    const loadingMessage = ElMessage({
      message: '正在删除...',
      type: 'info',
      duration: 0
    })
    
    try {
      await deleteAlertRule(row.id)
      loadingMessage.close()
      ElMessage.success('删除成功')
    } catch (error) {
      // 如果删除失败，恢复数据
      loadingMessage.close()
      if (index > -1) {
        rules.value.splice(index, 0, row)
      }
      ElMessage.error('删除失败，请重试')
      console.error('删除失败:', error)
    }
  } catch (e) {
    if (e !== 'cancel') {
      console.error('删除操作异常:', e)
    }
  }
}

const handleToggleStatus = async (row) => {
  try {
    await updateAlertRule(row.id, { is_enabled: row.is_enabled })
    ElMessage.success(`已${row.is_enabled ? '启用' : '禁用'}告警规则`)
  } catch (error) {
    // 失败时回滚状态
    row.is_enabled = !row.is_enabled
    console.error('更新状态失败:', error)
    ElMessage.error('更新状态失败')
  }
}

onMounted(() => {
  loadRules()
})

// 页面激活时也重新加载，确保从创建/编辑页面返回时数据是最新的
onActivated(() => {
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

