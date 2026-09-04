<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ToolLayout from '../components/ToolLayout.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiSelect from '../../../shared/components/ui/UiSelect.vue'
import UiTextarea from '../../../shared/components/ui/UiTextarea.vue'
import UiCodeBlock from '../../../shared/components/ui/UiCodeBlock.vue'
import UiCopyButton from '../../../shared/components/ui/UiCopyButton.vue'
import UiConfirmDialog from '../../../shared/components/ui/UiConfirmDialog.vue'
import UiModal from '../../../shared/components/ui/UiModal.vue'
import { downloadFile, errorMessage } from '../../../shared/api'
import { fieldTypes, microApi, type DummyField, type Preset } from '../api'
import { blankField, useMicroStore } from '../store'
import { useToolWorker } from '../useToolWorker'
import type { DummyOutput } from '../dummy'
const state = useMicroStore().dummy
const { result, error, busy, run, cancel, reset } = useToolWorker<DummyOutput>()
const format = ref('json'),
  presets = ref<Preset[]>([]),
  presetId = ref(''),
  presetError = ref(''),
  presetNotice = ref('')
const presetBusy = ref(false),
  confirmDelete = ref(false),
  confirmLarge = ref(false)
const output = computed(() => result.value?.[format.value as 'json' | 'csv' | 'sql'] ?? '')
const selectedPreset = computed(() => presets.value.find((preset) => preset.id === presetId.value))
const fieldLabels: Record<DummyField['type'], string> = {
  full_name: 'Nama lengkap',
  first_name: 'Nama depan',
  last_name: 'Nama belakang',
  email: 'Email (.test)',
  phone: 'Telepon fiktif',
  address: 'Alamat',
  company: 'Perusahaan',
  uuid: 'UUID',
  integer: 'Integer',
  boolean: 'Boolean',
  date: 'Tanggal',
  lorem: 'Lorem ipsum',
  enum: 'Pilihan enum',
}
watch(() => [state.fields, state.count, state.seed, state.table], reset, { deep: true })
function generate(): void {
  confirmLarge.value = false
  run('dummy', state)
}
function requestGenerate(): void {
  if (state.count > 10000) confirmLarge.value = true
  else generate()
}
async function loadPresets(): Promise<void> {
  presetBusy.value = true
  presetError.value = ''
  try {
    presets.value = await microApi.presets()
  } catch (cause) {
    presetError.value = errorMessage(cause)
  } finally {
    presetBusy.value = false
  }
}
function applyPreset(): void {
  if (!selectedPreset.value) return
  state.fields = selectedPreset.value.fields.map((field) => ({ ...field }))
  state.presetName = selectedPreset.value.name
  presetNotice.value = 'Schema preset dimuat. Isi sebelumnya telah diganti; data belum dibuat.'
}
async function savePreset(): Promise<void> {
  presetBusy.value = true
  presetError.value = ''
  presetNotice.value = ''
  try {
    const preset = await microApi.savePreset(state.presetName, state.fields)
    presets.value = [...presets.value, preset].sort((a, b) => a.name.localeCompare(b.name))
    presetId.value = preset.id
    presetNotice.value = 'Preset tersimpan. Hanya schema field yang disimpan, bukan hasil data.'
  } catch (cause) {
    presetError.value = errorMessage(cause)
  } finally {
    presetBusy.value = false
  }
}
async function deletePreset(): Promise<void> {
  if (!selectedPreset.value) return
  presetBusy.value = true
  presetError.value = ''
  try {
    await microApi.deletePreset(presetId.value)
    presets.value = presets.value.filter((preset) => preset.id !== presetId.value)
    presetId.value = ''
    confirmDelete.value = false
    presetNotice.value = 'Preset dihapus. Schema pada form tetap ada.'
  } catch (cause) {
    presetError.value = errorMessage(cause)
  } finally {
    presetBusy.value = false
  }
}
function download(): void {
  downloadFile(
    new Blob([output.value], {
      type: format.value === 'csv' ? 'text/csv;charset=utf-8' : 'text/plain;charset=utf-8',
    }),
    `dummy-data.${format.value}`,
  )
}
onMounted(loadPresets)
</script>
<template>
  <ToolLayout
    title="Dummy Data"
    description="Tentukan field, buat data uji, lalu unduh JSON, CSV, atau SQL. Pembuatan data berlangsung lokal di browser."
  >
    <div class="tool-grid">
      <form
        class="tool-section"
        @submit.prevent="requestGenerate"
      >
        <div class="tool-actions">
          <h2>Schema field</h2>
          <UiButton
            variant="secondary"
            :disabled="state.fields.length >= 30 || busy"
            @click="state.fields.push(blankField(`field_${state.fields.length + 1}`))"
          >
            Tambah field
          </UiButton>
        </div>
        <fieldset
          class="dummy-fields"
          :disabled="busy"
        >
          <div
            v-for="(field, index) in state.fields"
            :key="index"
            class="dummy-field"
          >
            <div class="dummy-field-main">
              <UiInput
                v-model="field.name"
                :label="`Nama field ${index + 1}`"
                required
                maxlength="63"
                pattern="[A-Za-z_][A-Za-z0-9_]*"
              />
              <UiSelect
                v-model="field.type"
                :label="`Tipe field ${index + 1}`"
                :options="fieldTypes.map((value) => ({ value, label: fieldLabels[value] }))"
              />
              <UiButton
                variant="secondary"
                size="sm"
                :disabled="state.fields.length === 1"
                :label="`Hapus field ${index + 1}`"
                @click="state.fields.splice(index, 1)"
              >
                Hapus
              </UiButton>
            </div>
            <div
              v-if="field.type === 'integer'"
              class="tool-grid"
            >
              <UiInput
                :model-value="String(field.minimum)"
                label="Nilai minimum"
                type="number"
                min="-1000000000"
                max="1000000000"
                required
                @update:model-value="field.minimum = Number($event)"
              />
              <UiInput
                :model-value="String(field.maximum)"
                label="Nilai maksimum"
                type="number"
                min="-1000000000"
                max="1000000000"
                required
                @update:model-value="field.maximum = Number($event)"
              />
            </div>
            <div
              v-if="field.type === 'date'"
              class="tool-grid"
            >
              <UiInput
                v-model="field.start"
                label="Dari tanggal"
                type="date"
                required
              />
              <UiInput
                v-model="field.end"
                label="Sampai tanggal"
                type="date"
                required
              />
            </div>
            <UiTextarea
              v-if="field.type === 'enum'"
              v-model="field.choices"
              label="Pilihan enum"
              hint="Satu pilihan per baris; nilai kosong diabaikan."
              maxlength="2000"
              required
            />
          </div>
        </fieldset>
        <div class="tool-grid">
          <UiInput
            :model-value="String(state.count)"
            label="Jumlah baris"
            type="number"
            min="1"
            max="100000"
            required
            :disabled="busy"
            @update:model-value="state.count = Number($event)"
          />
          <UiInput
            v-model="state.seed"
            label="Seed (opsional)"
            maxlength="200"
            :disabled="busy"
            hint="Schema + seed yang sama menghasilkan data yang sama."
          />
        </div>
        <UiInput
          v-model="state.table"
          label="Nama tabel untuk ekspor SQL"
          maxlength="63"
          pattern="[A-Za-z_][A-Za-z0-9_]*"
          required
          :disabled="busy"
        />
        <p class="small muted">
          1–30 field, maksimal 100.000 baris / 1 juta sel / total output sekitar 20 MB. Locale en;
          data fiktif tidak dijamin unik. SQL hanya diunduh, tidak dieksekusi.
        </p>
        <p
          v-if="error"
          role="alert"
          class="field-error"
        >
          {{ error }}
        </p>
        <div class="tool-actions">
          <UiButton
            type="submit"
            :loading="busy"
          >
            Buat data
          </UiButton>
          <UiButton
            v-if="busy"
            variant="secondary"
            @click="cancel"
          >
            Batalkan
          </UiButton>
        </div>
        <details class="tool-details">
          <summary>Preset schema</summary>
          <div class="tool-section">
            <p class="small muted">
              Preset disimpan di database lokal (maks. 100). Jangan masukkan rahasia dalam nama
              field atau pilihan enum. Backup laporan QA tidak mencakup preset.
            </p>
            <UiInput
              v-model="state.presetName"
              label="Nama preset baru"
              maxlength="255"
            />
            <UiButton
              variant="secondary"
              :loading="presetBusy"
              :disabled="!state.presetName.trim() || busy"
              @click="savePreset"
            >
              Simpan schema sebagai preset
            </UiButton>
            <UiSelect
              v-model="presetId"
              label="Preset tersimpan"
              :disabled="presetBusy || busy"
              :options="[
                { value: '', label: 'Pilih preset' },
                ...presets.map((preset) => ({ value: preset.id, label: preset.name })),
              ]"
            />
            <div class="tool-actions">
              <UiButton
                variant="secondary"
                :disabled="!selectedPreset || presetBusy || busy"
                @click="applyPreset"
              >
                Muat schema ke form
              </UiButton>
              <UiButton
                variant="danger"
                :disabled="!selectedPreset || presetBusy"
                @click="confirmDelete = true"
              >
                Hapus preset
              </UiButton>
              <UiButton
                variant="secondary"
                :disabled="presetBusy"
                @click="loadPresets"
              >
                Muat ulang
              </UiButton>
            </div>
            <p
              v-if="presetError"
              role="alert"
              class="field-error"
            >
              {{ presetError }}
            </p>
            <p
              v-if="presetNotice"
              role="status"
            >
              {{ presetNotice }}
            </p>
          </div>
        </details>
      </form>
      <section
        class="tool-section"
        aria-label="Hasil dummy data"
      >
        <h2>Hasil data</h2>
        <p
          v-if="busy"
          role="status"
          class="tool-notice"
        >
          Membuat data di worker. Kamu dapat membatalkannya tanpa memengaruhi database.
        </p>
        <template v-else-if="result">
          <p role="status">
            {{ result.count.toLocaleString() }} baris · Seed:
            <code>{{ result.seed }}</code>
          </p>
          <div class="tool-actions">
            <UiSelect
              v-model="format"
              label="Format ekspor"
              :options="[
                { value: 'json', label: 'JSON' },
                { value: 'csv', label: 'CSV' },
                { value: 'sql', label: 'SQL INSERT (PostgreSQL)' },
              ]"
            />
            <UiCopyButton
              :value="output"
              label="Salin data"
            />
            <UiButton
              variant="secondary"
              @click="download"
            >
              Unduh {{ format.toUpperCase() }}
            </UiButton>
          </div>
          <UiCodeBlock
            :code="output.slice(0, 100000)"
            :label="format.toUpperCase()"
            :copyable="false"
          />
          <p
            v-if="output.length > 100000"
            class="small muted"
          >
            Pratinjau dibatasi 100.000 karakter. Salin/unduh mencakup seluruh data.
          </p>
          <p class="small muted">
            Simpan seed di atas bila ingin membuat ulang data. Seed kosong menghasilkan data baru
            setiap kali. CSV melindungi teks yang menyerupai formula dengan awalan apostrof.
          </p>
        </template>
        <p
          v-else
          class="tool-notice"
        >
          Isi schema, lalu pilih “Buat data”. Hasil tidak disimpan ke server.
        </p>
      </section>
    </div>
    <UiConfirmDialog
      v-model="confirmDelete"
      title="Hapus preset?"
      :description="`Preset ${selectedPreset?.name ?? ''} akan dihapus permanen. Schema pada form tetap ada.`"
      :busy="presetBusy"
      :error="presetError"
      @confirm="deletePreset"
    />
    <UiModal
      v-model="confirmLarge"
      title="Buat data dalam jumlah besar?"
      description="Lebih dari 10.000 baris dapat memerlukan beberapa detik dan memakai memori tambahan."
      size="sm"
    >
      <template #footer>
        <UiButton
          variant="secondary"
          @click="confirmLarge = false"
        >
          Batal
        </UiButton>
        <UiButton @click="generate">Lanjut buat data</UiButton>
      </template>
    </UiModal>
  </ToolLayout>
</template>
<style scoped>
.dummy-fields {
  border: 0;
  padding: 0;
  margin: 0;
  display: grid;
  min-width: 0;
}
.dummy-field {
  display: grid;
  gap: 16px;
  border-bottom: 1px solid var(--color-border);
  padding: 16px 0;
}
.dummy-field-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  gap: 12px;
  align-items: end;
}
@media (max-width: 580px) {
  .dummy-field-main {
    grid-template-columns: 1fr;
  }
}
</style>
