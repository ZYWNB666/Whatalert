<template>
  <div class="projects-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>项目管理</span>
          <el-button v-if="userStore.isSuperuser" type="primary" @click="showCreateDialog">
            <el-icon><Plus /></el-icon>
            创建项目
          </el-button>
        </div>
      </template>

      <!-- 项目列表 -->
      <el-table :data="projects" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="项目名称" width="200">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" size="small" type="info" style="margin-right: 8px">默认</el-tag>
            {{ row.name }}
          </template>
        </el-table-column>
        <el-table-column prop="code" label="项目代码" width="150" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="你的角色" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.user_role" :type="getRoleType(row.user_role)" size="small">
              {{ getRoleLabel(row.user_role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="成员" width="100">
          <template #default="{ row }">
            {{ row.member_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="告警规则" width="120">
          <template #default="{ row }">
            {{ row.alert_rule_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '激活' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showMembers(row)">成员</el-button>
            <el-button 
              size="small" 
              @click="showEditDialog(row)"
              :disabled="row.user_role !== 'admin'"
            >
              编辑
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="handleDelete(row)"
              :disabled="row.is_default || row.user_role !== 'admin'"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑项目对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="dialogTitle"
      width="500px"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目代码" prop="code">
          <el-input 
            v-model="form.code" 
            placeholder="请输入项目代码（英文）"
            :disabled="isEdit"
          />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input 
            v-model="form.description" 
            type="textarea"
            :rows="3"
            placeholder="请输入项目描述"
          />
        </el-form-item>
        <el-form-item label="状态" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 项目成员对话框 -->
    <el-dialog 
      v-model="membersDialogVisible" 
      title="项目成员管理"
      width="750px"
    >
      <div style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
        <el-tag v-if="currentUserRole" :type="getRoleType(currentUserRole)">
          你的角色: {{ getRoleLabel(currentUserRole) }}
        </el-tag>
        <el-button 
          type="primary" 
          size="small" 
          @click="showAddMemberDialog"
          :disabled="!hasManagePermission"
        >
          <el-icon><Plus /></el-icon>
          添加成员
        </el-button>
      </div>
      
      <el-table :data="members" style="width: 100%" v-loading="membersLoading">
        <el-table-column prop="username" label="用户名" width="150">
          <template #default="{ row }">
            {{ row.username }}
            <el-tag v-if="isCurrentUser(row.user_id)" size="small" type="success" style="margin-left: 8px">
              你
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" show-overflow-tooltip />
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleType(row.role)">
              {{ getRoleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="加入时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at * 1000).toLocaleString('zh-CN') }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button 
              size="small" 
              @click="showChangeRoleDialog(row)"
              :disabled="!canManageMember(row.role) || isCurrentUser(row.user_id)"
            >
              修改角色
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="handleRemoveMember(row)"
              :disabled="!canManageMember(row.role) || isCurrentUser(row.user_id)"
            >
              移除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 添加成员对话框 -->
    <el-dialog 
      v-model="addMemberDialogVisible" 
      title="添加项目成员"
      width="500px"
    >
      <el-form 
        :model="addMemberForm" 
        :rules="addMemberRules" 
        ref="addMemberFormRef" 
        label-width="80px"
      >
        <el-form-item label="选择用户" prop="user_id">
          <el-select 
            v-model="addMemberForm.user_id" 
            placeholder="请选择用户"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="user in availableUsers"
              :key="user.id"
              :label="`${user.username} (${user.email || '无邮箱'})`"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="addMemberForm.role" style="width: 100%">
            <el-option
              v-for="role in getAvailableRoles"
              :key="role.value"
              :label="role.label"
              :value="role.value"
            />
          </el-select>
          <div style="margin-top: 8px; font-size: 12px; color: #909399;">
            <div>• <strong>查看者</strong>：只能查看项目内容，无修改权限（只读）</div>
            <div>• <strong>维护者</strong>：可以创建和修改告警规则、数据源等（增改查）</div>
            <div>• <strong>管理员</strong>：拥有所有权限，包括删除和管理成员（增删改查）</div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addMemberDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddMember">确定</el-button>
      </template>
    </el-dialog>

    <!-- 修改角色对话框 -->
    <el-dialog 
      v-model="changeRoleDialogVisible" 
      title="修改成员角色"
      width="400px"
    >
      <el-form 
        :model="changeRoleForm" 
        :rules="changeRoleRules" 
        ref="changeRoleFormRef" 
        label-width="80px"
      >
        <el-form-item label="用户">
          <el-text>{{ currentMember?.username }}</el-text>
        </el-form-item>
        <el-form-item label="当前角色">
          <el-tag :type="getRoleType(currentMember?.role)">
            {{ getRoleLabel(currentMember?.role) }}
          </el-tag>
        </el-form-item>
        <el-form-item label="新角色" prop="role">
          <el-select v-model="changeRoleForm.role" style="width: 100%">
            <el-option
              v-for="role in getAvailableRoles"
              :key="role.value"
              :label="role.label"
              :value="role.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changeRoleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleChangeRole">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { 
  getProjects, 
  createProject, 
  updateProject, 
  deleteProject,
  getProjectMembers,
  addProjectMember,
  updateProjectMemberRole,
  removeProjectMember
} from '@/api/projects'
import { getUsers } from '@/api/users'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const loading = ref(false)
const projects = ref([])
const dialogVisible = ref(false)
const membersDialogVisible = ref(false)
const isEdit = ref(false)
const dialogTitle = ref('创建项目')
const formRef = ref(null)
const members = ref([])
const membersLoading = ref(false)
const currentProject = ref(null)
const currentUserRole = ref(null)  // 当前用户在项目中的角色

// 添加成员相关
const addMemberDialogVisible = ref(false)
const addMemberFormRef = ref(null)
const availableUsers = ref([])
const addMemberForm = ref({
  user_id: null,
  role: 'member'
})

// 修改角色相关
const changeRoleDialogVisible = ref(false)
const changeRoleFormRef = ref(null)
const currentMember = ref(null)
const changeRoleForm = ref({
  role: 'member'
})

const form = ref({
  name: '',
  code: '',
  description: '',
  is_active: true,
  settings: {}
})

const rules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  code: [
    { required: true, message: '请输入项目代码', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_-]+$/, message: '只能包含字母、数字、下划线和短横线', trigger: 'blur' }
  ]
}

const addMemberRules = {
  user_id: [{ required: true, message: '请选择用户', trigger: 'change' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

const changeRoleRules = {
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

onMounted(() => {
  fetchProjects()
})

const fetchProjects = async () => {
  loading.value = true
  try {
    const res = await getProjects()
    projects.value = res.projects || []
  } catch (error) {
    ElMessage.error('获取项目列表失败')
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  dialogTitle.value = '创建项目'
  form.value = {
    name: '',
    code: '',
    description: '',
    is_active: true,
    settings: {}
  }
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  isEdit.value = true
  dialogTitle.value = '编辑项目'
  form.value = { ...row }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    try {
      if (isEdit.value) {
        await updateProject(form.value.id, form.value)
        ElMessage.success('项目更新成功')
      } else {
        await createProject(form.value)
        ElMessage.success('项目创建成功')
      }
      dialogVisible.value = false
      fetchProjects()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  })
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除项目 "${row.name}" 吗？删除后将无法恢复。`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await deleteProject(row.id)
    ElMessage.success('项目已删除')
    fetchProjects()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const showMembers = async (row) => {
  currentProject.value = row
  membersDialogVisible.value = true
  await fetchMembers(row.id)
}

const fetchMembers = async (projectId) => {
  membersLoading.value = true
  try {
    members.value = await getProjectMembers(projectId)
    
    // 获取当前用户在项目中的角色
    const userStore = useUserStore()
    const currentUserId = userStore.userInfo?.id
    const currentMemberInfo = members.value.find(m => m.user_id === currentUserId)
    currentUserRole.value = currentMemberInfo?.role || null
  } catch (error) {
    ElMessage.error('获取成员列表失败')
  } finally {
    membersLoading.value = false
  }
}

const handleRemoveMember = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要移除成员 "${row.username}" 吗？`,
      '确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await removeProjectMember(currentProject.value.id, row.user_id)
    ElMessage.success('成员已移除')
    fetchMembers(currentProject.value.id)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('移除失败')
    }
  }
}

const getRoleType = (role) => {
  const types = {
    admin: 'danger',
    maintainer: 'warning',
    viewer: 'info'
  }
  return types[role] || 'info'
}

const getRoleLabel = (role) => {
  const labels = {
    admin: '管理员',
    maintainer: '维护者',
    viewer: '查看者'
  }
  return labels[role] || role
}

// 检查是否有管理权限（只有 admin）
const hasManagePermission = computed(() => {
  return currentUserRole.value === 'admin'
})

// 检查是否可以操作目标成员
const canManageMember = (targetRole) => {
  // 只有管理员可以管理成员
  return currentUserRole.value === 'admin'
}

// 检查当前用户
const isCurrentUser = (userId) => {
  const userStore = useUserStore()
  return userStore.userInfo?.id === userId
}

const showAddMemberDialog = async () => {
  try {
    // 获取所有用户列表
    const res = await getUsers()
    // 后端直接返回数组，不是对象
    const allUsers = Array.isArray(res) ? res : (res.users || [])
    // 过滤掉已经是成员的用户
    const memberUserIds = members.value.map(m => m.user_id)
    availableUsers.value = allUsers.filter(u => !memberUserIds.includes(u.id))
    
    if (availableUsers.value.length === 0) {
      ElMessage.warning('没有可添加的用户')
      return
    }
    
    // 默认角色为查看者
    addMemberForm.value = {
      user_id: null,
      role: 'viewer'
    }
    addMemberDialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取用户列表失败')
  }
}

// 获取可选角色列表
const getAvailableRoles = computed(() => {
  // 只有管理员可以添加成员
  if (currentUserRole.value === 'admin') {
    return [
      { label: '查看者 (只读)', value: 'viewer' },
      { label: '维护者 (增改查)', value: 'maintainer' },
      { label: '管理员 (增删改查)', value: 'admin' }
    ]
  }
  // 其他角色不应该有添加权限
  return []
})

const handleAddMember = async () => {
  if (!addMemberFormRef.value) return
  
  await addMemberFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    try {
      await addProjectMember(currentProject.value.id, addMemberForm.value)
      ElMessage.success('成员添加成功')
      addMemberDialogVisible.value = false
      fetchMembers(currentProject.value.id)
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '添加失败')
    }
  })
}

const showChangeRoleDialog = (row) => {
  currentMember.value = row
  changeRoleForm.value = {
    role: row.role
  }
  changeRoleDialogVisible.value = true
}

const handleChangeRole = async () => {
  if (!changeRoleFormRef.value) return
  
  await changeRoleFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    try {
      await updateProjectMemberRole(
        currentProject.value.id, 
        currentMember.value.user_id, 
        changeRoleForm.value
      )
      ElMessage.success('角色修改成功')
      changeRoleDialogVisible.value = false
      fetchMembers(currentProject.value.id)
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '修改失败')
    }
  })
}
</script>

<style scoped>
.projects-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
