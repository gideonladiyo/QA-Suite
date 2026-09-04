import type { RouteRecordRaw } from 'vue-router'
export const vaultRoutes: RouteRecordRaw[] = [
  {
    path: '/vault',
    component: () => import('../../shared/views/ModuleStageView.vue'),
    meta: { title: 'Vault' },
    props: {
      title: 'Vault',
      description: 'Tempat lokal untuk menyimpan kredensial development dan testing.',
      stage: 'Tahap 5',
      features: [
        'Master lock dan enkripsi per sesi',
        'Reveal, copy, dan auto-lock',
        'Pencarian metadata dan audit akses',
      ],
      securityNotice:
        'Vault belum tersedia. Jangan masukkan kredensial sampai modul keamanan selesai diimplementasikan.',
    },
  },
]
