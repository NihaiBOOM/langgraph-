<template>
  <div class="login-page">
    <div class="login-card">
      <h2>注册</h2>
      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="form.username" type="text" placeholder="3-20位字母数字" required />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="form.password" type="password" placeholder="至少 6 位" required />
        </div>
        <div class="form-group">
          <label>确认密码</label>
          <input v-model="form.confirmPassword" type="password" placeholder="再次输入密码" required />
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
        <div v-if="success" class="success-msg">{{ success }}</div>
        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
        <p class="link-row">已有账号？<router-link to="/login">去登录</router-link></p>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import request from '../utils/request'

const router = useRouter()
const form = ref({ username: '', password: '', confirmPassword: '' })
const loading = ref(false)
const error = ref('')
const success = ref('')

async function handleRegister() {
  if (form.value.password !== form.value.confirmPassword) {
    error.value = '两次密码不一致'
    return
  }
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    const res = await request.post('/auth/register', {
      username: form.value.username,
      password: form.value.password,
    })
    if (res.success) {
      success.value = '注册成功！即将跳转到登录页...'
      setTimeout(() => router.push('/login'), 1200)
    } else {
      error.value = res.message || '注册失败'
    }
  } catch (e) {
    error.value = e.response?.data?.message || '网络错误'
  } finally {
    loading.value = false
  }
}
</script>