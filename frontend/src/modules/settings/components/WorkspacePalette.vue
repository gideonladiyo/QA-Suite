<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useUiStore } from '../../../shared/stores/ui'
import {
  defaultPalette,
  importPalette,
  loadSavedPalettes,
  normalizeHex,
  normalizePalette,
  palettePresets,
  paletteRoles,
  paletteTokens,
  savedPalettesLimit,
  samePalette,
  storeSavedPalettes,
  type Palette,
  type SavedPalette,
} from '../../../shared/palettes'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiCard from '../../../shared/components/ui/UiCard.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiTextarea from '../../../shared/components/ui/UiTextarea.vue'
import UiConfirmDialog from '../../../shared/components/ui/UiConfirmDialog.vue'
import UiModal from '../../../shared/components/ui/UiModal.vue'

const savedPaletteRoles = [
  { key: 'ink', label: 'Primary', hint: 'Tombol utama dan navigasi aktif.' },
  { key: 'violet', label: 'Secondary', hint: 'Penanda dan elemen pendukung.' },
  { key: 'mauve', label: 'Accent', hint: 'Penekanan tambahan.' },
  { key: 'blush', label: 'Highlight', hint: 'Sorotan dan permukaan lembut.' },
] as const

const ui = useUiStore()
const draft = ref<Palette>({ ...(ui.colorPalette ?? defaultPalette) })
const imported = ref('')
const importError = ref('')
const feedback = ref('')
const submitted = ref(false)
const customSection = ref<HTMLDetailsElement>()
const savedPalettes = ref(loadSavedPalettes())
const editorOpen = ref(false)
const editorId = ref<string | null>(null)
const editorName = ref('')
const editorDraft = ref<Palette>({ ...defaultPalette })
const editorSubmitted = ref(false)
const editorNameError = ref('')
const editorError = ref('')
const editorForm = ref<HTMLFormElement>()
const libraryError = ref('')
const libraryFeedback = ref('')
const deleteTarget = ref<SavedPalette | null>(null)
const normalized = computed(() => normalizePalette(draft.value))
const isOriginal = computed(() => normalized.value && samePalette(normalized.value, defaultPalette))
const previewStyle = computed(() =>
  isOriginal.value
    ? {}
    : paletteTokens(
        normalized.value ?? ui.colorPalette ?? defaultPalette,
        ui.resolvedTheme === 'dark',
      ),
)
const dirty = computed(
  () => !normalized.value || !samePalette(normalized.value, ui.colorPalette ?? defaultPalette),
)
const activeName = computed(() => {
  const active = ui.colorPalette ?? defaultPalette
  return (
    palettePresets.find((preset) => samePalette(preset.colors, active))?.name ??
    savedPalettes.value.find((palette) => samePalette(palette.colors, active))?.name ??
    'Custom'
  )
})
function choose(colors: Palette): void {
  draft.value = { ...colors }
  submitted.value = false
  feedback.value = ''
  libraryError.value = ''
  libraryFeedback.value = ''
}
function previewSaved(palette: SavedPalette): void {
  choose(palette.colors)
  libraryFeedback.value = `${palette.name} dimuat ke preview. Klik Terapkan palet untuk mengaktifkannya.`
}
function openPaletteEditor(palette?: SavedPalette): void {
  editorId.value = palette?.id ?? null
  editorName.value = palette?.name ?? ''
  editorDraft.value = { ...(palette?.colors ?? normalized.value ?? defaultPalette) }
  editorSubmitted.value = false
  editorNameError.value = ''
  editorError.value = ''
  editorOpen.value = true
}
function savePalette(): void {
  editorSubmitted.value = true
  const name = editorName.value.trim()
  const colors = normalizePalette(editorDraft.value)
  editorNameError.value = ''
  editorError.value = ''
  if (!name) {
    editorNameError.value = 'Isi nama palet sebelum menyimpan.'
    return
  }
  if (!colors) {
    editorError.value = 'Periksa keempat kode HEX sebelum menyimpan.'
    void nextTick(() =>
      editorForm.value?.querySelector<HTMLInputElement>('[aria-invalid="true"]')?.focus(),
    )
    return
  }
  const duplicate = savedPalettes.value.find(
    (palette) =>
      palette.id !== editorId.value &&
      palette.name.toLocaleLowerCase('id-ID') === name.toLocaleLowerCase('id-ID'),
  )
  if (duplicate) {
    editorNameError.value = 'Nama palet sudah digunakan. Pilih nama lain.'
    return
  }
  if (!editorId.value && savedPalettes.value.length >= savedPalettesLimit) {
    editorError.value = `Maksimal ${savedPalettesLimit} palet tersimpan. Hapus satu palet terlebih dahulu.`
    return
  }
  const id =
    editorId.value ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
  const updating = !!editorId.value
  const saved = { id, name, colors: { ...colors } }
  const next = updating
    ? savedPalettes.value.map((palette) => (palette.id === id ? saved : palette))
    : [...savedPalettes.value, saved]
  if (!storeSavedPalettes(next)) {
    editorError.value = 'Browser tidak mengizinkan penyimpanan palet.'
    return
  }
  savedPalettes.value = next
  editorOpen.value = false
  libraryFeedback.value = `${name} ${updating ? 'diperbarui' : 'disimpan'}.`
}
function deleteSaved(): void {
  if (!deleteTarget.value) return
  const target = deleteTarget.value
  const next = savedPalettes.value.filter((palette) => palette.id !== target.id)
  if (!storeSavedPalettes(next)) {
    libraryError.value = 'Browser tidak mengizinkan perubahan palet tersimpan.'
    deleteTarget.value = null
    return
  }
  savedPalettes.value = next
  libraryFeedback.value = `${target.name} dihapus dari browser ini.`
  libraryError.value = ''
  deleteTarget.value = null
}
function loadImport(): void {
  try {
    choose(importPalette(imported.value))
    importError.value = ''
    feedback.value = 'Empat warna dimuat dari gelap ke terang. Periksa perannya, lalu terapkan.'
  } catch (cause) {
    importError.value = cause instanceof Error ? cause.message : 'Palet belum dapat dibaca.'
  }
}
function apply(): void {
  submitted.value = true
  if (!normalized.value) {
    if (customSection.value) customSection.value.open = true
    void nextTick(() =>
      customSection.value?.querySelector<HTMLInputElement>('[aria-invalid="true"]')?.focus(),
    )
    return
  }
  if (ui.setColorPalette(normalized.value)) {
    draft.value = { ...normalized.value }
    feedback.value = ui.colorPaletteError ? '' : 'Palet diterapkan dan tersimpan di browser ini.'
  }
}
watch(
  () => ui.colorPalette,
  (value) => {
    draft.value = { ...(value ?? defaultPalette) }
  },
)
</script>

<template>
  <section
    aria-labelledby="workspace-palette-heading"
    class="stack workspace-palette"
  >
    <div>
      <h2 id="workspace-palette-heading">Identitas workspace</h2>
      <p class="muted small mt-2">
        Pilih preset atau buat palet sendiri. Perubahan tampil di preview sebelum diterapkan.
      </p>
    </div>
    <div
      class="palette-presets"
      role="group"
      aria-label="Preset palet warna"
    >
      <UiCard
        v-for="preset in palettePresets"
        :key="preset.name"
        interactive
        padding="sm"
        :aria-pressed="!!normalized && samePalette(normalized, preset.colors)"
        :class="{ 'preset-selected': normalized && samePalette(normalized, preset.colors) }"
        @click="choose(preset.colors)"
      >
        <span
          class="preset-colors"
          aria-hidden="true"
        >
          <span
            v-for="{ key } in paletteRoles"
            :key="key"
            :style="{ backgroundColor: preset.colors[key] }"
          />
        </span>
        <strong>{{ preset.name }}</strong>
        <span class="preset-state">
          {{ normalized && samePalette(normalized, preset.colors) ? 'Dipilih' : 'Pilih palet' }}
        </span>
      </UiCard>
    </div>
    <form
      class="stack"
      novalidate
      @submit.prevent="apply"
    >
      <details
        ref="customSection"
        class="palette-custom"
      >
        <summary>Sesuaikan warna atau impor palet</summary>
        <div class="stack mt-4">
          <div class="palette-fields">
            <div
              v-for="role in paletteRoles"
              :key="role.key"
              class="palette-color-field"
            >
              <input
                type="color"
                class="color-picker"
                :aria-label="`Pilih warna ${role.label}`"
                :value="normalizeHex(draft[role.key]) ?? defaultPalette[role.key]"
                @input="draft[role.key] = ($event.target as HTMLInputElement).value"
              />
              <UiInput
                v-model="draft[role.key]"
                :label="role.label"
                :hint="role.hint"
                maxlength="7"
                :error="
                  submitted && !normalizeHex(draft[role.key])
                    ? 'Gunakan HEX, misalnya #1565C0.'
                    : undefined
                "
                spellcheck="false"
                autocomplete="off"
              />
            </div>
          </div>
          <div class="palette-import stack">
            <UiTextarea
              v-model="imported"
              label="Tempel palet"
              :rows="2"
              maxlength="2000"
              :error="importError || undefined"
              placeholder="#1565C0 #00838F #5E35B1 #B3E5FC"
              hint="4 kode HEX dipisahkan spasi/koma, atau tautan Color Hunt/Coolors berisi 4 warna. Warna diurutkan dari gelap ke terang; perannya bisa kamu ubah di atas."
            />
            <div>
              <UiButton
                variant="secondary"
                @click="loadImport"
              >
                Muat ke preview
              </UiButton>
            </div>
            <p class="small muted">
              Cari inspirasi di
              <a
                class="palette-link"
                href="https://colorhunt.co/"
                target="_blank"
                rel="noopener noreferrer"
              >
                Color Hunt
              </a>
              atau
              <a
                class="palette-link"
                href="https://m2.material.io/design/color/the-color-system.html"
                target="_blank"
                rel="noopener noreferrer"
              >
                Material Design dari Google
              </a>
              . Impor hanya membaca kode warna, tidak membuka tautan atau mengunduh tema.
            </p>
          </div>
        </div>
      </details>
      <div
        class="palette-preview"
        aria-label="Preview palet"
        :style="previewStyle"
        :data-theme="ui.resolvedTheme"
        :data-palette="isOriginal ? 'original' : undefined"
      >
        <div class="stack preview-content">
          <span class="small muted">
            Preview · {{ ui.resolvedTheme === 'dark' ? 'Gelap' : 'Terang' }}
          </span>
          <h3>Workspace kamu</h3>
          <p class="small muted">
            Teks dan aksen mengikuti palet. Warna tombol disesuaikan agar tetap terbaca.
          </p>
          <span class="preview-highlight">Contoh sorotan</span>
        </div>
        <UiButton type="submit">Terapkan palet</UiButton>
      </div>
      <p
        v-if="submitted && !normalized"
        class="field-error"
        role="alert"
      >
        Periksa kode warna di bagian Sesuaikan warna sebelum menerapkan palet.
      </p>
      <div class="palette-footer">
        <p
          class="small muted"
          role="status"
        >
          Palet aktif: {{ activeName }}. {{ dirty ? 'Preview belum diterapkan.' : feedback }}
        </p>
        <UiButton
          v-if="dirty"
          variant="ghost"
          @click="choose(ui.colorPalette ?? defaultPalette)"
        >
          Batalkan perubahan
        </UiButton>
      </div>
      <p
        v-if="importError === '' && dirty && feedback"
        class="small muted"
        role="status"
      >
        {{ feedback }}
      </p>
      <p
        v-if="ui.colorPaletteError"
        class="field-error"
        role="alert"
      >
        {{ ui.colorPaletteError }}
      </p>
    </form>
    <section
      class="saved-palettes stack"
      aria-labelledby="saved-palettes-heading"
    >
      <div class="saved-palettes-header">
        <div>
          <h3 id="saved-palettes-heading">Palet tersimpan</h3>
          <p class="small muted mt-2">
            Buat beberapa identitas warna dan gunakan kembali kapan saja.
          </p>
        </div>
        <UiButton @click="openPaletteEditor()">Tambah palet</UiButton>
      </div>
      <p
        v-if="libraryError"
        class="field-error"
        role="alert"
      >
        {{ libraryError }}
      </p>
      <p
        v-if="libraryFeedback"
        class="small muted"
        role="status"
      >
        {{ libraryFeedback }}
      </p>
      <p
        v-if="savedPalettes.length === 0"
        class="saved-empty small muted"
      >
        Belum ada palet tersimpan. Klik Tambah palet untuk membuat palet pertama.
      </p>
      <ul
        v-else
        class="saved-palette-list"
        aria-label="Daftar palet tersimpan"
      >
        <li
          v-for="palette in savedPalettes"
          :key="palette.id"
          class="saved-palette-row"
        >
          <div class="saved-palette-identity">
            <span
              class="saved-palette-colors"
              aria-hidden="true"
            >
              <span
                v-for="{ key } in paletteRoles"
                :key="key"
                :style="{ backgroundColor: palette.colors[key] }"
              />
            </span>
            <strong>{{ palette.name }}</strong>
          </div>
          <div class="saved-palette-actions">
            <UiButton
              size="sm"
              variant="secondary"
              :aria-label="`Gunakan palet ${palette.name}`"
              @click="previewSaved(palette)"
            >
              Gunakan
            </UiButton>
            <UiButton
              size="sm"
              variant="ghost"
              :aria-label="`Edit palet ${palette.name}`"
              @click="openPaletteEditor(palette)"
            >
              Edit
            </UiButton>
            <UiButton
              size="sm"
              variant="danger"
              :aria-label="`Hapus palet ${palette.name}`"
              @click="deleteTarget = palette"
            >
              Hapus
            </UiButton>
          </div>
        </li>
      </ul>
    </section>
    <p class="small muted">
      Palet aktif dan daftar palet tersimpan hanya ada di browser ini, bukan database. Pilih Portal
      original lalu Terapkan palet untuk kembali ke warna awal. Warna status sukses, peringatan, dan
      error tidak diubah.
    </p>
    <UiModal
      v-model="editorOpen"
      :title="editorId ? 'Edit palet' : 'Tambah palet'"
      description="Isi nama dan empat warna identitas workspace."
      size="md"
    >
      <form
        id="saved-palette-editor-form"
        ref="editorForm"
        class="stack palette-editor-form"
        novalidate
        @submit.prevent="savePalette"
      >
        <UiInput
          v-model="editorName"
          label="Nama palet"
          maxlength="60"
          :error="editorNameError || undefined"
          placeholder="Contoh: Brand marketing"
          autocomplete="off"
          autofocus
        />
        <div class="palette-fields">
          <div
            v-for="role in savedPaletteRoles"
            :key="role.key"
            class="palette-color-field"
          >
            <input
              type="color"
              class="color-picker"
              :aria-label="`Pilih warna ${role.label}`"
              :value="normalizeHex(editorDraft[role.key]) ?? defaultPalette[role.key]"
              @input="editorDraft[role.key] = ($event.target as HTMLInputElement).value"
            />
            <UiInput
              v-model="editorDraft[role.key]"
              :label="role.label"
              :hint="role.hint"
              maxlength="7"
              :error="
                editorSubmitted && !normalizeHex(editorDraft[role.key])
                  ? 'Gunakan HEX, misalnya #1565C0.'
                  : undefined
              "
              spellcheck="false"
              autocomplete="off"
            />
          </div>
        </div>
        <p
          v-if="editorError"
          class="field-error"
          role="alert"
        >
          {{ editorError }}
        </p>
      </form>
      <template #footer>
        <UiButton
          variant="secondary"
          @click="editorOpen = false"
        >
          Batal
        </UiButton>
        <UiButton
          type="submit"
          form="saved-palette-editor-form"
        >
          {{ editorId ? 'Simpan perubahan' : 'Simpan palet' }}
        </UiButton>
      </template>
    </UiModal>
    <UiConfirmDialog
      :model-value="!!deleteTarget"
      title="Hapus palet tersimpan?"
      :description="
        deleteTarget
          ? `${deleteTarget.name} akan dihapus dari browser ini. Palet yang sedang aktif tidak berubah.`
          : ''
      "
      confirm-label="Hapus palet"
      @update:model-value="(open) => !open && (deleteTarget = null)"
      @confirm="deleteSaved"
    />
  </section>
</template>

<style scoped>
.workspace-palette {
  gap: 24px;
}
.palette-presets {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}
.palette-presets :deep(.ui-card) {
  min-width: 0;
}
.preset-colors {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
}
.preset-colors span {
  flex: 1;
  height: 24px;
  border-radius: 4px;
  border: 1px solid var(--color-border);
}
.palette-presets strong {
  font-size: 13px;
}
.preset-state {
  display: block;
  color: var(--color-text-muted);
  font-size: 12px;
  margin-top: 6px;
}
.preset-selected {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
.palette-custom summary {
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  padding: 12px 0;
}
.palette-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}
.palette-color-field {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  align-items: start;
  gap: 12px;
}
.color-picker {
  width: 44px;
  height: 44px;
  padding: 3px;
  margin-top: 25px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  cursor: pointer;
}
.palette-import {
  border-top: 1px solid var(--color-border);
  padding-top: 20px;
  gap: 12px;
}
.palette-link {
  color: var(--color-primary);
  text-decoration: underline;
  text-underline-offset: 3px;
}
.palette-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
  padding: 24px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-panel);
  background: var(--color-surface);
  color: var(--color-text);
}
.preview-content {
  gap: 10px;
  flex: 1 1 230px;
  min-width: 0;
}
.palette-preview h3 {
  color: var(--color-primary);
  font-size: 18px;
}
.preview-highlight {
  background: var(--color-blush);
  color: var(--color-on-blush);
  padding: 5px 8px;
  font-size: 12px;
  width: fit-content;
  border-radius: 4px;
}
.palette-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.saved-palettes {
  gap: 16px;
  padding-top: 24px;
  border-top: 1px solid var(--color-border);
}
.saved-palettes h3 {
  font-size: 18px;
}
.saved-palettes-header,
.saved-palette-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.palette-editor-form {
  gap: 20px;
}
.saved-empty {
  padding: 20px;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-panel);
}
.saved-palette-list {
  list-style: none;
  padding: 0;
  border-top: 1px solid var(--color-border);
}
.saved-palette-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border);
}
.saved-palette-identity {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.saved-palette-identity strong {
  overflow-wrap: anywhere;
}
.saved-palette-colors {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  height: 28px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 4px;
}
@media (max-width: 600px) {
  .palette-presets {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .palette-fields {
    grid-template-columns: minmax(0, 1fr);
  }
  .palette-preview {
    padding: 20px;
  }
  .saved-palette-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
