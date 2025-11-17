import request from './request'

// 获取告警规则列表
export const getAlertRules = (params) => {
  return request({
    url: '/alert-rules/',
    method: 'get',
    params
  })
}

// 获取告警规则详情
export const getAlertRule = (id) => {
  return request({
    url: `/alert-rules/${id}`,
    method: 'get'
  })
}

// 创建告警规则
export const createAlertRule = (data) => {
  return request({
    url: '/alert-rules/',
    method: 'post',
    data
  })
}

// 更新告警规则
export const updateAlertRule = (id, data) => {
  return request({
    url: `/alert-rules/${id}`,
    method: 'put',
    data
  })
}

// 删除告警规则
export const deleteAlertRule = (id) => {
  return request({
    url: `/alert-rules/${id}`,
    method: 'delete'
  })
}

// 获取当前告警
export const getCurrentAlerts = (params) => {
  return request({
    url: '/alert-rules/events/current',
    method: 'get',
    params
  })
}

// 获取历史告警
export const getAlertHistory = (params) => {
  return request({
    url: '/alert-rules/events/history',
    method: 'get',
    params
  })
}

// 测试告警规则
export const testAlertRule = (data) => {
  return request({
    url: '/alert-rules/test',
    method: 'post',
    data
  })
}

