<template>
  <div class="page">
    <div class="page-header">
      <h2>工单管理</h2>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else-if="tickets.length === 0" class="empty">暂无工单</div>
    <table v-else class="admin-table">
      <thead>
        <tr>
          <th>工单编号</th>
          <th>用户</th>
          <th>售后类型</th>
          <th>风险</th>
          <th>状态</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in tickets" :key="t.id">
          <td>{{ t.ticket_no }}</td>
          <td>{{ t.username || '用户#' + t.user_id }}</td>
          <td>{{ afterSalesLabel(t.after_sales_type) }}</td>
          <td>
            <span :class="['risk-tag', t.risk_level === 'high' ? 'risk-high' : 'risk-low']">
              {{ t.risk_level === 'high' ? '高' : '低' }}
            </span>
          </td>
          <td><span :class="['status-badge', `status-${t.status}`]">{{ statusLabel(t.status) }}</span></td>
          <td>{{ formatTime(t.created_at) }}</td>
          <td><button class="btn-link" @click="$router.push(`/admin/tickets/${t.id}`)">查看详情</button></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '../utils/request'

const tickets = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await request.get('/tickets?all=true')
    tickets.value = res.data || []
  } catch (e) {
    error.value = e.response?.data?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function statusLabel(s) {
  return { pending: '待处理', pending_review: '待审核', completed: '已完成', rejected: '已拒绝' }[s] || s
}
function afterSalesLabel(t) {
  return { refund_only: '仅退款', return_refund: '退货退款', exchange: '换货' }[t] || t
}
function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

onMounted(load)
</script>