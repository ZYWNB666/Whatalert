import request from './request'

// 获取审计日志列表
export const getAuditLogs = (params) => {
  return request({
    url: '/audit/',
    method: 'get',
    params
  })
}

// 获取审计日志详情
export const getAuditLog = (id) => {
  return request({
    url: `/audit/${id}`,
    method: 'get'
  })
}

// 获取审计日志统计
export const getAuditStats = (params) => {
  return request({
    url: '/audit/stats/summary',
    method: 'get',
    params
  })
}

