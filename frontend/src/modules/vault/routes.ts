import type { RouteRecordRaw } from 'vue-router'
export const vaultRoutes: RouteRecordRaw[] = [
  {
    path: '/vault',
    component: () => import('./views/VaultView.vue'),
    meta: { title: 'Vault' },
  },
]
