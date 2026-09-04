import type { RouteRecordRaw } from 'vue-router'
export const settingsRoutes: RouteRecordRaw[] = [
  {
    path: '/settings',
    component: () => import('./views/SettingsView.vue'),
    meta: { title: 'Settings' },
  },
  {
    path: '/components',
    component: () => import('./views/ComponentsView.vue'),
    meta: { title: 'Komponen UI' },
  },
]
