<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  PhArrowUpRight,
  PhArrowRight,
  PhClipboardText,
  PhDatabase,
  PhLockKey,
  PhStack,
  PhCheck,
} from '@phosphor-icons/vue'
import UiCard from '../../../shared/components/ui/UiCard.vue'
import UiBadge from '../../../shared/components/ui/UiBadge.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import { toolNavigation } from '../../../shared/navigation'
import { useUiStore } from '../../../shared/stores/ui'
import { localDate, qaApi, statusLabel, type ReportSummary } from '../../qa-reports/api'
import { errorMessage } from '../../../shared/api'
import UiErrorState from '../../../shared/components/ui/UiErrorState.vue'
const todayReport = ref<ReportSummary>()
const reportLoading = ref(true)
const reportError = ref('')
async function loadReport(): Promise<void> {
  reportLoading.value = true
  reportError.value = ''
  try {
    const date = localDate()
    todayReport.value = (await qaApi.list({ start: date, end: date })).reports[0]
  } catch (cause) {
    reportError.value = errorMessage(cause)
  } finally {
    reportLoading.value = false
  }
}
const ui = useUiStore()
const now = ref(new Date())
const date = computed(() =>
  new Intl.DateTimeFormat('id-ID', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(now.value),
)
let timer: ReturnType<typeof setInterval>
onMounted(() => {
  void loadReport()
  timer = setInterval(() => {
    const previousDate = localDate(now.value)
    now.value = new Date()
    if (previousDate !== localDate(now.value)) void loadReport()
  }, 60_000)
})
onUnmounted(() => clearInterval(timer))
const tools = [
  { ...toolNavigation[0]!, description: 'Kirim request, periksa respons API.' },
  { ...toolNavigation[1]!, description: 'Format dan validasi payload JSON.' },
  { ...toolNavigation[2]!, description: 'Susun data uji dari schema pilihanmu.' },
  { ...toolNavigation[3]!, description: 'Lihat isi encoding dan claim token.' },
]
</script>
<template>
  <div class="page-header">
    <div>
      <p class="greeting">SATU WORKSPACE, LEBIH TERATUR</p>
      <h1>Selamat datang kembali.</h1>
      <p>Ruang untuk laporan QA, alat developer, dan koneksi project-mu.</p>
    </div>
    <time
      class="today"
      :datetime="now.toISOString()"
    >
      {{ date }}
    </time>
  </div>
  <div class="dashboard-grid">
    <div class="main-column">
      <UiCard
        class="report-panel"
        padding="none"
      >
        <div class="report-heading">
          <div class="cluster">
            <PhClipboardText :size="22" />
            <h2>Laporan QA hari ini</h2>
          </div>
          <UiBadge>
            {{
              reportLoading
                ? 'Memuat'
                : reportError
                  ? 'Tidak tersedia'
                  : todayReport
                    ? statusLabel(todayReport.status)
                    : 'Belum dibuat'
            }}
          </UiBadge>
        </div>
        <div class="report-content">
          <div
            class="report-symbol"
            aria-hidden="true"
          >
            <PhClipboardText
              :size="52"
              weight="duotone"
            />
          </div>
          <UiErrorState
            v-if="reportError"
            :message="reportError"
            retryable
            @retry="loadReport"
          />
          <h3 v-else>
            {{
              todayReport
                ? `${todayReport.item_count} aktivitas tercatat hari ini.`
                : 'Mulai dari pengujian pertama.'
            }}
          </h3>
          <p>
            Catat aktivitas per tiket, tambahkan hasil pengujian, lalu susun laporan harian dari
            satu tempat.
          </p>
          <RouterLink
            :to="todayReport ? `/qa-reports/${todayReport.id}?edit=1` : '/qa-reports/new'"
            class="report-link"
          >
            {{ todayReport ? 'Buka laporan hari ini' : 'Input laporan harian' }}
            <PhArrowRight :size="17" />
          </RouterLink>
        </div>
        <div class="report-footer">
          <span>Aktivitas harian</span>
          <span>Preview laporan</span>
          <span>Riwayat pengujian</span>
        </div>
      </UiCard>
      <section
        class="tools-section"
        aria-labelledby="tools-title"
      >
        <div class="section-heading">
          <div>
            <h2 id="tools-title">Alat untuk pekerjaan kecil.</h2>
            <p>Empat utilitas yang akan hadir di workspace.</p>
          </div>
          <span class="small muted">4 alat siap dipakai</span>
        </div>
        <div class="tools-list">
          <RouterLink
            v-for="tool in tools"
            :key="tool.path"
            :to="tool.path"
            class="tool-row"
          >
            <span class="tool-icon">
              <component
                :is="tool.icon"
                :size="23"
                weight="duotone"
              />
            </span>
            <span class="tool-copy">
              <strong>{{ tool.label }}</strong>
              <span>{{ tool.description }}</span>
            </span>
            <PhArrowUpRight
              :size="18"
              class="muted"
            />
          </RouterLink>
        </div>
      </section>
    </div>
    <div class="side-column">
      <UiCard
        padding="md"
        class="context-card"
      >
        <template #header>
          <div class="section-heading">
            <PhDatabase
              :size="24"
              weight="duotone"
            />
            <UiBadge>Belum terhubung</UiBadge>
          </div>
        </template>
        <h3>Konteks project</h3>
        <p>
          Koneksi Supabase akan tampil di sini, supaya kamu selalu tahu project yang sedang
          digunakan.
        </p>
        <RouterLink
          to="/supabase-hub"
          class="text-link"
        >
          Buka Supabase Hub
          <PhArrowRight :size="15" />
        </RouterLink>
      </UiCard>
      <UiCard
        padding="md"
        tone="outlined"
        class="context-card"
      >
        <template #header>
          <div class="section-heading">
            <PhLockKey
              :size="24"
              weight="duotone"
            />
            <UiBadge>Belum disiapkan</UiBadge>
          </div>
        </template>
        <h3>Ruang untuk secret-mu</h3>
        <p>
          Master lock, enkripsi, dan akses per sesi akan disiapkan sebelum Vault bisa digunakan.
        </p>
        <RouterLink
          to="/vault"
          class="text-link"
        >
          Tentang Vault
          <PhArrowRight :size="15" />
        </RouterLink>
      </UiCard>
      <div class="shortcut-note">
        <span class="shortcut-keys">
          <kbd>Ctrl</kbd>
          <span>+</span>
          <kbd>K</kbd>
        </span>
        <p>
          Lebih sedikit klik.
          <br />
          Langsung ke alat yang kamu cari.
        </p>
        <UiButton
          variant="ghost"
          size="sm"
          @click="ui.paletteOpen = true"
        >
          Coba pencarian
          <PhArrowUpRight :size="14" />
        </UiButton>
      </div>
    </div>
  </div>
  <section class="foundation-strip">
    <div class="foundation-icon">
      <PhStack
        :size="24"
        weight="duotone"
      />
    </div>
    <div class="foundation-copy">
      <h3>Fondasi antarmuka sudah tersedia.</h3>
      <p>
        Button, card, form, dialog, dan tabel menggunakan komponen yang sama di seluruh workspace.
      </p>
    </div>
    <RouterLink
      to="/components"
      class="text-link"
    >
      Jelajahi komponen
      <PhArrowRight :size="16" />
    </RouterLink>
  </section>
  <footer class="dashboard-footer">
    <span>
      <PhCheck :size="14" />
      Font dan aset disajikan lokal
    </span>
    <span>Dibangun satu tahap setiap kali.</span>
  </footer>
</template>
<style scoped>
.page-header .greeting {
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--color-secondary);
  font-weight: 600;
  margin: 0 0 12px;
}
.today {
  font-size: 12px;
  color: var(--color-text-muted);
  padding-top: 29px;
  white-space: nowrap;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.75fr) minmax(270px, 1fr);
  gap: 28px;
}
.main-column,
.side-column {
  min-width: 0;
}
.report-panel {
  overflow: hidden;
  border-color: transparent;
  background: var(--color-brand-panel);
  color: var(--color-brand-text);
}
.report-heading {
  padding: 22px 26px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid color-mix(in srgb, var(--color-secondary) 17%, transparent);
}
.report-heading h2 {
  font-size: 16px;
}
.report-content {
  padding: 30px 30px 32px;
}
.report-symbol {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 78px;
  height: 78px;
  border-radius: 16px;
  background: var(--color-blush);
  color: var(--color-on-blush);
  margin-bottom: 21px;
}
.report-content h3 {
  font-size: 22px;
  font-weight: 500;
  letter-spacing: -0.5px;
}
.report-content p {
  color: var(--color-brand-muted);
  margin: 10px 0 22px;
  font-size: 14px;
  max-width: 42ch;
  line-height: 1.7;
}
.report-link {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  font-weight: 500;
  padding-bottom: 3px;
  border-bottom: 1px solid var(--color-secondary);
}
.report-link:hover {
  opacity: 0.8;
}
.report-footer {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 17px 26px;
  border-top: 1px solid color-mix(in srgb, var(--color-secondary) 17%, transparent);
  font-size: 11px;
  color: var(--color-brand-muted);
}
.side-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.context-card {
  flex: 0;
}
.context-card :deep(.card-header) {
  margin-bottom: 17px;
}
.context-card .section-heading {
  margin-bottom: 0;
  color: var(--color-secondary);
}
.context-card p {
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.65;
  margin: 10px 0 20px;
}
.context-card .text-link {
  font-size: 12px;
}
.shortcut-note {
  padding: 6px 24px 0;
}
.shortcut-keys {
  display: flex;
  gap: 5px;
  align-items: center;
  color: var(--color-text-muted);
  font-size: 12px;
}
.shortcut-keys kbd {
  padding: 3px 7px;
  background: var(--color-surface);
}
.shortcut-note p {
  color: var(--color-text-muted);
  font-size: 13px;
  margin: 12px 0 8px;
  line-height: 1.7;
}
.shortcut-note :deep(button) {
  padding-left: 0;
}
.tools-section {
  margin-top: 32px;
}
.tools-section h2 {
  font-size: 18px;
}
.tools-section .section-heading p {
  font-size: 13px;
}
.tools-list {
  display: grid;
}
.tool-row {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 79px;
  border-bottom: 1px solid var(--color-border);
  padding: 15px 0;
}
.tool-row:last-child {
  border-bottom: 0;
}
.tool-row:hover .tool-copy strong {
  color: var(--color-primary);
}
.tool-icon {
  display: flex;
  padding: 11px;
  background: var(--color-surface-subtle);
  color: var(--color-primary);
  border-radius: 10px;
}
.tool-copy {
  flex: 1;
}
.tool-copy strong {
  display: block;
  font-weight: 500;
  font-size: 14px;
}
.tool-copy > span {
  display: block;
  color: var(--color-text-muted);
  font-size: 12px;
  margin-top: 4px;
}
.foundation-strip {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 23px 0;
  margin-top: 32px;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}
.foundation-icon {
  color: var(--color-secondary);
}
.foundation-copy {
  flex: 1;
}
.foundation-copy h3 {
  font-size: 14px;
  font-weight: 500;
}
.foundation-copy p {
  margin-top: 5px;
  font-size: 12px;
  color: var(--color-text-muted);
}
.foundation-strip .text-link {
  font-size: 12px;
}
.dashboard-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 20px;
  color: var(--color-text-muted);
  font-size: 11px;
}
.dashboard-footer > span {
  display: flex;
  align-items: center;
  gap: 6px;
}
@media (max-width: 1150px) {
  .today {
    display: none;
  }
  .dashboard-grid {
    grid-template-columns: minmax(0, 1.5fr) minmax(240px, 1fr);
    gap: 20px;
  }
  .report-heading {
    padding: 20px;
  }
  .report-heading .cluster {
    gap: 8px;
  }
  .report-heading h2 {
    font-size: 14px;
  }
  .foundation-strip {
    flex-wrap: wrap;
  }
}
@media (max-width: 950px) {
  .dashboard-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .side-column {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-top: 10px;
  }
  .shortcut-note {
    grid-column: 1 / -1;
    display: none;
  }
}
@media (max-width: 520px) {
  .side-column {
    grid-template-columns: minmax(0, 1fr);
  }
  .report-heading {
    flex-wrap: wrap;
  }
  .report-content {
    padding: 26px 22px;
  }
  .report-content h3 {
    font-size: 20px;
  }
  .report-footer {
    flex-wrap: wrap;
    justify-content: flex-start;
    column-gap: 20px;
  }
  .foundation-copy {
    flex-basis: calc(100% - 50px);
  }
  .foundation-strip > .text-link {
    margin-left: 42px;
  }
  .dashboard-footer {
    flex-direction: column;
    gap: 6px;
  }
}
</style>
