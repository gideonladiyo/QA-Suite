import type { RouteRecordRaw } from 'vue-router'
export const microUtilityRoutes: RouteRecordRaw[] = [
  { path: '/micro-utilities', redirect: '/micro-utilities/http-client' },
  {
    path: '/micro-utilities/http-client',
    component: () => import('./views/HttpClientView.vue'),
    meta: { title: 'HTTP Client' },
  },
  {
    path: '/micro-utilities/json',
    component: () => import('./views/JsonView.vue'),
    meta: { title: 'JSONizer' },
  },
  {
    path: '/micro-utilities/dummy-data',
    component: () => import('./views/DummyDataView.vue'),
    meta: { title: 'Dummy Data' },
  },
  {
    path: '/micro-utilities/base64-jwt',
    component: () => import('./views/EncodingView.vue'),
    meta: { title: 'Base64 / JWT' },
  },
]
