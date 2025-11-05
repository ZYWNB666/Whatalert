import request from './request'

// 获取通知渠道列表
export const getNotificationChannels = () => {
  return request({
    url: '/notifications/',
    method: 'get'
  })
}

// 获取通知渠道详情
export const getNotificationChannel = (id) => {
  return request({
    url: `/notifications/${id}`,
    method: 'get'
  })
}

// 创建通知渠道
export const createNotificationChannel = (data) => {
  return request({
    url: '/notifications/',
    method: 'post',
    data
  })
}

// 更新通知渠道
export const updateNotificationChannel = (id, data) => {
  return request({
    url: `/notifications/${id}`,
    method: 'put',
    data
  })
}

// 删除通知渠道
export const deleteNotificationChannel = (id) => {
  return request({
    url: `/notifications/${id}`,
    method: 'delete'
  })
}

// 测试通知渠道
export const testNotificationChannel = (id) => {
  return request({
    url: `/notifications/${id}/test`,
    method: 'post'
  })
}

