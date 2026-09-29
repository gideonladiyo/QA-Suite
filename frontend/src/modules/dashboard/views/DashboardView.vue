<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  PhArrowRight,
  PhArrowUpRight,
  PhClipboardText,
  PhDatabase,
  PhImageSquare,
  PhLockKey,
} from '@phosphor-icons/vue'
import UiBadge from '../../../shared/components/ui/UiBadge.vue'
import { toolNavigation } from '../../../shared/navigation'
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

const now = ref(new Date())
const date = computed(() =>
  new Intl.DateTimeFormat('id-ID', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(now.value),
)
const time = computed(() =>
  new Intl.DateTimeFormat('id-ID', { hour: '2-digit', minute: '2-digit' }).format(now.value),
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
  { ...toolNavigation[0]!, description: 'Kirim request dan periksa respons API.' },
  { ...toolNavigation[1]!, description: 'Format serta validasi JSON atau YAML.' },
  { ...toolNavigation[2]!, description: 'Susun data uji dari schema pilihanmu.' },
  { ...toolNavigation[3]!, description: 'Baca Base64 dan claim token secara lokal.' },
]
</script>

<template>
  <header class="dashboard-heading">
    <div>
      <h1>Dashboard</h1>
      <p>Ringkasan kerja hari ini dan jalan cepat ke alat yang kamu butuhkan.</p>
    </div>
    <div class="date-stamp">
      <time :datetime="now.toISOString()">{{ date }}</time>
      <span aria-hidden="true" />
      <strong>{{ time }}</strong>
    </div>
  </header>

  <div class="workspace-grid">
    <section
      class="ledger-panel report-panel"
      aria-labelledby="report-title"
    >
      <header class="ledger-header">
        <div class="ledger-label">
          <PhClipboardText
            :size="17"
            aria-hidden="true"
          />
          <span>QA REPORT / HARI INI</span>
        </div>
        <span class="register-code">WORK LOG</span>
      </header>

      <div class="report-body">
        <div class="report-copy">
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
          <h2 id="report-title">
            {{
              todayReport
                ? `${todayReport.item_count} aktivitas tercatat.`
                : 'Laporan hari ini belum dibuat.'
            }}
          </h2>
          <p>
            Catat pekerjaan per tiket, hasil pengujian, coverage, dan isu tanpa berpindah workspace.
          </p>
          <RouterLink
            :to="todayReport ? `/qa-reports/${todayReport.id}?edit=1` : '/qa-reports/new'"
            class="primary-link"
          >
            {{ todayReport ? 'Buka laporan hari ini' : 'Buat laporan' }}
            <PhArrowRight :size="17" />
          </RouterLink>
        </div>

        <UiErrorState
          v-if="reportError"
          :message="reportError"
          retryable
          @retry="loadReport"
        />
        <dl
          v-else
          class="report-register"
        >
          <div>
            <dt>Tanggal</dt>
            <dd>{{ localDate(now) }}</dd>
          </div>
          <div>
            <dt>Aktivitas</dt>
            <dd>{{ todayReport?.item_count ?? '—' }}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>{{ todayReport ? statusLabel(todayReport.status) : 'Belum ada catatan' }}</dd>
          </div>
        </dl>
      </div>

      <footer class="ledger-note">
        <span>Satu laporan per hari kerja</span>
        <RouterLink to="/qa-reports">
          Lihat riwayat
          <PhArrowRight :size="14" />
        </RouterLink>
      </footer>
    </section>

    <aside
      class="status-column"
      aria-label="Status workspace"
    >
      <section class="ledger-panel status-panel">
        <header class="ledger-header">
          <div class="ledger-label">
            <PhDatabase
              :size="17"
              aria-hidden="true"
            />
            <span>KONEKSI DATA</span>
          </div>
          <span class="register-code">SUPABASE</span>
        </header>
        <div class="status-body">
          <div>
            <h2>Belum terhubung</h2>
            <p>Pilih project sebelum menjalankan pekerjaan berbasis data.</p>
          </div>
          <RouterLink
            to="/supabase-hub"
            class="secondary-link"
          >
            Kelola koneksi
            <PhArrowRight :size="15" />
          </RouterLink>
        </div>
      </section>

      <section class="ledger-panel status-panel">
        <header class="ledger-header">
          <div class="ledger-label">
            <PhLockKey
              :size="17"
              aria-hidden="true"
            />
            <span>VAULT</span>
          </div>
          <UiBadge tone="success">Terenkripsi</UiBadge>
        </header>
        <div class="status-body">
          <div>
            <h2>Vault terkunci</h2>
            <p>Secret tetap tersamarkan sampai Master Lock dibuka.</p>
          </div>
          <RouterLink
            to="/vault"
            class="secondary-link"
          >
            Buka Vault
            <PhArrowRight :size="15" />
          </RouterLink>
        </div>
      </section>
    </aside>
  </div>

  <section
    class="tools-ledger"
    aria-labelledby="tools-title"
  >
    <header class="ledger-header">
      <div>
        <h2 id="tools-title">Utilitas developer</h2>
        <p>Proses cepat yang berjalan langsung dari workspace lokal.</p>
      </div>
      <span class="register-code">4 ALAT / SIAP DIPAKAI</span>
    </header>
    <div class="tool-rows">
      <RouterLink
        v-for="tool in tools"
        :key="tool.path"
        :to="tool.path"
        class="tool-row"
      >
        <component
          :is="tool.icon"
          :size="20"
          aria-hidden="true"
        />
        <strong>{{ tool.label }}</strong>
        <span>{{ tool.description }}</span>
        <PhArrowUpRight
          :size="16"
          aria-hidden="true"
        />
      </RouterLink>
    </div>
  </section>

  <section
    class="utility-strip"
    aria-label="Alat tambahan"
  >
    <RouterLink
      to="/photo-editor"
      class="utility-link"
    >
      <PhImageSquare
        :size="23"
        aria-hidden="true"
      />
      <span>
        <strong>Photo Editor</strong>
        <small>Layer, mask, adjustment, dan export diproses lokal.</small>
      </span>
      <PhArrowUpRight :size="16" />
    </RouterLink>
    <RouterLink
      to="/components"
      class="utility-link"
    >
      <span
        class="component-mark"
        aria-hidden="true"
      >
        UI
      </span>
      <span>
        <strong>Sistem komponen</strong>
        <small>Lihat fondasi antarmuka yang dipakai seluruh modul.</small>
      </span>
      <PhArrowUpRight :size="16" />
    </RouterLink>
  </section>

  <footer class="dashboard-footer">
    <span>WORKBENCH / CALIBRATION LEDGER</span>
    <span>LOCAL-FIRST · TANPA TELEMETRY</span>
  </footer>
</template>

<style scoped>
.dashboard-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--color-border-strong);
}
.dashboard-heading p {
  max-width: 62ch;
  margin-top: 7px;
  color: var(--color-text-muted);
  font-size: 14px;
}
.date-stamp {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 11px;
  white-space: nowrap;
}
.date-stamp span {
  width: 1px;
  height: 18px;
  background: var(--color-border-strong);
}
.date-stamp strong {
  color: var(--color-text);
  font-weight: 500;
}
.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.75fr) minmax(300px, 0.9fr);
  gap: 18px;
}
.ledger-panel,
.tools-ledger,
.utility-strip {
  background: var(--color-surface);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-panel);
}
.ledger-header {
  min-height: 48px;
  padding: 11px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--color-border-strong);
}
.ledger-label {
  display: flex;
  align-items: center;
  gap: 9px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.1em;
}
.register-code {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.11em;
  white-space: nowrap;
}
.report-body {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(220px, 0.7fr);
  min-height: 308px;
}
.report-copy {
  padding: 34px 32px;
  border-right: 1px solid var(--color-ledger-line);
}
.report-copy h2 {
  max-width: 20ch;
  margin-top: 20px;
  font-size: clamp(25px, 3vw, 36px);
}
.report-copy p {
  max-width: 52ch;
  margin: 12px 0 28px;
  color: var(--color-text-muted);
  font-size: 14px;
  line-height: 1.65;
}
.primary-link,
.secondary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  min-height: 42px;
  padding: 9px 14px;
  border-radius: var(--radius-control);
  font-size: 13px;
  font-weight: 600;
  transition:
    background-color var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}
.primary-link {
  color: var(--color-on-primary);
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
}
.primary-link:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
}
.secondary-link {
  color: var(--color-primary);
  background: transparent;
  border: 1px solid var(--color-border-strong);
}
.secondary-link:hover {
  border-color: var(--color-primary);
  background: var(--color-surface-accent);
}
.report-register {
  margin: 0;
  padding: 24px 20px;
}
.report-register div {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 12px;
  padding: 13px 0;
  border-bottom: 1px solid var(--color-ledger-line);
}
.report-register dt {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.report-register dd {
  margin: 0;
  font-size: 13px;
  font-weight: 500;
}
.ledger-note {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 46px;
  padding: 10px 16px;
  border-top: 1px solid var(--color-border-strong);
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.ledger-note a {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-primary);
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0;
  text-transform: none;
}
.status-column {
  display: grid;
  gap: 18px;
}
.status-panel {
  min-height: 0;
}
.status-body {
  display: flex;
  min-height: 150px;
  padding: 22px 20px;
  flex-direction: column;
  align-items: flex-start;
  justify-content: space-between;
  gap: 22px;
}
.status-body h2 {
  font-size: 21px;
}
.status-body p {
  max-width: 38ch;
  margin-top: 8px;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.55;
}
.tools-ledger {
  margin-top: 18px;
}
.tools-ledger > .ledger-header {
  align-items: flex-end;
}
.tools-ledger h2 {
  font-size: 18px;
}
.tools-ledger .ledger-header p {
  margin-top: 4px;
  color: var(--color-text-muted);
  font-size: 12px;
}
.tool-rows {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.tool-row {
  display: grid;
  grid-template-columns: 28px minmax(110px, 0.45fr) minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 72px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-ledger-line);
  transition: background-color var(--duration-fast) var(--ease-out);
}
.tool-row:nth-child(odd) {
  border-right: 1px solid var(--color-ledger-line);
}
.tool-row:nth-last-child(-n + 2) {
  border-bottom: 0;
}
.tool-row:hover {
  background: var(--color-surface-accent);
}
.tool-row > svg:first-child {
  color: var(--color-primary);
}
.tool-row strong {
  font-size: 13px;
}
.tool-row span {
  color: var(--color-text-muted);
  font-size: 12px;
}
.utility-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 18px;
}
.utility-link {
  display: flex;
  align-items: center;
  gap: 13px;
  min-height: 82px;
  padding: 16px 18px;
}
.utility-link + .utility-link {
  border-left: 1px solid var(--color-border-strong);
}
.utility-link:hover {
  background: var(--color-surface-accent);
}
.utility-link > span:nth-child(2) {
  flex: 1;
}
.utility-link strong,
.utility-link small {
  display: block;
}
.utility-link strong {
  font-size: 14px;
}
.utility-link small {
  margin-top: 4px;
  color: var(--color-text-muted);
  font-size: 11px;
}
.component-mark {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: 9px;
}
.dashboard-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 22px;
  padding-top: 14px;
  border-top: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.09em;
}

@media (max-width: 1080px) {
  .workspace-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .status-column {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 820px) {
  .tool-rows {
    grid-template-columns: minmax(0, 1fr);
  }
  .tool-row:nth-child(odd) {
    border-right: 0;
  }
  .tool-row:nth-last-child(2) {
    border-bottom: 1px solid var(--color-ledger-line);
  }
}
@media (max-width: 680px) {
  .dashboard-heading {
    align-items: flex-start;
    flex-direction: column;
  }
  .date-stamp {
    white-space: normal;
  }
  .report-body,
  .status-column,
  .utility-strip {
    grid-template-columns: minmax(0, 1fr);
  }
  .report-copy {
    padding: 28px 20px;
    border-right: 0;
    border-bottom: 1px solid var(--color-ledger-line);
  }
  .report-register {
    padding: 12px 20px 20px;
  }
  .tool-row {
    grid-template-columns: 26px minmax(0, 1fr) auto;
  }
  .tool-row span {
    grid-column: 2 / 3;
  }
  .tool-row > svg:last-child {
    grid-column: 3;
    grid-row: 1 / 3;
  }
  .utility-link + .utility-link {
    border-left: 0;
    border-top: 1px solid var(--color-border-strong);
  }
  .ledger-note,
  .dashboard-footer {
    align-items: flex-start;
    flex-direction: column;
  }
  .register-code {
    display: none;
  }
}
</style>
