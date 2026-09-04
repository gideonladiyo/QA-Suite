<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useUiStore } from '../../../shared/stores/ui'
import {
  defaultPalette,
  importPalette,
  normalizeHex,
  normalizePalette,
  palettePresets,
  paletteRoles,
  paletteTokens,
  samePalette,
  type Palette,
} from '../../../shared/palettes'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiCard from '../../../shared/components/ui/UiCard.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiTextarea from '../../../shared/components/ui/UiTextarea.vue'

const ui = useUiStore()
const draft = ref<Palette>({ ...(ui.colorPalette ?? defaultPalette) })
const imported = ref('')
const importError = ref('')
const feedback = ref('')
const submitted = ref(false)
const customSection = ref<HTMLDetailsElement>()
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
const activeName = computed(
  () =>
    palettePresets.find((preset) => samePalette(preset.colors, ui.colorPalette ?? defaultPalette))
      ?.name ?? 'Custom',
)
function choose(colors: Palette): void {
  draft.value = { ...colors }
  submitted.value = false
  feedback.value = ''
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
    <p class="small muted">
      Palet tersimpan hanya di browser ini, bukan database. Pilih Portal original lalu Terapkan
      palet untuk kembali ke warna awal. Warna status sukses, peringatan, dan error tidak diubah.
    </p>
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
}
</style>
