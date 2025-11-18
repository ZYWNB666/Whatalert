<template>
  <div class="notifications">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>通知渠道</span>
          <el-button 
            v-if="canCreate"
            type="primary" 
            @click="showDialog()"
          >
            <el-icon><Plus /></el-icon>
            添加渠道
          </el-button>
        </div>
      </template>
      
      <el-table :data="channels" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getChannelTypeColor(row.type)">
              {{ getChannelTypeName(row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="is_enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_enabled"
              :disabled="!canUpdate"
              @change="handleToggleStatus(row)"
            />
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
      :title="isEdit ? '编辑通知渠道' : '添加通知渠道'"
      width="650px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="120px">
        <el-form-item label="渠道名称" prop="name">
          <el-input v-model="form.name" placeholder="例如: 运维组飞书" />
        </el-form-item>
        
        <el-form-item label="渠道类型" prop="type">
          <el-select v-model="form.type" placeholder="请选择" style="width: 100%">
            <el-option label="🚀 飞书" value="feishu" />
            <el-option label="💬 钉钉" value="dingtalk" />
            <el-option label="💼 企业微信" value="wechat" />
            <el-option label="📧 邮件" value="email" />
            <el-option label="🔗 自定义Webhook" value="webhook" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        
        <!-- 飞书配置 -->
        <template v-if="form.type === 'feishu'">
          <el-form-item label="Webhook URL" required>
            <el-input v-model="webhookUrl" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." />
          </el-form-item>
          <el-form-item label="Secret">
            <el-input v-model="feishuSecret" placeholder="可选，用于签名验证" />
          </el-form-item>
          <el-form-item label="卡片类型">
            <el-radio-group v-model="feishuCardType">
              <el-radio label="advanced">高级消息卡片</el-radio>
              <el-radio label="simple">简单文本</el-radio>
            </el-radio-group>
          </el-form-item>
        </template>
        
        <!-- 钉钉配置 -->
        <template v-if="form.type === 'dingtalk'">
          <el-form-item label="Webhook URL" required>
            <el-input v-model="webhookUrl" placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
          </el-form-item>
          <el-form-item label="Secret">
            <el-input v-model="dingtalkSecret" placeholder="用于签名认证" />
          </el-form-item>
        </template>
        
        <!-- 企业微信配置 -->
        <template v-if="form.type === 'wechat'">
          <el-form-item label="Webhook URL" required>
            <el-input v-model="webhookUrl" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." />
          </el-form-item>
        </template>
        
        <!-- 邮件配置 -->
        <template v-if="form.type === 'email'">
          <el-form-item label="收件人" required>
            <el-select
              v-model="emailTo"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="输入邮箱地址，回车添加"
              style="width: 100%"
            >
            </el-select>
            <span class="tip">可添加多个邮箱地址</span>
          </el-form-item>
          <el-form-item label="抄送">
            <el-select
              v-model="emailCc"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="可选"
              style="width: 100%"
            >
            </el-select>
          </el-form-item>
          <el-form-item label="主题前缀">
            <el-input v-model="emailSubjectPrefix" placeholder="[告警]" />
          </el-form-item>
        </template>
        
        <!-- Webhook配置 -->
        <template v-if="form.type === 'webhook'">
          <el-form-item label="Webhook URL" required>
            <el-input v-model="webhookUrl" placeholder="https://your-api.com/webhook/alerts" />
          </el-form-item>
          <el-form-item label="请求方法">
            <el-radio-group v-model="webhookMethod">
              <el-radio label="POST">POST</el-radio>
              <el-radio label="PUT">PUT</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="自定义Headers">
            <el-input
              v-model="webhookHeaders"
              type="textarea"
              :rows="3"
              placeholder='{"Authorization": "Bearer your-token", "Custom-Header": "value"}'
            />
            <span class="tip">JSON格式，例如添加认证令牌</span>
          </el-form-item>
          <el-form-item label="Body模板">
            <el-radio-group v-model="webhookBodyType" style="margin-bottom: 10px">
              <el-radio label="default">默认格式</el-radio>
              <el-radio label="custom">自定义模板</el-radio>
            </el-radio-group>
            <el-input
              v-if="webhookBodyType === 'custom'"
              v-model="webhookBodyTemplate"
              type="textarea"
              :rows="8"
              placeholder='自定义JSON模板，支持Jinja2语法。例如:
{
  "text": "{{ alert.rule_name }}",
  "severity": "{{ alert.severity }}",
  "value": {{ alert.value }},
  "status": "{{ status }}"
}'
            />
            <div v-else class="tip">
              默认格式将发送完整的告警信息，包括: fingerprint, rule_name, severity, status, value, labels, annotations 等
            </div>
          </el-form-item>
        </template>
        
        <el-divider content-position="left">标签过滤（可选）</el-divider>
        
        <el-form-item label="包含标签">
          <el-input
            v-model="includeLabelsJson"
            type="textarea"
            :rows="2"
            placeholder='{"severity": ["critical", "warning"]}'
          />
          <span class="tip">只发送包含这些标签的告警</span>
        </el-form-item>
        
        <el-form-item label="排除标签">
          <el-input
            v-model="excludeLabelsJson"
            type="textarea"
            :rows="2"
            placeholder='{"team": ["test"]}'
          />
          <span class="tip">排除包含这些标签的告警</span>
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
  getNotificationChannels,
  createNotificationChannel,
  updateNotificationChannel,
  deleteNotificationChannel,
  testNotificationChannel
} from '@/api/notifications'

const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const channels = ref([])
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
  type: 'feishu',
  description: '',
  config: {},
  filter_config: {},
  is_enabled: true,
  is_default: false,
  project_id: null
})

// 各类型配置
const webhookUrl = ref('')
const feishuSecret = ref('')
const feishuCardType = ref('advanced')
const dingtalkSecret = ref('')
const emailTo = ref([])
const emailCc = ref([])
const emailSubjectPrefix = ref('[告警]')
const webhookMethod = ref('POST')
const webhookHeaders = ref('{}')
const webhookBodyType = ref('default')
const webhookBodyTemplate = ref('')
const includeLabelsJson = ref('{}')
const excludeLabelsJson = ref('{}')

const formRules = {
  name: [{ required: true, message: '请输入渠道名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择渠道类型', trigger: 'change' }]
}

const loadChannels = async () => {
  loading.value = true
  try {
    channels.value = await getNotificationChannels()
  } catch (error) {
    console.error('加载失败:', error)
  } finally {
    loading.value = false
  }
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

const getChannelTypeColor = (type) => {
  const map = {
    'feishu': '',
    'dingtalk': 'success',
    'wechat': 'warning',
    'email': 'info',
    'webhook': 'primary'
  }
  return map[type] || ''
}

const showDialog = (row = null) => {
  if (row) {
    isEdit.value = true
    editId.value = row.id
    form.value = { ...row }
    
    // 解析配置
    if (row.type === 'feishu') {
      webhookUrl.value = row.config.webhook_url || ''
      feishuSecret.value = row.config.secret || ''
      feishuCardType.value = row.config.card_type || 'advanced'
    } else if (row.type === 'dingtalk') {
      webhookUrl.value = row.config.webhook_url || ''
      dingtalkSecret.value = row.config.secret || ''
    } else if (row.type === 'wechat') {
      webhookUrl.value = row.config.webhook_url || ''
    } else if (row.type === 'email') {
      emailTo.value = row.config.to || []
      emailCc.value = row.config.cc || []
      emailSubjectPrefix.value = row.config.subject_prefix || '[告警]'
    } else if (row.type === 'webhook') {
      webhookUrl.value = row.config.url || ''
      webhookMethod.value = row.config.method || 'POST'
      webhookHeaders.value = JSON.stringify(row.config.headers || {}, null, 2)
      webhookBodyType.value = row.config.body_template === 'default' || !row.config.body_template ? 'default' : 'custom'
      webhookBodyTemplate.value = webhookBodyType.value === 'custom' ? row.config.body_template : ''
    }
    
    // 解析过滤配置
    includeLabelsJson.value = JSON.stringify(row.filter_config.include_labels || {}, null, 2)
    excludeLabelsJson.value = JSON.stringify(row.filter_config.exclude_labels || {}, null, 2)
  } else {
    isEdit.value = false
    editId.value = null
  }
  dialogVisible.value = true
}

const resetForm = () => {
  form.value = {
    name: '',
    type: 'feishu',
    description: '',
    config: {},
    filter_config: {},
    is_enabled: true,
    is_default: false,
    project_id: null
  }
  webhookUrl.value = ''
  feishuSecret.value = ''
  feishuCardType.value = 'advanced'
  dingtalkSecret.value = ''
  emailTo.value = []
  emailCc.value = []
  emailSubjectPrefix.value = '[告警]'
  webhookMethod.value = 'POST'
  webhookHeaders.value = '{}'
  webhookBodyType.value = 'default'
  webhookBodyTemplate.value = ''
  includeLabelsJson.value = '{}'
  excludeLabelsJson.value = '{}'
  formRef.value?.resetFields()
}

const handleSubmit = async () => {
  // 防止重复提交
  if (submitting.value) return
  
  await formRef.value?.validate()
  
  // 构建配置
  if (form.value.type === 'feishu') {
    form.value.config = {
      webhook_url: webhookUrl.value,
      secret: feishuSecret.value,
      card_type: feishuCardType.value
    }
  } else if (form.value.type === 'dingtalk') {
    form.value.config = {
      webhook_url: webhookUrl.value,
      secret: dingtalkSecret.value
    }
  } else if (form.value.type === 'wechat') {
    form.value.config = {
      webhook_url: webhookUrl.value
    }
  } else if (form.value.type === 'email') {
    form.value.config = {
      to: emailTo.value,
      cc: emailCc.value,
      subject_prefix: emailSubjectPrefix.value
    }
  } else if (form.value.type === 'webhook') {
    // 解析headers
    let headers = {}
    try {
      headers = webhookHeaders.value ? JSON.parse(webhookHeaders.value) : {}
    } catch (e) {
      ElMessage.error('Headers格式错误，请检查JSON格式')
      return
    }
    
    form.value.config = {
      url: webhookUrl.value,
      method: webhookMethod.value,
      headers: headers,
      body_template: webhookBodyType.value === 'default' ? 'default' : webhookBodyTemplate.value
    }
  }
  
  // 解析过滤配置
  try {
    const includeLabels = JSON.parse(includeLabelsJson.value)
    const excludeLabels = JSON.parse(excludeLabelsJson.value)
    form.value.filter_config = {
      include_labels: includeLabels,
      exclude_labels: excludeLabels
    }
  } catch (e) {
    ElMessage.error('标签过滤格式错误')
    return
  }
  
  submitting.value = true
  try {
    if (isEdit.value) {
      await updateNotificationChannel(editId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      // 创建时设置当前项目ID
      if (!form.value.project_id && userStore.currentProject) {
        form.value.project_id = userStore.currentProject.id
      }
      await createNotificationChannel(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadChannels()
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    submitting.value = false
  }
}

const handleTest = async (row) => {
  const loading = ElMessage({
    message: '发送测试消息中...',
    type: 'info',
    duration: 0
  })
  
  try {
    await testNotificationChannel(row.id)
    loading.close()
    ElMessage.success('测试消息发送成功！请检查接收端')
  } catch (error) {
    loading.close()
    console.error('测试失败:', error)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除通知渠道 "${row.name}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteNotificationChannel(row.id)
    ElMessage.success('删除成功')
    loadChannels()
  } catch (e) {
    if (e !== 'cancel') {
      console.error('删除失败:', e)
    }
  }
}

const handleToggleStatus = async (row) => {
  try {
    await updateNotificationChannel(row.id, { is_enabled: row.is_enabled })
    ElMessage.success(`已${row.is_enabled ? '启用' : '禁用'}通知渠道`)
  } catch (error) {
    // 失败时回滚状态
    row.is_enabled = !row.is_enabled
    console.error('更新状态失败:', error)
    ElMessage.error('更新状态失败')
  }
}

onMounted(() => {
  loadChannels()
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
