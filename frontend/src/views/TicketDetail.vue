<template>
  <div class="page" v-if="ticket">
    <div class="page-header">
      <button class="btn-back" @click="$router.back()">← 返回</button>
      <h2>工单详情</h2>
    </div>

    <div class="detail-card">
      <div class="detail-header">
        <span class="ticket-no">{{ ticket.ticket_no }}</span>
        <span :class="['status-badge', `status-${ticket.status}`]">{{ statusLabel(ticket.status) }}</span>
      </div>

      <div class="detail-section">
        <h4>售后信息</h4>
        <div class="detail-row"><span class="label">售后类型</span><span>{{ afterSalesLabel(ticket.after_sales_type) }}</span></div>
        <div class="detail-row"><span class="label">风险等级</span><span>{{ riskLabel(ticket.risk_level) }}</span></div>
        <div class="detail-row"><span class="label">创建时间</span><span>{{ formatTime(ticket.created_at) }}</span></div>
      </div>

      <div v-if="ticket.order" class="detail-section">
        <h4>订单商品</h4>
        <div class="order-product">
          <div class="product-info">
            <div class="product-name">{{ ticket.order.product_name }}</div>
            <div class="product-meta">
              <span>¥{{ ticket.order.unit_price?.toFixed(2) }} × {{ ticket.order.quantity }}</span>
              <span class="total">小计: ¥{{ ticket.order.total_amount?.toFixed(2) }}</span>
            </div>
            <div class="product-meta">
              <span>订单号: {{ ticket.order.order_no }}</span>
              <span>下单: {{ formatTime(ticket.order.purchased_at) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <h4>申请原因</h4>
        <p class="reason-text">{{ ticket.reason }}</p>
      </div>

      <div v-if="ticket.resolution" class="detail-section">
        <h4>处理结果</h4>
        <p class="reason-text">{{ ticket.resolution }}</p>
      </div>
    </div>

    <div class="detail-card">
      <h4>操作日志</h4>
      <div v-if="logsLoading" class="loading">加载中...</div>
      <div v-else-if="logs.length === 0" class="empty">暂无日志</div>
      <div v-else class="log-list">
        <div v-for="log in logs" :key="log.id" class="log-item">
          <span class="log-action">{{ log.action }}</span>
          <span class="log-msg">{{ log.message }}</span>
          <span class="log-time">{{ formatTime(log.created_at) }}</span>
        </div>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="loading">加载中...</div>
  <div v-else class="empty">工单不存在或无权查看</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import request from '../utils/request'

const route = useRoute()
const ticket = ref(null)
const logs = ref([])
const loading = ref(true)
const logsLoading = ref(false)

async function loadDetail() {
  loading.value = true
  try {
    const res = await request.get(`/tickets/${route.params.id}`)
    ticket.value = res.data
  } catch {
    ticket.value = null
  } finally {
    loading.value = false
  }
}

async function loadLogs() {
  logsLoading.value = true
  try {
    const res = await request.get(`/tickets/${route.params.id}/logs`)
    logs.value = res.data || []
  } catch {}
  logsLoading.value = false
}

function statusLabel(s) {
  return { pending: '待处理', pending_review: '待审核', completed: '已完成', rejected: '已拒绝' }[s] || s
}
function afterSalesLabel(t) {
  return { refund_only: '仅退款', return_refund: '退货退款', exchange: '换货' }[t] || t
}
function riskLabel(r) {
  return r === 'high' ? '高风险' : '低风险'
}
function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

onMounted(() => {
  loadDetail()
  loadLogs()
})
</script>