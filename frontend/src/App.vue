<template>
  <div id="app-root">
    <nav v-if="isLoggedIn && !route.meta.guest" class="nav">
      <div class="nav-brand">售后助手</div>
      <div class="nav-links">
        <router-link to="/chat">AI 对话</router-link>
        <router-link v-if="!isAdmin" to="/tickets">我的工单</router-link>
        <router-link v-if="isAdmin" to="/admin/tickets" class="nav-admin">工单管理</router-link>
      </div>
      <div class="nav-user">
        <span>{{ user?.username }}</span>
        <button class="btn-logout" @click="logout">退出</button>
      </div>
    </nav>
    <router-view />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const user = ref(null)

function safeParse(str) {
  if (!str || str === 'undefined' || str === 'null') return null
  try { return JSON.parse(str) } catch { return null }
}

function refreshUser() {
  user.value = safeParse(localStorage.getItem('user'))
}

watch(route, () => {
  refreshUser()
}, { immediate: true })

const isLoggedIn = computed(() => !!localStorage.getItem('token'))
const isAdmin = computed(() => user.value?.role === 'admin')

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}
</script>

<style scoped>
.nav {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 24px;
  background: #1f2937;
  color: #fff;
}

.nav-brand {
  font-size: 18px;
  font-weight: 700;
  margin-right: auto;
}

.nav-links {
  display: flex;
  gap: 20px;
}

.nav-links a {
  color: #d1d5db;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.15s;
}

.nav-links a:hover {
  color: #fff;
}

.nav-links a.router-link-active {
  color: #818cf8;
  font-weight: 600;
}

.nav-admin {
  color: #fbbf24 !important;
}

.nav-user {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #d1d5db;
}

.btn-logout {
  padding: 4px 12px;
  background: transparent;
  border: 1px solid #6b7280;
  border-radius: 6px;
  color: #d1d5db;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-logout:hover {
  background: #374151;
  border-color: #9ca3af;
  color: #fff;
}
</style>