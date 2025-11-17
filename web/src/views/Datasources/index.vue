<template>
  <div class="datasources">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据源管理</span>
          <el-button 
            v-if="canCreate"
            type="primary" 
            @click="showDialog()"
          >
            <el-icon><Plus /></el-icon>
            添加数据源
          </el-button>
        </div>
      </template>
      
      <el-table :data="datasources" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="type" label="类型" width="150">
          <template #default="{ row }">
            <el-tag>{{ getDatasourceTypeName(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="url" label="地址" min-width="300" show-overflow-tooltip />
        <el-table-column prop="is_enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_default" label="默认" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="primary" size="small">
              默认
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="canUpdate || canDelete" label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleTest(row)">
              测试
            </el-button>
            <el-button 
              v-if="canUpdate"
              link 
              type="primary" 
              size="small" 
              @click="showDialog(row)"
            >
              编辑
            </el-button>
            <el-button 
              v-if="canDelete"
              link 
              type="danger" 
              size="small" 
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑数据源' : '添加数据源'"
      width="600px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="120px">
        <el-form-item label="数据源名称" prop="name">
          <el-input v-model="form.name" placeholder="例如: 生产环境Prometheus" />
        </el-form-item>
        
        <el-form-item label="数据源类型" prop="type">
          <el-select v-model="form.type" placeholder="请选择" style="width: 100%">
            <el-option label="Prometheus" value="prometheus" />
            <el-option label="VictoriaMetrics" value="victoriametrics" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="数据源地址" prop="url">
          <el-input v-model="form.url" placeholder="http://prometheus:9090 或 http://vmselect:8481/select/0/prometheus" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            <strong>请填写基础URL，不要包含具体的API端点：</strong><br/>
            • Prometheus: http://prometheus:9090<br/>
            • VictoriaMetrics: http://vmselect:8481/select/0/prometheus<br/>
            系统会自动添加 /api/v1/query 或 /api/v1/query_range
          </div>
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        
        <el-form-item label="认证类型">
          <el-select v-model="authType" placeholder="无需认证" style="width: 100%">
            <el-option label="无需认证" value="none" />
            <el-option label="Token" value="token" />
            <el-option label="Basic Auth" value="basic" />
          </el-select>
        </el-form-item>
        
        <el-form-item v-if="authType === 'token'" label="Token">
          <el-input v-model="authToken" placeholder="Bearer xxx" />
        </el-form-item>
        
        <el-form-item v-if="authType === 'basic'" label="用户名">
          <el-input v-model="authUsername" />
        </el-form-item>
        
        <el-form-item v-if="authType === 'basic'" label="密码">
          <el-input v-model="authPassword" type="password" show-password />
        </el-form-item>
        
        <el-form-item label="额外标签">
          <el-input
            v-model="labelsJson"
            type="textarea"
            :rows="2"
            placeholder='{"cluster": "prod", "region": "us-west"}'
          />
          <span class="tip">JSON 格式，这些标签会附加到所有告警</span>
        </el-form-item>
        
        <el-form-item label="是否启用">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
        
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import {
  getDatasources,
  createDatasource,
  updateDatasource,
  deleteDatasource,
  testDatasource
} from '@/api/datasources'

const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const datasources = ref([])
const dialogVisible = ref(false)
const formRef = ref()

// 权限检查 - 基于项目角色
const canCreate = computed(() => userStore.canCreate())
const canUpdate = computed(() => userStore.canUpdate())
const canDelete = computed(() => userStore.canDelete())

const isEdit = ref(false)
const editId = ref(null)

const form = ref({
  name: '',
  type: 'prometheus',
  url: '',
  description: '',
  is_enabled: true,
  is_default: false,
  auth_config: {},
  http_config: {},
  extra_labels: {}
})

const authType = ref('none')
const authToken = ref('')
const authUsername = ref('')
const authPassword = ref('')
const labelsJson = ref('{}')

const formRules = {
  name: [{ required: true, message: '请输入数据源名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择数据源类型', trigger: 'change' }],
  url: [{ required: true, message: '请输入数据源地址', trigger: 'blur' }]
}

const loadDatasources = async () => {
  loading.value = true
  try {
    datasources.value = await getDatasources()
  } catch (error) {
    console.error('加载失败:', error)
  } finally {
    loading.value = false
  }
}

const getDatasourceTypeName = (type) => {
  const map = {
    'prometheus': 'Prometheus',
    'victoriametrics': 'VictoriaMetrics'
  }
  return map[type] || type
}

const showDialog = (row = null) => {
  if (row) {
    isEdit.value = true
    editId.value = row.id
    form.value = { ...row }
    labelsJson.value = JSON.stringify(row.extra_labels || {}, null, 2)
    
    // 解析认证配置
    if (row.auth_config?.type) {
      authType.value = row.auth_config.type
      if (row.auth_config.type === 'token') {
        authToken.value = row.auth_config.token || ''
      } else if (row.auth_config.type === 'basic') {
        authUsername.value = row.auth_config.username || ''
        authPassword.value = row.auth_config.password || ''
      }
    }
  } else {
    isEdit.value = false
    editId.value = null
  }
  dialogVisible.value = true
}

const resetForm = () => {
  form.value = {
    name: '',
    type: 'prometheus',
    url: '',
    description: '',
    is_enabled: true,
    is_default: false,
    auth_config: {},
    http_config: {},
    extra_labels: {}
  }
  authType.value = 'none'
  authToken.value = ''
  authUsername.value = ''
  authPassword.value = ''
  labelsJson.value = '{}'
  formRef.value?.resetFields()
}

const handleSubmit = async () => {
  // 防止重复提交
  if (submitting.value) return
  
  await formRef.value?.validate()
  
  // 解析标签
  try {
    form.value.extra_labels = JSON.parse(labelsJson.value)
  } catch (e) {
    ElMessage.error('标签格式错误')
    return
  }
  
  // 构建认证配置
  if (authType.value === 'token') {
    form.value.auth_config = {
      type: 'token',
      token: authToken.value
    }
  } else if (authType.value === 'basic') {
    form.value.auth_config = {
      type: 'basic',
      username: authUsername.value,
      password: authPassword.value
    }
  } else {
    form.value.auth_config = {}
  }
  
  submitting.value = true
  try {
    if (isEdit.value) {
      await updateDatasource(editId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createDatasource(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadDatasources()
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    submitting.value = false
  }
}

const handleTest = async (row) => {
  const loading = ElMessage({
    message: '测试连接中...',
    type: 'info',
    duration: 0
  })
  
  try {
    const result = await testDatasource(row.id)
    loading.close()
    ElMessage.success(`连接成功！查询到 ${result.metrics_count} 个指标`)
  } catch (error) {
    loading.close()
    console.error('测试失败:', error)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除数据源 "${row.name}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteDatasource(row.id)
    ElMessage.success('删除成功')
    loadDatasources()
  } catch (e) {
    if (e !== 'cancel') {
      console.error('删除失败:', e)
    }
  }
}

onMounted(() => {
  loadDatasources()
})
</script>

<style scoped lang="scss">
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tip {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
  display: block;
}
</style>
