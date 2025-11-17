import request from './request'

// 获取静默规则列表
export const getSilenceRules = () => {
  return request({
    url: '/silence/',
    method: 'get'
  })
}

// 创建静默规则
export const createSilenceRule = (data) => {
  return request({
    url: '/silence/',
    method: 'post',
    data
  })
}

// 更新静默规则
export const updateSilenceRule = (id, data) => {
  return request({
    url: `/silence/${id}`,
    method: 'put',
    data
  })
}

// 删除静默规则
export const deleteSilenceRule = (id) => {
  return request({
    url: `/silence/${id}`,
    method: 'delete'
  })
}

// 获取被静默的告警列表
export const getSilencedAlerts = (ruleId, params = {}) => {
  return request({
    url: `/silence/${ruleId}/silenced-alerts`,
    method: 'get',
    params
  })
}
