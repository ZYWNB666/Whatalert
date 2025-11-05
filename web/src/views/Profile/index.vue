<template>
  <div class="profile">
    <el-card class="profile-card">
      <template #header>
        <span>个人信息</span>
      </template>
      
      <el-form :model="profileForm" label-width="100px">
        <el-form-item label="用户名">
          <el-input v-model="profileForm.username" disabled />
        </el-form-item>
        
        <el-form-item label="邮箱">
          <el-input v-model="profileForm.email" disabled />
        </el-form-item>
        
        <el-form-item label="姓名">
          <el-input v-model="profileForm.full_name" disabled />
        </el-form-item>
        
        <el-form-item label="手机号">
          <el-input v-model="profileForm.phone" disabled>
            <template #suffix>
              <el-button link type="primary" @click="showPhoneDialog = true">
                修改
              </el-button>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card class="password-card" style="margin-top: 20px">
      <template #header>
        <span>安全设置</span>
      </template>
      
      <el-form label-width="100px">
        <el-form-item label="登录密码">
          <el-input value="********" disabled>
            <template #suffix>
              <el-button link type="primary" @click="showPasswordDialog = true">
                修改
              </el-button>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 修改手机号对话框 -->
    <el-dialog
      v-model="showPhoneDialog"
      title="修改手机号"
      width="450px"
      @closed="resetPhoneForm"
    >
      <el-form ref="phoneFormRef" :model="phoneForm" :rules="phoneRules" label-width="100px">
        <el-form-item label="新手机号" prop="phone">
          <el-input v-model="phoneForm.phone" placeholder="请输入新手机号" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showPhoneDialog = false">取消</el-button>
        <el-button type="primary" @click="handlePhoneSubmit" :loading="phoneSubmitting">
          确定
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 修改密码对话框 -->
    <el-dialog
      v-model="showPasswordDialog"
      title="修改密码"
      width="450px"
      @closed="resetPasswordForm"
    >
      <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="100px">
        <el-form-item label="旧密码" prop="old_password">
          <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="请输入旧密码" />
        </el-form-item>
        
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="请输入新密码" />
        </el-form-item>
        
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showPasswordDialog = false">取消</el-button>
        <el-button type="primary" @click="handlePasswordSubmit" :loading="passwordSubmitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { updateUser, updateUserPassword } from '@/api/users'

const userStore = useUserStore()

const profileForm = ref({
  username: '',
  email: '',
  full_name: '',
  phone: ''
})

const showPhoneDialog = ref(false)
const showPasswordDialog = ref(false)
const phoneSubmitting = ref(false)
const passwordSubmitting = ref(false)

const phoneFormRef = ref()
const passwordFormRef = ref()

const phoneForm = ref({
  phone: ''
})

const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const phoneRules = {
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ]
}

const passwordRules = {
  old_password: [
    { required: true, message: '请输入旧密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.value.new_password) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const loadProfile = () => {
  const userInfo = userStore.userInfo
  if (userInfo) {
    profileForm.value = {
      username: userInfo.username,
      email: userInfo.email,
      full_name: userInfo.full_name || '-',
      phone: userInfo.phone || '未设置'
    }
  }
}

const resetPhoneForm = () => {
  phoneForm.value = {
    phone: ''
  }
  phoneFormRef.value?.resetFields()
}

const resetPasswordForm = () => {
  passwordForm.value = {
    old_password: '',
    new_password: '',
    confirm_password: ''
  }
  passwordFormRef.value?.resetFields()
}

const handlePhoneSubmit = async () => {
  if (phoneSubmitting.value) return
  
  await phoneFormRef.value?.validate()
  
  phoneSubmitting.value = true
  try {
    await updateUser(userStore.userInfo.id, {
      phone: phoneForm.value.phone
    })
    
    ElMessage.success('手机号修改成功')
    showPhoneDialog.value = false
    
    // 更新本地用户信息
    await userStore.fetchUserInfo()
    loadProfile()
  } catch (error) {
    console.error('修改失败:', error)
  } finally {
    phoneSubmitting.value = false
  }
}

const handlePasswordSubmit = async () => {
  if (passwordSubmitting.value) return
  
  await passwordFormRef.value?.validate()
  
  passwordSubmitting.value = true
  try {
    await updateUserPassword(userStore.userInfo.id, {
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password
    })
    
    ElMessage.success('密码修改成功，请重新登录')
    showPasswordDialog.value = false
    
    // 延迟后退出登录
    setTimeout(() => {
      userStore.logout()
      window.location.href = '/login'
    }, 1500)
  } catch (error) {
    console.error('修改失败:', error)
  } finally {
    passwordSubmitting.value = false
  }
}

onMounted(() => {
  loadProfile()
})
</script>

<style scoped lang="scss">
.profile {
  max-width: 800px;
  
  .profile-card,
  .password-card {
    .el-input {
      :deep(.el-input__wrapper) {
        background-color: #f5f7fa;
      }
    }
  }
}
</style>

