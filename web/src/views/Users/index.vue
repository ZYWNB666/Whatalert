<template>
  <div class="users">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="showDialog()">
            <el-icon><Plus /></el-icon>
            添加用户
          </el-button>
        </div>
      </template>
      
      <el-table :data="users" v-loading="loading" style="width: 100%">
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="full_name" label="姓名" min-width="100" />
        <el-table-column prop="phone" label="手机号" min-width="120" />
        <el-table-column label="角色" min-width="150">
          <template #default="{ row }">
            <el-tag
              v-for="role in row.role_names"
              :key="role"
              type="success"
              size="small"
              style="margin-right: 5px"
            >
              {{ role }}
            </el-tag>
            <span v-if="!row.role_names || row.role_names.length === 0" style="color: #999">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '激活' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_superuser" label="超管" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_superuser ? 'success' : 'info'" size="small">
              {{ row.is_superuser ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDialog(row)">
              编辑
            </el-button>
            <el-button link type="warning" size="small" @click="showPasswordDialog(row)">
              改密
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 用户编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '添加用户'"
      width="600px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="isEdit" />
        </el-form-item>
        
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" />
        </el-form-item>
        
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        
        <el-form-item label="姓名" prop="full_name">
          <el-input v-model="form.full_name" />
        </el-form-item>
        
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" />
        </el-form-item>
        
        <el-form-item label="角色">
          <el-select v-model="form.role_ids" multiple placeholder="请选择角色" style="width: 100%">
            <el-option
              v-for="role in filteredRoles"
              :key="role.id"
              :label="role.name"
              :value="role.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="是否激活">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        
        <el-form-item label="超级管理员">
          <el-switch v-model="form.is_superuser" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 修改密码对话框 -->
    <el-dialog
      v-model="passwordDialogVisible"
      title="修改密码"
      width="450px"
      @closed="resetPasswordForm"
    >
      <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="100px">
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" show-password />
        </el-form-item>
        
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handlePasswordSubmit" :loading="passwordSubmitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getUsers,
  createUser,
  updateUser,
  deleteUser,
  updateUserPassword,
  getRoles
} from '@/api/users'

const loading = ref(false)
const submitting = ref(false)
const passwordSubmitting = ref(false)
const users = ref([])
const roles = ref([])
const dialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const formRef = ref()
const passwordFormRef = ref()

// 过滤掉观察者角色
const filteredRoles = computed(() => {
  return roles.value.filter(role => role.code !== 'viewer')
})

const isEdit = ref(false)
const editId = ref(null)

const form = ref({
  username: '',
  email: '',
  password: '',
  full_name: '',
  phone: '',
  is_active: true,
  is_superuser: false,
  role_ids: []
})

const passwordForm = ref({
  new_password: '',
  confirm_password: ''
})

const formRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const passwordRules = {
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

const loadUsers = async () => {
  loading.value = true
  try {
    users.value = await getUsers()
  } catch (error) {
    console.error('加载失败:', error)
  } finally {
    loading.value = false
  }
}

const loadRoles = async () => {
  try {
    roles.value = await getRoles()
  } catch (error) {
    console.error('加载角色失败:', error)
  }
}

const showDialog = (row = null) => {
  if (row) {
    isEdit.value = true
    editId.value = row.id
    form.value = {
      username: row.username,
      email: row.email,
      full_name: row.full_name,
      phone: row.phone,
      is_active: row.is_active,
      is_superuser: row.is_superuser,
      role_ids: row.roles ? row.roles.map(role => role.id) : []
    }
  } else {
    isEdit.value = false
    editId.value = null
  }
  dialogVisible.value = true
}

const showPasswordDialog = (row) => {
  editId.value = row.id
  passwordDialogVisible.value = true
}

const resetForm = () => {
  form.value = {
    username: '',
    email: '',
    password: '',
    full_name: '',
    phone: '',
    is_active: true,
    is_superuser: false,
    role_ids: []
  }
  formRef.value?.resetFields()
}

const resetPasswordForm = () => {
  passwordForm.value = {
    new_password: '',
    confirm_password: ''
  }
  passwordFormRef.value?.resetFields()
}

const handleSubmit = async () => {
  // 防止重复提交
  if (submitting.value) return
  
  await formRef.value?.validate()
  
  submitting.value = true
  try {
    if (isEdit.value) {
      await updateUser(editId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createUser(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadUsers()
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    submitting.value = false
  }
}

const handlePasswordSubmit = async () => {
  // 防止重复提交
  if (passwordSubmitting.value) return
  
  await passwordFormRef.value?.validate()
  
  passwordSubmitting.value = true
  try {
    await updateUserPassword(editId.value, {
      old_password: '',  // 管理员修改不需要旧密码
      new_password: passwordForm.value.new_password
    })
    ElMessage.success('密码修改成功')
    passwordDialogVisible.value = false
  } catch (error) {
    console.error('修改失败:', error)
  } finally {
    passwordSubmitting.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除用户 "${row.username}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteUser(row.id)
    ElMessage.success('删除成功')
    loadUsers()
  } catch (e) {
    if (e !== 'cancel') {
      console.error('删除失败:', e)
    }
  }
}

onMounted(() => {
  loadUsers()
  loadRoles()
})
</script>

<style scoped lang="scss">
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

