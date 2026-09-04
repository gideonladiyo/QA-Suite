import type { RouteRecordRaw } from 'vue-router'
export const dashboardRoutes: RouteRecordRaw[] = [
  { path: '/', component: () => import('./views/DashboardView.vue'), meta: { title: 'Dashboard' } },
]
