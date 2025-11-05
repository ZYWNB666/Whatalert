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

// 删除静默规则
export const deleteSilenceRule = (id) => {
  return request({
    url: `/silence/${id}`,
    method: 'delete'
  })
}

