<template>
  <div class="alert-rule-create">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? '编辑告警规则' : '创建告警规则' }}</span>
          <el-button @click="handleBack">返回</el-button>
        </div>
      </template>
      
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        style="max-width: 800px"
      >
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入规则名称" />
        </el-form-item>
        
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入规则描述"
          />
        </el-form-item>
        
        <el-form-item label="PromQL表达式" prop="expr">
          <el-input
            v-model="form.expr"
            type="textarea"
            :rows="4"
            placeholder="请输入PromQL表达式，例如: up == 0"
          />
        </el-form-item>
        
        <el-form-item label="告警等级" prop="severity">
          <el-select v-model="form.severity" placeholder="请选择告警等级">
            <el-option label="Critical" value="critical" />
            <el-option label="Warning" value="warning" />
            <el-option label="Info" value="info" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="评估间隔" prop="eval_interval">
          <el-input-number
            v-model="form.eval_interval"
            :min="10"
            :step="10"
          />
          <span style="margin-left: 10px">秒</span>
        </el-form-item>
        
        <el-form-item label="持续时间" prop="for_duration">
          <el-input-number
            v-model="form.for_duration"
            :min="0"
            :step="10"
          />
          <span style="margin-left: 10px">秒</span>
        </el-form-item>
        
        <el-form-item label="重复发送间隔" prop="repeat_interval">
          <el-select v-model="form.repeat_interval" placeholder="请选择重复发送间隔">
            <el-option label="15分钟" :value="900" />
            <el-option label="30分钟" :value="1800" />
            <el-option label="1小时" :value="3600" />
            <el-option label="3小时" :value="10800" />
            <el-option label="6小时" :value="21600" />
          </el-select>
          <span class="tip">告警持续未恢复时，间隔多久再次发送通知</span>
        </el-form-item>
        
        <el-form-item label="数据源" prop="datasource_id">
          <el-select v-model="form.datasource_id" placeholder="请选择数据源">
            <el-option
              v-for="ds in datasources"
              :key="ds.id"
              :label="ds.name"
              :value="ds.id"
            >
              <span>{{ ds.name }}</span>
              <span style="color: #999; margin-left: 10px">{{ ds.type }}</span>
            </el-option>
          </el-select>
          <el-button
            link
            type="primary"
            style="margin-left: 10px"
            @click="handleNavigate('/datasources')"
          >
            管理数据源
          </el-button>
        </el-form-item>
        
        <el-divider content-position="left">告警路由配置（可选）</el-divider>
        
        <el-form-item label="通知渠道">
          <el-select
            v-model="selectedChannels"
            multiple
            placeholder="请选择通知渠道"
            style="width: 100%"
          >
            <el-option
              v-for="channel in notificationChannels"
              :key="channel.id"
              :label="channel.name"
              :value="channel.id"
            >
              <span>{{ channel.name }}</span>
              <el-tag size="small" style="margin-left: 10px">
                {{ getChannelTypeName(channel.type) }}
              </el-tag>
            </el-option>
          </el-select>
          <el-button
            link
            type="primary"
            style="margin-left: 10px"
            @click="handleNavigate('/notifications')"
          >
            管理通知渠道
          </el-button>
          <span class="tip">留空则使用默认渠道</span>
        </el-form-item>
        
        <el-form-item label="标签">
          <div style="width: 100%">
            <div 
              v-for="(item, index) in labels" 
              :key="index"
              style="display: flex; gap: 10px; margin-bottom: 10px;"
            >
              <el-input
                v-model="item.key"
                placeholder="标签名（如: team）"
                style="flex: 1"
              />
              <el-input
                v-model="item.value"
                placeholder="标签值（如: backend）"
                style="flex: 1"
              />
              <el-button
                type="danger"
                :icon="Delete"
                circle
                @click="removeLabel(index)"
              />
            </div>
            <el-button
              type="primary"
              :icon="Plus"
              size="small"
              @click="addLabel"
            >
              添加标签
            </el-button>
            <el-divider direction="vertical" />
            <el-dropdown @command="handleLabelPreset">
              <el-button size="small" :icon="Star">
                常用标签
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="team">team（团队）</el-dropdown-item>
                  <el-dropdown-item command="service">service（服务）</el-dropdown-item>
                  <el-dropdown-item command="env">env（环境）</el-dropdown-item>
                  <el-dropdown-item command="region">region（区域）</el-dropdown-item>
                  <el-dropdown-item command="cluster">cluster（集群）</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <span class="tip">用于告警分组和筛选，例如：team=backend, service=api</span>
        </el-form-item>
        
        <el-form-item label="注释">
          <div style="width: 100%">
            <div 
              v-for="(item, index) in annotations" 
              :key="index"
              style="display: flex; gap: 10px; margin-bottom: 10px;"
            >
              <el-input
                v-model="item.key"
                placeholder="注释名（如: summary）"
                style="flex: 1"
              />
              <el-input
                v-model="item.value"
                placeholder="注释值（支持模板变量）"
                style="flex: 2"
              />
              <el-button
                type="danger"
                :icon="Delete"
                circle
                @click="removeAnnotation(index)"
              />
            </div>
            <el-button
              type="primary"
              :icon="Plus"
              size="small"
              @click="addAnnotation"
            >
              添加注释
            </el-button>
            <el-divider direction="vertical" />
            <el-dropdown @command="handleAnnotationPreset">
              <el-button size="small" :icon="Star">
                常用注释
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="summary">summary（摘要）</el-dropdown-item>
                  <el-dropdown-item command="description">description（详细描述）</el-dropdown-item>
                  <el-dropdown-item command="runbook_url">runbook_url（处理手册）</el-dropdown-item>
                  <el-dropdown-item command="dashboard_url">dashboard_url（仪表盘链接）</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <span class="tip">
            用于告警通知内容。支持模板变量：instance、value、labels.xxx 等
          </span>
        </el-form-item>
        
        <el-form-item label="是否启用" prop="is_enabled">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading">
            {{ isEdit ? '更新' : '创建' }}
          </el-button>
          <el-button @click="handleBack">取消</el-button>
          <el-button 
            type="success" 
            @click="handleTest" 
            :loading="testLoading"
            :disabled="!form.datasource_id || !form.expr"
          >
            <el-icon><VideoPlay /></el-icon>
            测试
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 测试结果面板 -->
      <el-card v-if="testResult" style="margin-top: 20px; max-width: 800px">
        <template #header>
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center;">
              <el-icon 
                :size="20" 
                :color="testResult.success ? '#67C23A' : '#F56C6C'"
                style="margin-right: 8px"
              >
                <component :is="testResult.success ? 'SuccessFilled' : 'CircleCloseFilled'" />
              </el-icon>
              <span>测试结果</span>
            </div>
            <el-button size="small" @click="testResult = null">清除</el-button>
          </div>
        </template>

        <!-- 成功结果 -->
        <div v-if="testResult.success">
          <el-alert 
            :title="`查询成功，匹配到 ${testResult.result_count} 条数据（耗时 ${testResult.query_time}s）`"
            type="success" 
            :closable="false"
            style="margin-bottom: 16px"
          />
          
          <div v-if="testResult.results && testResult.results.length > 0">
            <div 
              v-for="(item, index) in testResult.results" 
              :key="index"
              style="margin-bottom: 16px; padding: 12px; background: #f5f7fa; border-radius: 4px;"
            >
              <div style="font-weight: bold; margin-bottom: 8px;">
                结果 #{{ index + 1 }}
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: #606266;">标签: </span>
                <el-tag 
                  v-for="(value, key) in item.metric" 
                  :key="key"
                  size="small"
                  style="margin-right: 4px;"
                >
                  {{ key }}={{ value }}
                </el-tag>
              </div>
              <div>
                <span style="color: #606266;">值: </span>
                <span style="font-family: monospace; color: #E6A23C;">{{ item.value[1] }}</span>
                <span style="margin-left: 16px; color: #909399; font-size: 12px;">
                  时间: {{ formatTimestamp(item.value[0]) }}
                </span>
              </div>
            </div>
            
            <div v-if="testResult.result_count > 10" style="color: #909399; font-size: 14px;">
              显示前 10 条，共 {{ testResult.result_count }} 条
            </div>
          </div>
          <div v-else>
            <el-empty description="查询成功，但没有匹配到任何数据" />
          </div>
        </div>

        <!-- 错误结果 -->
        <div v-else>
          <el-alert 
            :title="`${getErrorTypeLabel(testResult.error_type)}: ${testResult.error}`"
            type="error" 
            :closable="false"
          />
          <div style="margin-top: 16px; padding: 12px; background: #fef0f0; border-radius: 4px; color: #F56C6C;">
            <div v-if="testResult.error_type === 'syntax'">
              <strong>语法错误提示：</strong>
              <ul style="margin: 8px 0; padding-left: 20px;">
                <li>检查 PromQL 表达式语法是否正确</li>
                <li>确保使用正确的操作符和函数</li>
                <li>参考 <a href="https://prometheus.io/docs/prometheus/latest/querying/basics/" target="_blank" style="color: #409EFF;">PromQL 文档</a></li>
              </ul>
            </div>
            <div v-else-if="testResult.error_type === 'connection'">
              <strong>连接错误提示：</strong>
              <ul style="margin: 8px 0; padding-left: 20px;">
                <li>检查数据源配置是否正确</li>
                <li>确认数据源服务是否正常运行</li>
                <li>检查网络连接</li>
              </ul>
            </div>
          </div>
        </div>
      </el-card>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router'
import { ElMessage } from 'element-plus'
import { VideoPlay, SuccessFilled, CircleCloseFilled, Plus, Delete, Star } from '@element-plus/icons-vue'
import { getAlertRule, createAlertRule, updateAlertRule, testAlertRule } from '@/api/alertRules'
import { getDatasources } from '@/api/datasources'
import { getNotificationChannels } from '@/api/notifications'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)

const isEdit = computed(() => !!route.params.id)

const form = ref({
  name: '',
  description: '',
  expr: '',
  severity: 'warning',
  eval_interval: 60,
  for_duration: 60,
  repeat_interval: 1800,
  datasource_id: 1,
  project_id: null,
  labels: {},
  annotations: {},
  is_enabled: true,
  route_config: {}
})

const labelsJson = ref('{}')
const annotationsJson = ref('{}')
const labels = ref([])
const annotations = ref([])
const datasources = ref([])
const notificationChannels = ref([])
const selectedChannels = ref([])
const testLoading = ref(false)
const testResult = ref(null)

const rules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  expr: [{ required: true, message: '请输入PromQL表达式', trigger: 'blur' }],
  severity: [{ required: true, message: '请选择告警等级', trigger: 'change' }],
  datasource_id: [{ required: true, message: '请选择数据源', trigger: 'change' }]
}

const getChannelTypeName = (type) => {
  const map = {
    'feishu': '飞书',
    'dingtalk': '钉钉',
    'wechat': '企业微信',
    'email': '邮件',
    'webhook': '自定义Webhook'
  }
  return map[type] || type
}

const loadDatasources = async () => {
  try {
    datasources.value = await getDatasources()
  } catch (error) {
    console.error('加载数据源失败:', error)
  }
}

const loadNotificationChannels = async () => {
  try {
    notificationChannels.value = await getNotificationChannels()
  } catch (error) {
    console.error('加载通知渠道失败:', error)
  }
}

const loadRule = async () => {
  if (!isEdit.value) {
    // 创建模式，重置表单
    resetForm()
    return
  }
  
  try {
    const data = await getAlertRule(route.params.id)
    form.value = {
      name: data.name,
      description: data.description,
      expr: data.expr,
      severity: data.severity,
      eval_interval: data.eval_interval,
      for_duration: data.for_duration,
      repeat_interval: data.repeat_interval || 1800,
      datasource_id: data.datasource_id,
      project_id: data.project_id,
      labels: data.labels || {},
      annotations: data.annotations || {},
      is_enabled: data.is_enabled,
      route_config: data.route_config || {}
    }
    
    // 转换为键值对数组
    labels.value = Object.entries(data.labels || {}).map(([key, value]) => ({ key, value }))
    annotations.value = Object.entries(data.annotations || {}).map(([key, value]) => ({ key, value }))
    
    labelsJson.value = JSON.stringify(data.labels || {}, null, 2)
    annotationsJson.value = JSON.stringify(data.annotations || {}, null, 2)
    selectedChannels.value = data.route_config?.notification_channels || []
  } catch (error) {
    console.error('加载失败:', error)
    ElMessage.error('加载规则失败')
  }
}

const resetForm = () => {
  form.value = {
    name: '',
    description: '',
    expr: '',
    severity: 'warning',
    eval_interval: 60,
    for_duration: 60,
    repeat_interval: 1800,
    datasource_id: 1,
    project_id: null,
    labels: {},
    annotations: {},
    is_enabled: true,
    route_config: {}
  }
  labels.value = []
  annotations.value = []
  labelsJson.value = '{}'
  annotationsJson.value = '{}'
  selectedChannels.value = []
  testResult.value = null
  // 清除表单验证
  formRef.value?.clearValidate()
}

const handleTest = async () => {
  if (!form.value.datasource_id || !form.value.expr) {
    ElMessage.warning('请先选择数据源并填写 PromQL 表达式')
    return
  }

  testLoading.value = true
  testResult.value = null
  
  try {
    const response = await testAlertRule({
      datasource_id: form.value.datasource_id,
      expr: form.value.expr,
      for_duration: form.value.for_duration
    })
    
    testResult.value = response
    
    if (response.success) {
      if (response.result_count === 0) {
        ElMessage.warning('查询成功，但没有匹配到任何数据')
      } else {
        ElMessage.success(`测试成功！匹配到 ${response.result_count} 条数据`)
      }
    } else {
      ElMessage.error(`测试失败: ${response.error}`)
    }
  } catch (error) {
    console.error('测试失败:', error)
    ElMessage.error('测试请求失败，请检查网络或稍后重试')
  } finally {
    testLoading.value = false
  }
}

const formatTimestamp = (timestamp) => {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN')
}

const getErrorTypeLabel = (type) => {
  const labels = {
    syntax: '语法错误',
    connection: '连接错误',
    execution: '执行错误'
  }
  return labels[type] || '错误'
}

const handleNavigate = (path) => {
  router.push(path).catch(err => {
    console.error('导航失败:', err)
  })
}

const handleBack = () => {
  router.replace('/alert-rules').catch(err => {
    console.error('返回失败:', err)
  })
}

const handleSubmit = async () => {
  if (loading.value) return
  
  try {
    await formRef.value?.validate()
  } catch (error) {
    return
  }
  
  // 检查是否有当前项目
  if (!userStore.currentProject) {
    ElMessage.error('请先选择项目')
    return
  }
  
  try {
    // 将标签和注释数组转换为对象
    const labelsObj = {}
    labels.value.forEach(item => {
      if (item.key && item.value) {
        labelsObj[item.key.trim()] = item.value.trim()
      }
    })
    
    const annotationsObj = {}
    annotations.value.forEach(item => {
      if (item.key && item.value) {
        annotationsObj[item.key.trim()] = item.value.trim()
      }
    })
    
    form.value.labels = labelsObj
    form.value.annotations = annotationsObj
    form.value.route_config = {
      notification_channels: selectedChannels.value
    }
    // 设置项目ID（创建时使用当前项目，编辑时保持原有项目）
    if (!isEdit.value) {
      form.value.project_id = userStore.currentProject.id
    }
  } catch (e) {
    ElMessage.error('标签或注释格式错误')
    return
  }
  
  loading.value = true
  try {
    if (isEdit.value) {
      await updateAlertRule(route.params.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createAlertRule(form.value)
      ElMessage.success('创建成功')
    }
    router.replace('/alert-rules').catch(err => {
      console.error('导航失败:', err)
    })
  } catch (error) {
    console.error('提交失败:', error)
    ElMessage.error('操作失败，请重试')
  } finally {
    loading.value = false
  }
}

// 标签管理
const addLabel = () => {
  labels.value.push({ key: '', value: '' })
}

const removeLabel = (index) => {
  labels.value.splice(index, 1)
}

const handleLabelPreset = (command) => {
  const presets = {
    team: { key: 'team', value: '' },
    service: { key: 'service', value: '' },
    env: { key: 'env', value: 'production' },
    region: { key: 'region', value: '' },
    cluster: { key: 'cluster', value: '' }
  }
  labels.value.push(presets[command])
}

// 注释管理
const addAnnotation = () => {
  annotations.value.push({ key: '', value: '' })
}

const removeAnnotation = (index) => {
  annotations.value.splice(index, 1)
}

const handleAnnotationPreset = (command) => {
  const presets = {
    summary: { key: 'summary', value: '{{labels.alertname}}: {{labels.instance}}' },
    description: { key: 'description', value: '当前值: {{value}}, 阈值已超过 {{labels.threshold}}' },
    runbook_url: { key: 'runbook_url', value: 'https://your-wiki.com/runbook/' },
    dashboard_url: { key: 'dashboard_url', value: 'https://your-grafana.com/d/' }
  }
  annotations.value.push(presets[command])
}

onBeforeRouteLeave((to, from, next) => {
  loading.value = false
  testLoading.value = false
  next()
})

// 监听路由参数变化，当从编辑切换到创建时重置表单
watch(() => route.params.id, (newId, oldId) => {
  // 当路由变化时重新加载
  loadRule()
})

onMounted(() => {
  loadDatasources()
  loadNotificationChannels()
  loadRule()
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

:deep(.el-form-item__content) {
  flex-wrap: wrap;
}

:deep(.el-input-number) {
  width: 200px;
}
</style>

