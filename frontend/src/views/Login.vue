<template>
  <div class="login-page">
    <div class="login-card">
      <h2>登录</h2>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="form.username" type="text" placeholder="请输入用户名" required />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="form.password" type="password" placeholder="请输入密码" required />
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
        <p class="link-row">还没有账号？<router-link to="/register">立即注册</router-link></p>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import request from '../utils/request'

const router = useRouter()
const route = useRoute()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    const res = await request.post('/auth/login', form.value)
    if (res.success) {
      localStorage.setItem('token', res.data.token.access_token)
      localStorage.setItem('user', JSON.stringify(res.data.token.user))
      const redirect = route.query.redirect || '/chat'
      router.push(redirect)
    } else {
      error.value = res.message || '登录失败'
    }
  } catch (e) {
    error.value = e.response?.data?.message || '网络错误'
  } finally {
    loading.value = false
  }
}
</script>