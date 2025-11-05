import request from './request'

// 获取用户列表
export const getUsers = () => {
  return request({
    url: '/users/',
    method: 'get'
  })
}

// 获取用户详情
export const getUser = (id) => {
  return request({
    url: `/users/${id}`,
    method: 'get'
  })
}

// 创建用户
export const createUser = (data) => {
  return request({
    url: '/users/',
    method: 'post',
    data
  })
}

// 更新用户
export const updateUser = (id, data) => {
  return request({
    url: `/users/${id}`,
    method: 'put',
    data
  })
}

// 删除用户
export const deleteUser = (id) => {
  return request({
    url: `/users/${id}`,
    method: 'delete'
  })
}

// 修改密码
export const updateUserPassword = (id, data) => {
  return request({
    url: `/users/${id}/password`,
    method: 'post',
    data
  })
}

// 获取角色列表
export const getRoles = () => {
  return request({
    url: '/users/roles/list',
    method: 'get'
  })
}

