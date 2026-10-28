<template>
  <div class="page" v-if="ticket">
    <div class="page-header">
      <button class="btn-back" @click="$router.back()">← 返回</button>
      <h2>工单审核</h2>
    </div>

    <div class="detail-card">
      <div class="detail-header">
        <span class="ticket-no">{{ ticket.ticket_no }}</span>
        <span :class="['status-badge', `status-${ticket.status}`]">{{ statusLabel(ticket.status) }}</span>
      </div>

      <div class="detail-section">
        <h4>申请人</h4>
        <div class="detail-row"><span class="label">用户</span><span>{{ ticket.username || '用户#' + ticket.user_id }}</span></div>
        <div class="detail-row"><span class="label">关联订单</span><span>订单 #{{ ticket.order_id }}</span></div>
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
        <h4>售后信息</h4>
        <div class="detail-row"><span class="label">售后类型</span><span>{{ afterSalesLabel(ticket.after_sales_type) }}</span></div>
        <div class="detail-row"><span class="label">风险等级</span><span>{{ riskLabel(ticket.risk_level) }}</span></div>
        <div class="detail-row"><span class="label">创建时间</span><span>{{ formatTime(ticket.created_at) }}</span></div>
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

    <div v-if="ticket.status === 'pending' || ticket.status === 'pending_review'" class="detail-card">
      <h4>审核操作</h4>
      <div class="form-group">
        <label>处理说明</label>
        <textarea v-model="resolution" rows="3" placeholder="请输入处理说明..." required></textarea>
      </div>
      <div class="modal-actions">
        <button class="btn-danger" @click="handleReject" :disabled="acting">拒绝工单</button>
        <button class="btn-primary" @click="handleApprove" :disabled="acting">通过工单</button>
      </div>
    </div>

    <div class="detail-card">
      <h4>操作日志</h4>
      <div class="log-list">
        <div v-for="log in logs" :key="log.id" class="log-item">
          <span class="log-action">{{ log.action }}</span>
          <span class="log-msg">{{ log.message }}</span>
          <span class="log-time">{{ formatTime(log.created_at) }}</span>
        </div>
        <div v-if="logs.length === 0" class="empty">暂无日志</div>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="loading">加载中...</div>
  <div v-else class="empty">工单不存在</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import request from '../utils/request'

const route = useRoute()
const ticket = ref(null)
const logs = ref([])
const loading = ref(true)
const resolution = ref('')
const acting = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await request.get(`/tickets/${route.params.id}?as_admin=true`)
    ticket.value = res.data
  } catch {
    ticket.value = null
  } finally {
    loading.value = false
  }
}

async function loadLogs() {
  try {
    const res = await request.get(`/tickets/${route.params.id}/logs`)
    logs.value = res.data || []
  } catch {}
}

async function handleApprove() {
  if (!resolution.value) { alert('请填写处理说明'); return }
  acting.value = true
  try {
    await request.post(`/tickets/${route.params.id}/review`, { decision: 'approve', resolution: resolution.value })
    resolution.value = ''
    await load()
    await loadLogs()
  } catch (e) {
    alert(e.response?.data?.message || '操作失败')
  } finally {
    acting.value = false
  }
}

async function handleReject() {
  if (!resolution.value) { alert('请填写拒绝原因'); return }
  acting.value = true
  try {
    await request.post(`/tickets/${route.params.id}/review`, { decision: 'reject', resolution: resolution.value })
    resolution.value = ''
    await load()
    await loadLogs()
  } catch (e) {
    alert(e.response?.data?.message || '操作失败')
  } finally {
    acting.value = false
  }
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

onMounted(() => { load(); loadLogs() })
</script>