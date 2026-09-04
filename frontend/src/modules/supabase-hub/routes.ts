import type { RouteRecordRaw } from 'vue-router'
export const supabaseHubRoutes: RouteRecordRaw[] = [
  {
    path: '/supabase-hub',
    component: () => import('../../shared/views/ModuleStageView.vue'),
    meta: { title: 'Supabase Hub' },
    props: {
      title: 'Supabase Hub',
      description: 'Kelola koneksi project dan periksa data dari satu tempat.',
      stage: 'Tahap 4',
      features: [
        'Koneksi dinamis dengan key terenkripsi',
        'Pemeriksaan koneksi dan browser tabel',
        'Konteks koneksi terpisah per tab',
      ],
    },
  },
]
