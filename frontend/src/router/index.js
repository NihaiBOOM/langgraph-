import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/login', component: () => import('../views/Login.vue'), meta: { guest: true } },
  { path: '/register', component: () => import('../views/Register.vue'), meta: { guest: true } },
  { path: '/chat', component: () => import('../views/Chat.vue'), meta: { auth: true } },
  { path: '/tickets', component: () => import('../views/TicketList.vue'), meta: { auth: true } },
  { path: '/tickets/:id', component: () => import('../views/TicketDetail.vue'), meta: { auth: true } },
  { path: '/admin/tickets', component: () => import('../views/AdminTicketList.vue'), meta: { auth: true, admin: true } },
  { path: '/admin/tickets/:id', component: () => import('../views/AdminTicketDetail.vue'), meta: { auth: true, admin: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function getRole() {
  try {
    const u = JSON.parse(localStorage.getItem('user') || 'null')
    return u?.role || null
  } catch { return null }
}

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  const isAdmin = getRole() === 'admin'

  if (to.meta.guest && token) {
    return '/chat'
  }

  if (to.meta.auth && !token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.meta.admin) {
    if (!isAdmin) return '/chat'
  } else if (to.path.startsWith('/tickets')) {
    if (isAdmin) return '/admin/tickets'
  }

  return true
})

export default router