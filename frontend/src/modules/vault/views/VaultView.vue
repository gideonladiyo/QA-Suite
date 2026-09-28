<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  PhCopy,
  PhEye,
  PhEyeSlash,
  PhKey,
  PhLockKey,
  PhPencilSimple,
  PhPlus,
  PhShieldCheck,
  PhTerminalWindow,
  PhTrash,
} from '@phosphor-icons/vue'
import { ApiError, errorMessage } from '../../../shared/api'
import { useToast } from '../../../shared/composables/useToast'
import UiBadge from '../../../shared/components/ui/UiBadge.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiCard from '../../../shared/components/ui/UiCard.vue'
import UiCheckbox from '../../../shared/components/ui/UiCheckbox.vue'
import UiConfirmDialog from '../../../shared/components/ui/UiConfirmDialog.vue'
import UiDataTable from '../../../shared/components/ui/UiDataTable.vue'
import UiEmptyState from '../../../shared/components/ui/UiEmptyState.vue'
import UiErrorState from '../../../shared/components/ui/UiErrorState.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiModal from '../../../shared/components/ui/UiModal.vue'
import UiSelect from '../../../shared/components/ui/UiSelect.vue'
import UiSkeleton from '../../../shared/components/ui/UiSkeleton.vue'
import UiTextarea from '../../../shared/components/ui/UiTextarea.vue'
import {
  vaultApi,
  type VaultCategory,
  type VaultEntry,
  type VaultEntryInput,
  type VaultSort,
  type VaultStatus,
} from '../api'

const categoryOptions: readonly { value: VaultCategory | ''; label: string }[] = [
  { value: '', label: 'Semua kategori' },
  { value: 'password', label: 'Password' },
  { value: 'api_key', label: 'API key' },
  { value: 'token', label: 'Token' },
  { value: 'command', label: 'Command' },
  { value: 'note', label: 'Catatan' },
  { value: 'other', label: 'Lainnya' },
]
const entryCategoryOptions = categoryOptions.slice(1) as readonly {
  value: VaultCategory
  label: string
}[]
const sortOptions: readonly { value: VaultSort; label: string }[] = [
  { value: 'recent', label: 'Terakhir digunakan' },
  { value: 'alphabetical', label: 'Judul A–Z' },
  { value: 'created', label: 'Terbaru dibuat' },
]
type VaultRow = VaultEntry & { protectedValue: string; actions: string }
const columns: readonly { key: keyof VaultRow; label: string }[] = [
  { key: 'title', label: 'Item' },
  { key: 'category', label: 'Kategori' },
  { key: 'protectedValue', label: 'Nilai' },
  { key: 'last_accessed_at', label: 'Terakhir diakses' },
  { key: 'actions', label: 'Aksi' },
]
const autoLockKey = 'qa-portal:vault-auto-lock'

const { notify } = useToast()
const status = ref<VaultStatus>()
const loading = ref(true)
const pageError = ref('')
const lockNotice = ref('')
const masterSecret = ref('')
const confirmation = ref('')
const masterError = ref('')
const masterBusy = ref(false)
const token = ref('')
const entries = ref<VaultEntry[]>([])
const listLoading = ref(false)
const listError = ref('')
const actionError = ref('')
const search = ref('')
const category = ref<VaultCategory | ''>('')
const sort = ref<VaultSort>('recent')
const autoLockMinutes = ref(loadAutoLock())
const revealed = ref<{ id: string; value: string; notes: string }>()
const revealBusy = ref('')
const copyBusy = ref('')
const editorOpen = ref(false)
const editing = ref<VaultEntry>()
const editorBusy = ref(false)
const editorError = ref('')
const editorForm = ref<HTMLFormElement>()
const showEditorValue = ref(false)
const deleteTarget = ref<VaultEntry>()
const deleteBusy = ref(false)
const deleteError = ref('')
const generatorLength = ref('20')
const generator = reactive({ uppercase: true, lowercase: true, digits: true, symbols: true })
const form = reactive<VaultEntryInput>(blankEntry())
const rows = computed<VaultRow[]>(() =>
  entries.value.map((entry) => ({ ...entry, protectedValue: '', actions: '' })),
)

let searchTimer: ReturnType<typeof setTimeout> | undefined
let lockTimer: ReturnType<typeof setTimeout> | undefined
let clipboardTimer: ReturnType<typeof setTimeout> | undefined
let lastTouch = 0

function loadAutoLock(): number {
  const value = Number(localStorage.getItem(autoLockKey) ?? 5)
  return Number.isInteger(value) && value >= 1 && value <= 60 ? value : 5
}

function saveAutoLock(value: string): void {
  autoLockMinutes.value = Number(value)
  localStorage.setItem(autoLockKey, value)
}

function blankEntry(): VaultEntryInput {
  return { title: '', username: '', category: 'password', url: '', value: '', notes: '' }
}

function categoryLabel(value: VaultCategory): string {
  return entryCategoryOptions.find((option) => option.value === value)?.label ?? value
}

function dateLabel(value: string | null): string {
  if (!value) return 'Belum pernah'
  return new Intl.DateTimeFormat('id-ID', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function clearUnlockedState(message = ''): void {
  token.value = ''
  entries.value = []
  revealed.value = undefined
  editorOpen.value = false
  deleteTarget.value = undefined
  status.value = { configured: status.value?.configured ?? true, unlocked: false }
  lockNotice.value = message
  clearTimeout(lockTimer)
}

function handleVaultError(cause: unknown): void {
  if (cause instanceof ApiError && cause.status === 423) {
    clearUnlockedState('Sesi Vault berakhir. Masukkan Master PIN atau passphrase lagi.')
  }
}

async function checkStatus(): Promise<void> {
  loading.value = true
  pageError.value = ''
  try {
    status.value = await vaultApi.status()
  } catch (cause) {
    pageError.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

async function loadEntries(): Promise<void> {
  if (!token.value) return
  listLoading.value = true
  listError.value = ''
  try {
    entries.value = await vaultApi.list(token.value, {
      search: search.value,
      category: category.value,
      sort: sort.value,
    })
  } catch (cause) {
    handleVaultError(cause)
    listError.value = errorMessage(cause)
  } finally {
    listLoading.value = false
  }
}

function beginUnlocked(result: { token: string; auto_lock_minutes: number }): void {
  token.value = result.token
  status.value = { configured: true, unlocked: true }
  autoLockMinutes.value = result.auto_lock_minutes
  masterSecret.value = ''
  confirmation.value = ''
  masterError.value = ''
  lockNotice.value = ''
  lastTouch = Date.now()
  resetActivity()
  void loadEntries()
}

async function submitMaster(): Promise<void> {
  masterError.value = ''
  if (!status.value?.configured && masterSecret.value !== confirmation.value) {
    masterError.value = 'Konfirmasi Master tidak sama.'
    return
  }
  masterBusy.value = true
  try {
    const result = status.value?.configured
      ? await vaultApi.unlock(masterSecret.value, autoLockMinutes.value)
      : await vaultApi.setup(masterSecret.value, confirmation.value, autoLockMinutes.value)
    beginUnlocked(result)
  } catch (cause) {
    masterError.value = errorMessage(cause)
  } finally {
    masterBusy.value = false
  }
}

async function lockVault(automatic = false): Promise<void> {
  const current = token.value
  if (!current) return
  clearUnlockedState(automatic ? 'Vault dikunci otomatis karena tidak ada aktivitas.' : '')
  try {
    await vaultApi.lock(current)
    if (!automatic) notify('Vault dikunci.')
  } catch (cause) {
    pageError.value = errorMessage(cause)
  }
}

function resetActivity(): void {
  if (!token.value) return
  clearTimeout(lockTimer)
  lockTimer = setTimeout(() => void lockVault(true), autoLockMinutes.value * 60_000)
  if (Date.now() - lastTouch >= 60_000) {
    lastTouch = Date.now()
    void vaultApi.touch(token.value).catch(handleVaultError)
  }
}

function openCreate(): void {
  editing.value = undefined
  Object.assign(form, blankEntry())
  editorError.value = ''
  showEditorValue.value = false
  editorOpen.value = true
}

async function openEdit(entry: VaultEntry): Promise<void> {
  revealBusy.value = entry.id
  actionError.value = ''
  try {
    const detail = await vaultApi.reveal(token.value, entry.id)
    editing.value = entry
    Object.assign(form, {
      title: entry.title,
      username: entry.username ?? '',
      category: entry.category,
      url: entry.url ?? '',
      value: detail.value,
      notes: detail.notes,
    })
    editorError.value = ''
    showEditorValue.value = false
    editorOpen.value = true
  } catch (cause) {
    handleVaultError(cause)
    actionError.value = errorMessage(cause)
  } finally {
    revealBusy.value = ''
  }
}

async function saveEntry(): Promise<void> {
  editorError.value = ''
  if (!form.title.trim() || !form.value) {
    editorError.value = 'Judul dan nilai wajib diisi.'
    await nextTick()
    editorForm.value?.querySelector<HTMLElement>(':invalid')?.focus()
    return
  }
  editorBusy.value = true
  try {
    if (editing.value) await vaultApi.update(token.value, editing.value.id, { ...form })
    else await vaultApi.create(token.value, { ...form })
    editorOpen.value = false
    revealed.value = undefined
    notify(editing.value ? 'Item Vault diperbarui.' : 'Item Vault disimpan.')
    await loadEntries()
  } catch (cause) {
    handleVaultError(cause)
    editorError.value = errorMessage(cause)
  } finally {
    editorBusy.value = false
  }
}

async function toggleReveal(entry: VaultEntry): Promise<void> {
  if (revealed.value?.id === entry.id) {
    revealed.value = undefined
    return
  }
  revealBusy.value = entry.id
  actionError.value = ''
  try {
    const detail = await vaultApi.reveal(token.value, entry.id)
    revealed.value = { id: entry.id, value: detail.value, notes: detail.notes }
    entry.last_accessed_at = new Date().toISOString()
  } catch (cause) {
    handleVaultError(cause)
    actionError.value = errorMessage(cause)
  } finally {
    revealBusy.value = ''
  }
}

async function digestText(value: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

async function copyEntry(entry: VaultEntry): Promise<void> {
  copyBusy.value = entry.id
  actionError.value = ''
  try {
    const response = await vaultApi.copy(token.value, entry.id)
    const digest = await digestText(response.value)
    await navigator.clipboard.writeText(response.value)
    entry.last_accessed_at = new Date().toISOString()
    notify('Nilai disalin. Clipboard akan dicoba dibersihkan dalam 30 detik.')
    clearTimeout(clipboardTimer)
    clipboardTimer = setTimeout(async () => {
      try {
        const current = await navigator.clipboard.readText()
        if ((await digestText(current)) === digest) {
          await navigator.clipboard.writeText('')
          notify('Clipboard Vault dibersihkan.')
        }
      } catch {
        notify('Browser tidak mengizinkan pembersihan clipboard otomatis.')
      }
    }, 30_000)
  } catch (cause) {
    handleVaultError(cause)
    actionError.value =
      cause instanceof DOMException
        ? 'Clipboard tidak tersedia. Gunakan Lihat lalu salin secara manual.'
        : errorMessage(cause)
  } finally {
    copyBusy.value = ''
  }
}

async function removeEntry(): Promise<void> {
  if (!deleteTarget.value) return
  deleteBusy.value = true
  deleteError.value = ''
  try {
    await vaultApi.remove(token.value, deleteTarget.value.id)
    if (revealed.value?.id === deleteTarget.value.id) revealed.value = undefined
    deleteTarget.value = undefined
    notify('Item Vault dihapus permanen.')
    await loadEntries()
  } catch (cause) {
    handleVaultError(cause)
    deleteError.value = errorMessage(cause)
  } finally {
    deleteBusy.value = false
  }
}

function randomIndex(maximum: number): number {
  return crypto.getRandomValues(new Uint32Array(1))[0]! % maximum
}

function generatePassword(): void {
  const groups = [
    generator.lowercase ? 'abcdefghijkmnopqrstuvwxyz' : '',
    generator.uppercase ? 'ABCDEFGHJKLMNPQRSTUVWXYZ' : '',
    generator.digits ? '23456789' : '',
    generator.symbols ? '!@#$%^&*()-_=+' : '',
  ].filter(Boolean)
  if (!groups.length) {
    editorError.value = 'Pilih minimal satu kelompok karakter.'
    return
  }
  const length = Math.min(64, Math.max(12, Number(generatorLength.value) || 20))
  generatorLength.value = String(length)
  const all = groups.join('')
  const output = groups.map((group) => group[randomIndex(group.length)]!)
  while (output.length < length) output.push(all[randomIndex(all.length)]!)
  for (let index = output.length - 1; index > 0; index--) {
    const swap = randomIndex(index + 1)
    ;[output[index], output[swap]] = [output[swap]!, output[index]!]
  }
  form.value = output.join('')
  showEditorValue.value = true
  editorError.value = ''
}

function closeOnPageHide(): void {
  if (token.value) void vaultApi.lock(token.value, true)
}

watch([search, category, sort], () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void loadEntries(), 250)
})

onMounted(() => {
  void checkStatus()
  window.addEventListener('keydown', resetActivity)
  window.addEventListener('pointerdown', resetActivity)
  window.addEventListener('pagehide', closeOnPageHide)
})

onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  clearTimeout(lockTimer)
  clearTimeout(clipboardTimer)
  window.removeEventListener('keydown', resetActivity)
  window.removeEventListener('pointerdown', resetActivity)
  window.removeEventListener('pagehide', closeOnPageHide)
  const current = token.value
  token.value = ''
  if (current) void vaultApi.lock(current, true)
})
</script>

<template>
  <div class="page-header">
    <div>
      <h1>Vault</h1>
      <p>
        Simpan password, token, catatan sensitif, dan command penting dalam satu ruang terenkripsi.
      </p>
    </div>
    <div class="vault-status">
      <UiBadge :tone="status?.unlocked ? 'success' : 'neutral'">
        <component
          :is="status?.unlocked ? PhShieldCheck : PhLockKey"
          :size="14"
        />
        {{ status?.unlocked ? 'Terbuka' : 'Terkunci' }}
      </UiBadge>
      <UiButton
        v-if="status?.unlocked"
        variant="secondary"
        size="sm"
        @click="lockVault()"
      >
        <PhLockKey :size="16" />
        Kunci sekarang
      </UiButton>
    </div>
  </div>

  <UiSkeleton
    v-if="loading"
    :lines="5"
    label="Memeriksa Vault"
  />
  <UiErrorState
    v-else-if="pageError && !status"
    :message="pageError"
    retryable
    @retry="checkStatus"
  />

  <UiCard
    v-else-if="!status?.unlocked"
    class="master-card"
    padding="lg"
    elevated
  >
    <div class="master-heading">
      <div class="master-icon">
        <PhLockKey
          :size="30"
          weight="duotone"
        />
      </div>
      <div>
        <h2>{{ status?.configured ? 'Buka Vault' : 'Buat Master Lock' }}</h2>
        <p class="muted small mt-2">
          {{
            status?.configured
              ? 'Master hanya digunakan untuk membuka key enkripsi di memori sesi ini.'
              : 'Gunakan minimal 6 digit untuk PIN atau 8 karakter untuk passphrase.'
          }}
        </p>
      </div>
    </div>
    <p
      v-if="lockNotice"
      class="lock-notice"
      role="status"
    >
      {{ lockNotice }}
    </p>
    <form
      class="master-form"
      @submit.prevent="submitMaster"
    >
      <UiInput
        v-model="masterSecret"
        :label="status?.configured ? 'Master PIN atau passphrase' : 'Master baru'"
        type="password"
        required
        maxlength="128"
        :autocomplete="status?.configured ? 'current-password' : 'new-password'"
        autofocus
      />
      <UiInput
        v-if="!status?.configured"
        v-model="confirmation"
        label="Ulangi Master"
        type="password"
        required
        maxlength="128"
        autocomplete="new-password"
      />
      <UiSelect
        :model-value="String(autoLockMinutes)"
        label="Kunci otomatis"
        :options="
          [1, 3, 5, 10, 15, 30, 60].map((value) => ({
            value: String(value),
            label: `${value} menit`,
          }))
        "
        hint="Berlaku untuk sesi Vault berikutnya dan tersimpan di browser ini."
        @update:model-value="saveAutoLock"
      />
      <div
        v-if="!status?.configured"
        class="recovery-warning"
      >
        <strong>Tidak ada pemulihan Master di versi ini.</strong>
        <span>Jika lupa, isi Vault tidak dapat didekripsi kembali.</span>
      </div>
      <UiErrorState
        v-if="masterError"
        :message="masterError"
      />
      <UiButton
        type="submit"
        :loading="masterBusy"
      >
        {{ status?.configured ? 'Buka Vault' : 'Buat dan buka Vault' }}
      </UiButton>
    </form>
  </UiCard>

  <template v-else>
    <section
      class="vault-toolbar"
      aria-label="Cari dan filter Vault"
    >
      <UiInput
        v-model="search"
        label="Cari item"
        placeholder="Judul atau username"
        autocomplete="off"
      />
      <UiSelect
        v-model="category"
        label="Kategori"
        :options="categoryOptions"
      />
      <UiSelect
        v-model="sort"
        label="Urutkan"
        :options="sortOptions"
      />
      <UiButton
        class="add-entry"
        @click="openCreate"
      >
        <PhPlus :size="17" />
        Tambah item
      </UiButton>
    </section>

    <div class="vault-summary">
      <span>
        <strong>{{ entries.length }}</strong>
        item ditampilkan
      </span>
      <span>Auto-lock {{ autoLockMinutes }} menit</span>
      <span>Nilai tetap terenkripsi sampai kamu memilih Lihat atau Salin</span>
    </div>

    <UiErrorState
      v-if="actionError"
      :message="actionError"
    />
    <UiSkeleton
      v-if="listLoading"
      :lines="5"
      label="Memuat item Vault"
    />
    <UiErrorState
      v-else-if="listError"
      :message="listError"
      retryable
      @retry="loadEntries"
    />
    <UiEmptyState
      v-else-if="!entries.length"
      :title="search || category ? 'Tidak ada item yang cocok' : 'Vault masih kosong'"
      :description="
        search || category
          ? 'Ubah pencarian atau filter kategori.'
          : 'Tambahkan password, token, catatan, atau command penting pertamamu.'
      "
    >
      <template #icon>
        <PhKey
          :size="34"
          weight="duotone"
        />
      </template>
      <template #action>
        <UiButton
          v-if="!search && !category"
          @click="openCreate"
        >
          Tambah item pertama
        </UiButton>
      </template>
    </UiEmptyState>
    <UiDataTable
      v-else
      :rows="rows"
      :columns="columns"
      row-key="id"
      caption="Item Vault terenkripsi"
      :page-size="10"
    >
      <template #cell-title="{ row }">
        <div class="entry-title">
          <component
            :is="row.category === 'command' ? PhTerminalWindow : PhKey"
            :size="19"
          />
          <div>
            <strong>{{ row.title }}</strong>
            <a
              v-if="row.url"
              :href="row.url"
              target="_blank"
              rel="noreferrer"
            >
              {{ row.url }}
            </a>
            <span
              v-else-if="row.username"
              class="muted small"
            >
              {{ row.username }}
            </span>
          </div>
        </div>
      </template>
      <template #cell-category="{ row }">
        <UiBadge :tone="row.category === 'command' ? 'info' : 'neutral'">
          {{ categoryLabel(row.category) }}
        </UiBadge>
      </template>
      <template #cell-protectedValue="{ row }">
        <div
          v-if="revealed?.id === row.id"
          class="revealed-content"
        >
          <pre class="revealed-value"><code>{{ revealed.value }}</code></pre>
          <p
            v-if="revealed.notes"
            class="revealed-notes"
          >
            {{ revealed.notes }}
          </p>
        </div>
        <code
          v-else
          class="masked-value"
          aria-label="Nilai disembunyikan"
        >
          ••••••••
        </code>
      </template>
      <template #cell-last_accessed_at="{ row }">{{ dateLabel(row.last_accessed_at) }}</template>
      <template #cell-actions="{ row }">
        <div class="entry-actions">
          <UiButton
            size="sm"
            variant="secondary"
            :loading="copyBusy === row.id"
            :disabled="!!copyBusy"
            @click="copyEntry(row)"
          >
            <PhCopy :size="15" />
            Salin
          </UiButton>
          <UiButton
            size="sm"
            variant="ghost"
            :loading="revealBusy === row.id"
            :disabled="!!revealBusy"
            @click="toggleReveal(row)"
          >
            <component
              :is="revealed?.id === row.id ? PhEyeSlash : PhEye"
              :size="15"
            />
            {{ revealed?.id === row.id ? 'Sembunyikan' : 'Lihat' }}
          </UiButton>
          <UiButton
            size="sm"
            variant="ghost"
            @click="openEdit(row)"
          >
            <PhPencilSimple :size="15" />
            Edit
          </UiButton>
          <UiButton
            size="sm"
            variant="danger"
            @click="deleteTarget = row"
          >
            <PhTrash :size="15" />
            Hapus
          </UiButton>
        </div>
      </template>
    </UiDataTable>
  </template>

  <UiModal
    v-model="editorOpen"
    :title="editing ? 'Edit item Vault' : 'Tambah item Vault'"
    description="Password dan command menggunakan penyimpanan terenkripsi yang sama."
    size="lg"
    :dismissible="!editorBusy"
  >
    <form
      id="vault-entry-form"
      ref="editorForm"
      class="entry-form"
      @submit.prevent="saveEntry"
    >
      <div class="entry-grid">
        <UiInput
          v-model="form.title"
          label="Judul"
          required
          maxlength="255"
          autofocus
        />
        <UiSelect
          v-model="form.category"
          label="Kategori"
          :options="entryCategoryOptions"
          required
        />
      </div>
      <div
        v-if="!['command', 'note'].includes(form.category)"
        class="entry-grid"
      >
        <UiInput
          v-model="form.username"
          label="Username"
          maxlength="255"
          autocomplete="off"
        />
        <UiInput
          v-model="form.url"
          label="URL"
          type="url"
          maxlength="2048"
          placeholder="https://..."
          autocomplete="off"
        />
      </div>
      <UiTextarea
        v-if="form.category === 'command' || form.category === 'note'"
        v-model="form.value"
        :label="form.category === 'command' ? 'Command' : 'Isi catatan'"
        :hint="form.category === 'command' ? 'Bisa satu baris atau script multi-baris.' : undefined"
        rows="6"
        required
        maxlength="65536"
        spellcheck="false"
        class="mono-input"
      />
      <div
        v-else
        class="secret-editor"
      >
        <UiInput
          v-model="form.value"
          label="Nilai rahasia"
          :type="showEditorValue ? 'text' : 'password'"
          required
          maxlength="65536"
          autocomplete="new-password"
        />
        <UiButton
          variant="secondary"
          size="sm"
          @click="showEditorValue = !showEditorValue"
        >
          <component
            :is="showEditorValue ? PhEyeSlash : PhEye"
            :size="15"
          />
          {{ showEditorValue ? 'Sembunyikan' : 'Lihat nilai' }}
        </UiButton>
      </div>
      <details
        v-if="form.category === 'password'"
        class="generator-panel"
      >
        <summary>Generator password</summary>
        <div class="generator-content">
          <UiInput
            v-model="generatorLength"
            label="Panjang"
            type="number"
            min="12"
            max="64"
            inputmode="numeric"
          />
          <div class="generator-options">
            <UiCheckbox
              v-model="generator.uppercase"
              label="Huruf besar"
            />
            <UiCheckbox
              v-model="generator.lowercase"
              label="Huruf kecil"
            />
            <UiCheckbox
              v-model="generator.digits"
              label="Angka"
            />
            <UiCheckbox
              v-model="generator.symbols"
              label="Simbol"
            />
          </div>
          <UiButton
            variant="secondary"
            @click="generatePassword"
          >
            Buat password
          </UiButton>
        </div>
      </details>
      <UiTextarea
        v-model="form.notes"
        label="Catatan tambahan"
        hint="Catatan ini juga dienkripsi."
        rows="4"
        maxlength="65536"
      />
      <UiErrorState
        v-if="editorError"
        :message="editorError"
      />
    </form>
    <template #footer>
      <UiButton
        variant="secondary"
        :disabled="editorBusy"
        @click="editorOpen = false"
      >
        Batal
      </UiButton>
      <UiButton
        type="submit"
        form="vault-entry-form"
        :loading="editorBusy"
      >
        {{ editing ? 'Simpan perubahan' : 'Simpan item' }}
      </UiButton>
    </template>
  </UiModal>

  <UiConfirmDialog
    :model-value="!!deleteTarget"
    title="Hapus item Vault?"
    :description="`${deleteTarget?.title ?? 'Item'} akan dihapus permanen. Data terenkripsi ini tidak dapat dipulihkan.`"
    confirm-label="Hapus permanen"
    :busy="deleteBusy"
    :error="deleteError"
    @update:model-value="(open) => !open && (deleteTarget = undefined)"
    @confirm="removeEntry"
  />
</template>

<style scoped>
.vault-status,
.entry-actions,
.secret-editor {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.master-card {
  max-width: 560px;
}
.master-heading {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 28px;
}
.master-icon {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: var(--radius-control);
  color: var(--color-primary);
  background: var(--color-surface-subtle);
}
.master-form,
.entry-form {
  display: grid;
  gap: 20px;
}
.recovery-warning,
.lock-notice {
  display: grid;
  gap: 4px;
  padding: 14px 16px;
  margin-bottom: 20px;
  border-left: 4px solid var(--color-warning);
  background: color-mix(in srgb, var(--color-warning) 8%, var(--color-surface));
  color: var(--color-warning);
  font-size: 13px;
}
.vault-toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 1.5fr) minmax(160px, 0.7fr) minmax(170px, 0.7fr) auto;
  align-items: end;
  gap: 12px;
  margin-bottom: 16px;
}
.add-entry {
  margin-bottom: 1px;
}
.vault-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
  padding: 12px 16px;
  margin-bottom: 18px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  color: var(--color-text-muted);
  font-size: 12px;
}
.entry-title {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  max-width: 300px;
}
.entry-title > svg {
  margin-top: 2px;
  color: var(--color-primary);
}
.entry-title div {
  display: grid;
  gap: 3px;
  min-width: 0;
}
.entry-title strong,
.entry-title a {
  overflow: hidden;
  text-overflow: ellipsis;
}
.entry-title a {
  color: var(--color-primary);
  font-size: 12px;
  max-width: 260px;
}
.masked-value {
  color: var(--color-text-muted);
  letter-spacing: 0.18em;
}
.revealed-value {
  max-width: 360px;
  max-height: 130px;
  margin: 0;
  padding: 8px 10px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface-subtle);
  font-size: 12px;
}
.revealed-content {
  display: grid;
  gap: 6px;
}
.revealed-notes {
  max-width: 360px;
  margin: 0;
  color: var(--color-text-muted);
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}
.entry-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.secret-editor {
  align-items: end;
}
.secret-editor > :first-child {
  flex: 1 1 320px;
}
.generator-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
}
.generator-panel summary {
  padding: 12px 14px;
  font-size: 14px;
  font-weight: 500;
}
.generator-content {
  display: grid;
  grid-template-columns: 120px 1fr auto;
  align-items: end;
  gap: 16px;
  padding: 0 14px 14px;
}
.generator-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(120px, 1fr));
}
.mono-input :deep(textarea) {
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.6;
}
@media (max-width: 1000px) {
  .vault-toolbar {
    grid-template-columns: 1fr 1fr;
  }
  .add-entry {
    width: fit-content;
  }
  .generator-content {
    grid-template-columns: 110px 1fr;
  }
  .generator-content > :last-child {
    grid-column: 1 / -1;
    width: fit-content;
  }
}
@media (max-width: 640px) {
  .vault-toolbar,
  .entry-grid,
  .generator-content {
    grid-template-columns: 1fr;
  }
  .vault-toolbar .add-entry,
  .generator-content > :last-child {
    grid-column: auto;
    width: 100%;
  }
  .entry-actions {
    min-width: 260px;
  }
}
</style>
