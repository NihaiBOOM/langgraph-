<template>
  <div class="page">
    <div class="page-header">
      <h2>我的工单</h2>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else-if="tickets.length === 0" class="empty">
      <p>还没有工单</p>
      <router-link to="/chat" class="btn-primary">去 AI 对话申请售后</router-link>
    </div>
    <div v-else class="ticket-list">
      <div v-for="t in tickets" :key="t.id" class="ticket-item" @click="goDetail(t.id)">
        <div class="ticket-top">
          <span class="ticket-no">{{ t.ticket_no }}</span>
          <span :class="['status-badge', `status-${t.status}`]">{{ statusLabel(t.status) }}</span>
        </div>
        <div class="ticket-body">
          <div class="ticket-reason">{{ t.reason }}</div>
          <div class="ticket-meta">
            <span>{{ afterSalesLabel(t.after_sales_type) }}</span>
            <span>{{ formatTime(t.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../utils/request'

const router = useRouter()
const tickets = ref([])
const loading = ref(false)
const error = ref('')

async function loadTickets() {
  loading.value = true
  error.value = ''
  try {
    const res = await request.get('/tickets')
    tickets.value = res.data || []
  } catch (e) {
    error.value = e.response?.data?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function goDetail(id) { router.push(`/tickets/${id}`) }

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

onMounted(loadTickets)
</script>