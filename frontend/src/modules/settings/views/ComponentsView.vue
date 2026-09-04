<script setup lang="ts">
import { nextTick, onUnmounted, ref } from 'vue'
import { PhPlus, PhArrowRight, PhTray } from '@phosphor-icons/vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiCard from '../../../shared/components/ui/UiCard.vue'
import UiBadge from '../../../shared/components/ui/UiBadge.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiSelect from '../../../shared/components/ui/UiSelect.vue'
import UiTextarea from '../../../shared/components/ui/UiTextarea.vue'
import UiCheckbox from '../../../shared/components/ui/UiCheckbox.vue'
import UiTabs from '../../../shared/components/ui/UiTabs.vue'
import UiModal from '../../../shared/components/ui/UiModal.vue'
import UiConfirmDialog from '../../../shared/components/ui/UiConfirmDialog.vue'
import UiSkeleton from '../../../shared/components/ui/UiSkeleton.vue'
import UiEmptyState from '../../../shared/components/ui/UiEmptyState.vue'
import UiErrorState from '../../../shared/components/ui/UiErrorState.vue'
import UiDataTable from '../../../shared/components/ui/UiDataTable.vue'
import UiCodeBlock from '../../../shared/components/ui/UiCodeBlock.vue'
import { useToast } from '../../../shared/composables/useToast'
const { notify } = useToast()
const tab = ref('primitives')
const busy = ref(false)
const modal = ref(false)
const confirm = ref(false)
const title = ref('')
const environment = ref('staging')
const notes = ref('')
const checked = ref(false)
const error = ref('')
const success = ref(false)
const showError = ref(true)
let timer: ReturnType<typeof setTimeout> | undefined
function simulate(): void {
  busy.value = true
  timer = setTimeout(() => {
    busy.value = false
    notify('Contoh aksi selesai.')
  }, 1000)
}
async function submit(event: Event): Promise<void> {
  const form = event.currentTarget
  error.value = title.value.trim() ? '' : 'Isi nama contoh aktivitas terlebih dahulu.'
  success.value = !error.value
  if (error.value && form instanceof HTMLFormElement) {
    await nextTick()
    form.querySelector<HTMLInputElement>('[aria-invalid="true"]')?.focus()
  }
}
onUnmounted(() => clearTimeout(timer))
function retryExample(): void {
  showError.value = false
  notify('Contoh percobaan ulang berhasil.')
}
function confirmExample(): void {
  confirm.value = false
  notify('Contoh konfirmasi berhasil.')
}
const inventory = [
  { id: 1, name: 'UiButton', category: 'Aksi', states: 5 },
  { id: 2, name: 'UiCard', category: 'Layout', states: 3 },
  { id: 3, name: 'UiInput', category: 'Form', states: 4 },
  { id: 4, name: 'UiSelect', category: 'Form', states: 4 },
  { id: 5, name: 'UiTextarea', category: 'Form', states: 4 },
  { id: 6, name: 'UiModal', category: 'Overlay', states: 2 },
  { id: 7, name: 'UiBadge', category: 'Status', states: 5 },
]
const columns = [
  { key: 'name', label: 'Komponen', sortable: true },
  { key: 'category', label: 'Kategori', sortable: true },
] as const
const code =
  ':root {\n  --color-ink: #403d88;\n  --color-violet: #8b639b;\n  --color-mauve: #af719d;\n  --color-blush: #f8b2b2;\n}'
</script>
<template>
  <div class="page-header">
    <div>
      <h1>Satu bahasa, semua komponen.</h1>
      <p>
        Coba fondasi UI yang akan dipakai di setiap modul. Interaksi di halaman ini menggunakan data
        contoh.
      </p>
    </div>
    <UiBadge tone="info">UI library</UiBadge>
  </div>
  <UiTabs
    v-model="tab"
    label="Kategori komponen"
    :tabs="[
      { value: 'primitives', label: 'Komponen dasar' },
      { value: 'forms', label: 'Form & feedback' },
      { value: 'data', label: 'Tabel & output' },
    ]"
  >
    <template #primitives>
      <div class="stack">
        <UiCard>
          <template #header>
            <h2>Button</h2>
            <p class="small muted mt-1">Satu komponen dengan varian sesuai tujuan aksi.</p>
          </template>
          <div class="cluster">
            <UiButton @click="notify('Primary button berfungsi.')">
              <PhPlus :size="16" />
              Primary
            </UiButton>
            <UiButton
              variant="secondary"
              @click="notify('Secondary button berfungsi.')"
            >
              Secondary
            </UiButton>
            <UiButton
              variant="quiet"
              @click="notify('Quiet button berfungsi.')"
            >
              Quiet
            </UiButton>
            <UiButton
              variant="ghost"
              @click="notify('Ghost button berfungsi.')"
            >
              Ghost
              <PhArrowRight :size="16" />
            </UiButton>
            <UiButton
              variant="danger"
              @click="confirm = true"
            >
              Danger
            </UiButton>
          </div>
          <div class="cluster mt-5">
            <UiButton
              :loading="busy"
              @click="simulate"
            >
              Coba loading
            </UiButton>
            <UiButton disabled>Disabled</UiButton>
            <UiButton
              size="sm"
              variant="secondary"
              @click="notify('Small button berfungsi.')"
            >
              Small
            </UiButton>
            <UiButton
              icon-only
              label="Tambah contoh"
              variant="secondary"
              @click="notify('Icon button berfungsi.')"
            >
              <PhPlus :size="20" />
            </UiButton>
          </div>
        </UiCard>
        <section>
          <div class="section-heading"><h2>Card & surface</h2></div>
          <div class="card-examples">
            <UiCard>
              <template #header><h3>Default surface</h3></template>
              <p class="muted small">
                Border dan spacing yang konsisten, dengan slot header dan footer.
              </p>
              <template #footer><span class="small muted">Footer opsional</span></template>
            </UiCard>
            <UiCard tone="subtle">
              <template #header><h3>Subtle surface</h3></template>
              <p class="muted small">
                Untuk konten pendukung yang tetap berada dalam kelompok yang jelas.
              </p>
            </UiCard>
          </div>
        </section>
        <UiCard>
          <template #header><h2>Status</h2></template>
          <div class="cluster">
            <UiBadge>Draft</UiBadge>
            <UiBadge tone="success">Pass</UiBadge>
            <UiBadge tone="warning">In progress</UiBadge>
            <UiBadge tone="danger">Fail</UiBadge>
            <UiBadge tone="info">Info</UiBadge>
          </div>
        </UiCard>
        <section>
          <div class="section-heading"><h2>Dialog & konfirmasi</h2></div>
          <div class="cluster">
            <UiButton
              variant="secondary"
              @click="modal = true"
            >
              Buka dialog
            </UiButton>
            <UiButton
              variant="secondary"
              @click="confirm = true"
            >
              Coba konfirmasi
            </UiButton>
          </div>
        </section>
      </div>
    </template>
    <template #forms>
      <div class="component-columns">
        <UiCard>
          <template #header>
            <h2>Contoh form</h2>
            <p class="muted small mt-1">Label, validasi inline, dan state native.</p>
          </template>
          <form
            class="stack"
            novalidate
            @submit.prevent="submit"
          >
            <UiInput
              v-model="title"
              label="Nama aktivitas"
              placeholder="Contoh: cek alur login"
              hint="Data ini hanya untuk mencoba komponen."
              :error="error"
              required
              @input="success = false"
            />
            <UiSelect
              v-model="environment"
              label="Environment"
              :options="[
                { value: 'dev', label: 'Development' },
                { value: 'staging', label: 'Staging' },
                { value: 'prod', label: 'Production' },
              ]"
            />
            <UiTextarea
              v-model="notes"
              label="Catatan"
              placeholder="Tambahkan catatan contoh…"
            />
            <UiCheckbox
              v-model="checked"
              label="Tandai contoh aktivitas"
            />
            <UiButton type="submit">Validasi contoh</UiButton>
            <p
              v-if="success"
              role="status"
              class="small success-text"
            >
              Contoh form valid. Tidak ada data yang disimpan.
            </p>
          </form>
        </UiCard>
        <div class="stack">
          <UiCard>
            <template #header><h3>Loading</h3></template>
            <UiSkeleton :lines="4" />
          </UiCard>
          <UiCard>
            <UiEmptyState
              compact
              title="Belum ada aktivitas"
              description="Empty state menjelaskan apa yang bisa dilakukan berikutnya."
            >
              <template #icon><PhTray :size="30" /></template>
            </UiEmptyState>
          </UiCard>
          <UiErrorState
            v-if="showError"
            message="Contoh kegagalan koneksi. Input tetap tersimpan selama sesi."
            retryable
            @retry="retryExample"
          />
          <UiButton
            v-else
            variant="secondary"
            @click="showError = true"
          >
            Tampilkan contoh error
          </UiButton>
        </div>
      </div>
    </template>
    <template #data>
      <div class="stack">
        <UiCard>
          <template #header>
            <h2>Data table</h2>
            <p class="small muted mt-1">
              Klik judul kolom untuk mengurutkan. Pagination menggunakan inventaris komponen sebagai
              contoh.
            </p>
          </template>
          <UiDataTable
            :rows="inventory"
            :columns="columns"
            row-key="id"
            caption="Inventaris komponen shared"
            :page-size="4"
          >
            <template #cell-name="{ value }">
              <code>{{ value }}</code>
            </template>
          </UiDataTable>
        </UiCard>
        <UiCodeBlock
          :code="code"
          label="Palette tokens · CSS"
        />
      </div>
    </template>
  </UiTabs>
  <UiModal
    v-model="modal"
    title="Dialog yang bisa digunakan ulang"
    description="Fokus tetap berada di dialog. Tekan Escape atau tombol tutup untuk kembali."
  >
    <UiInput
      label="Contoh input dalam dialog"
      placeholder="Coba navigasi dengan Tab"
      autofocus
    />
    <template #footer><UiButton @click="modal = false">Selesai</UiButton></template>
  </UiModal>
  <UiConfirmDialog
    v-model="confirm"
    title="Contoh konfirmasi"
    description="Ini hanya demonstrasi dialog. Tidak ada data yang akan dihapus."
    confirm-label="Konfirmasi contoh"
    @confirm="confirmExample"
  />
</template>
<style scoped>
.card-examples {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}
.component-columns {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  align-items: start;
  gap: 24px;
}
.success-text {
  color: var(--color-success);
}
@media (max-width: 950px) {
  .component-columns {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 600px) {
  .card-examples {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
