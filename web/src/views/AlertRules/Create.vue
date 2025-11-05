<template>
  <div class="alert-rule-create">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? '编辑告警规则' : '创建告警规则' }}</span>
          <el-button @click="router.back()">返回</el-button>
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
            @click="router.push('/datasources')"
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
            @click="router.push('/notifications')"
          >
            管理通知渠道
          </el-button>
          <span class="tip">留空则使用默认渠道</span>
        </el-form-item>
        
        <el-form-item label="标签">
          <el-input
            v-model="labelsJson"
            type="textarea"
            :rows="3"
            placeholder='{"team": "backend", "service": "api"}'
          />
        </el-form-item>
        
        <el-form-item label="注释">
          <el-input
            v-model="annotationsJson"
            type="textarea"
            :rows="3"
            placeholder='{"summary": "实例 {{instance}} 告警", "description": "当前值: {{value}}"}'
          />
          <span class="tip">支持模板变量: {{instance}}, {{value}} 等</span>
        </el-form-item>
        
        <el-form-item label="是否启用" prop="is_enabled">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading">
            {{ isEdit ? '更新' : '创建' }}
          </el-button>
          <el-button @click="router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getAlertRule, createAlertRule, updateAlertRule } from '@/api/alertRules'
import { getDatasources } from '@/api/datasources'
import { getNotificationChannels } from '@/api/notifications'

const router = useRouter()
const route = useRoute()
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
  datasource_id: 1,
  labels: {},
  annotations: {},
  is_enabled: true,
  route_config: {}
})

const labelsJson = ref('{}')
const annotationsJson = ref('{}')
const datasources = ref([])
const notificationChannels = ref([])
const selectedChannels = ref([])

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
    // 如果不是编辑模式，重置表单
    form.value = {
      name: '',
      description: '',
      expr: '',
      severity: 'warning',
      eval_interval: 60,
      for_duration: 60,
      datasource_id: 1,
      labels: {},
      annotations: {},
      is_enabled: true,
      route_config: {}
    }
    labelsJson.value = '{}'
    annotationsJson.value = '{}'
    selectedChannels.value = []
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
      datasource_id: data.datasource_id,
      labels: data.labels || {},
      annotations: data.annotations || {},
      is_enabled: data.is_enabled,
      route_config: data.route_config || {}
    }
    labelsJson.value = JSON.stringify(data.labels || {}, null, 2)
    annotationsJson.value = JSON.stringify(data.annotations || {}, null, 2)
    selectedChannels.value = data.route_config?.notification_channels || []
  } catch (error) {
    console.error('加载失败:', error)
    ElMessage.error('加载规则失败')
  }
}

const handleSubmit = async () => {
  // 防止重复提交
  if (loading.value) return
  
  await formRef.value?.validate()
  
  try {
    form.value.labels = JSON.parse(labelsJson.value)
    form.value.annotations = JSON.parse(annotationsJson.value)
    form.value.route_config = {
      notification_channels: selectedChannels.value
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
    // 使用 push 而不是 back，确保列表页面会重新加载
    router.push('/alert-rules')
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    loading.value = false
  }
}

// 监听路由参数变化，确保切换编辑对象时重新加载数据
watch(() => route.params.id, () => {
  loadRule()
}, { immediate: false })

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
</style>

