<template>
  <div class="silence">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>静默规则</span>
          <el-button type="primary" @click="dialogVisible = true">
            <el-icon><Plus /></el-icon>
            创建静默
          </el-button>
        </div>
      </template>
      
      <el-table :data="rules" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="名称" min-width="200" />
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
        <el-table-column prop="is_enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <el-dialog v-model="dialogVisible" title="创建静默规则" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
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
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSilenceRules, createSilenceRule, deleteSilenceRule } from '@/api/silence'
import dayjs from 'dayjs'

const loading = ref(false)
const rules = ref([])
const dialogVisible = ref(false)
const timeRange = ref([])

const form = ref({
  name: '',
  description: '',
  matchers: []
})

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

const handleCreate = async () => {
  if (!timeRange.value || timeRange.value.length !== 2) {
    ElMessage.error('请选择时间范围')
    return
  }
  
  try {
    await createSilenceRule({
      ...form.value,
      starts_at: Math.floor(timeRange.value[0].getTime() / 1000),
      ends_at: Math.floor(timeRange.value[1].getTime() / 1000),
      is_enabled: true
    })
    
    ElMessage.success('创建成功')
    dialogVisible.value = false
    loadRules()
  } catch (error) {
    console.error('创建失败:', error)
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

