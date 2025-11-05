import request from './request'

// 获取数据源列表
export const getDatasources = () => {
  return request({
    url: '/datasources/',
    method: 'get'
  })
}

// 获取数据源详情
export const getDatasource = (id) => {
  return request({
    url: `/datasources/${id}`,
    method: 'get'
  })
}

// 创建数据源
export const createDatasource = (data) => {
  return request({
    url: '/datasources/',
    method: 'post',
    data
  })
}

// 更新数据源
export const updateDatasource = (id, data) => {
  return request({
    url: `/datasources/${id}`,
    method: 'put',
    data
  })
}

// 删除数据源
export const deleteDatasource = (id) => {
  return request({
    url: `/datasources/${id}`,
    method: 'delete'
  })
}

// 测试数据源连接
export const testDatasource = (id) => {
  return request({
    url: `/datasources/${id}/test`,
    method: 'post'
  })
}

