import type { RouteRecordRaw } from 'vue-router'

export const photoEditorRoutes: RouteRecordRaw[] = [
  {
    path: '/photo-editor',
    component: () => import('./views/PhotoEditorView.vue'),
    meta: { title: 'Photo Editor', layout: 'editor' },
  },
]
