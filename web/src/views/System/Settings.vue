<template>
  <div class="system-settings">
    <el-card>
      <template #header>
        <span>系统设置</span>
      </template>
      
      <el-tabs v-model="activeTab">
        <el-tab-pane label="SMTP 邮件配置" name="smtp">
          <el-form
            ref="smtpFormRef"
            :model="smtpForm"
            :rules="smtpRules"
            label-width="120px"
            style="max-width: 600px; margin-top: 20px"
          >
            <el-form-item label="SMTP 服务器" prop="host">
              <el-input v-model="smtpForm.host" placeholder="smtp.example.com" />
            </el-form-item>
            
            <el-form-item label="端口" prop="port">
              <el-input-number v-model="smtpForm.port" :min="1" :max="65535" />
            </el-form-item>
            
            <el-form-item label="用户名" prop="username">
              <el-input v-model="smtpForm.username" placeholder="alert@example.com" />
            </el-form-item>
            
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="smtpForm.password"
                type="password"
                show-password
                placeholder="SMTP 密码"
              />
            </el-form-item>
            
            <el-form-item label="发件人地址" prop="from_addr">
              <el-input v-model="smtpForm.from_addr" placeholder="alert@example.com" />
            </el-form-item>
            
            <el-form-item label="使用 TLS">
              <el-switch v-model="smtpForm.use_tls" />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="handleSaveSmtp" :loading="saving">
                保存配置
              </el-button>
              <el-button @click="showTestDialog = true">
                发送测试邮件
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="其他设置" name="general">
          <el-empty description="更多设置开发中..." />
        </el-tab-pane>
      </el-tabs>
    </el-card>
    
    <!-- 测试邮件对话框 -->
    <el-dialog v-model="showTestDialog" title="发送测试邮件" width="500px">
      <el-form label-width="100px">
        <el-form-item label="收件人邮箱">
          <el-input v-model="testEmail" placeholder="test@example.com" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showTestDialog = false">取消</el-button>
        <el-button type="primary" @click="handleTestSmtp" :loading="testing">
          发送
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

const activeTab = ref('smtp')
const smtpFormRef = ref()
const saving = ref(false)
const testing = ref(false)
const showTestDialog = ref(false)
const testEmail = ref('')

const smtpForm = ref({
  host: '',
  port: 587,
  username: '',
  password: '',
  from_addr: '',
  use_tls: true
})

const smtpRules = {
  host: [{ required: true, message: '请输入SMTP服务器', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  from_addr: [{ required: true, message: '请输入发件人地址', trigger: 'blur' }]
}

const loadSmtpSettings = async () => {
  try {
    const data = await request({
      url: '/settings/smtp',
      method: 'get'
    })
    smtpForm.value = data
  } catch (error) {
    console.error('加载SMTP配置失败:', error)
  }
}

const handleSaveSmtp = async () => {
  await smtpFormRef.value?.validate()
  
  saving.value = true
  try {
    await request({
      url: '/settings/smtp',
      method: 'post',
      data: smtpForm.value
    })
    ElMessage.success('SMTP 配置已保存')
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saving.value = false
  }
}

const handleTestSmtp = async () => {
  if (!testEmail.value) {
    ElMessage.error('请输入收件人邮箱')
    return
  }
  
  testing.value = true
  try {
    await request({
      url: '/settings/smtp/test',
      method: 'post',
      params: { test_email: testEmail.value }
    })
    ElMessage.success('测试邮件已发送，请检查收件箱')
    showTestDialog.value = false
  } catch (error) {
    console.error('发送失败:', error)
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  loadSmtpSettings()
})
</script>

<style scoped lang="scss">
.system-settings {
  .tip {
    font-size: 12px;
    color: #999;
    margin-top: 4px;
    display: block;
  }
}
</style>

