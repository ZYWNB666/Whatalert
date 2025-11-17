// 项目管理 API
import request from './request'

/**
 * 获取项目列表
 */
export function getProjects(params = {}) {
  return request({
    url: '/projects',
    method: 'get',
    params
  })
}

/**
 * 获取项目详情
 */
export function getProject(id) {
  return request({
    url: `/projects/${id}`,
    method: 'get'
  })
}

/**
 * 创建项目
 */
export function createProject(data) {
  return request({
    url: '/projects',
    method: 'post',
    data
  })
}

/**
 * 更新项目
 */
export function updateProject(id, data) {
  return request({
    url: `/projects/${id}`,
    method: 'put',
    data
  })
}

/**
 * 删除项目
 */
export function deleteProject(id) {
  return request({
    url: `/projects/${id}`,
    method: 'delete'
  })
}

/**
 * 获取项目成员列表
 */
export function getProjectMembers(projectId) {
  return request({
    url: `/projects/${projectId}/members`,
    method: 'get'
  })
}

/**
 * 添加项目成员
 */
export function addProjectMember(projectId, data) {
  return request({
    url: `/projects/${projectId}/members`,
    method: 'post',
    data
  })
}

/**
 * 更新项目成员角色
 */
export function updateProjectMemberRole(projectId, userId, data) {
  return request({
    url: `/projects/${projectId}/members/${userId}`,
    method: 'put',
    data
  })
}

/**
 * 移除项目成员
 */
export function removeProjectMember(projectId, userId) {
  return request({
    url: `/projects/${projectId}/members/${userId}`,
    method: 'delete'
  })
}
