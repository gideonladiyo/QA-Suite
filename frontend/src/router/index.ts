import { createRouter, createWebHistory } from 'vue-router'
import { dashboardRoutes } from '../modules/dashboard/routes'
import { qaReportRoutes } from '../modules/qa-reports/routes'
import { microUtilityRoutes } from '../modules/micro-utilities/routes'
import { supabaseHubRoutes } from '../modules/supabase-hub/routes'
import { vaultRoutes } from '../modules/vault/routes'
import { settingsRoutes } from '../modules/settings/routes'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...dashboardRoutes,
    ...qaReportRoutes,
    ...microUtilityRoutes,
    ...supabaseHubRoutes,
    ...vaultRoutes,
    ...settingsRoutes,
    {
      path: '/:pathMatch(.*)*',
      component: () => import('../shared/views/NotFoundView.vue'),
      meta: { title: 'Halaman tidak ditemukan' },
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
router.afterEach((to) => {
  document.title = `${String(to.meta.title ?? 'Workspace')} · QA Portal`
})
