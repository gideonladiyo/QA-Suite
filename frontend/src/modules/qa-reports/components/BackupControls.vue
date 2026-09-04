<script setup lang="ts">
import { ref, useId } from 'vue'
import { qaApi, localDate } from '../api'
import { downloadFile, errorMessage } from '../../../shared/api'
import { useToast } from '../../../shared/composables/useToast'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiModal from '../../../shared/components/ui/UiModal.vue'
import UiErrorState from '../../../shared/components/ui/UiErrorState.vue'
const emit = defineEmits<{ restored: [] }>()
const { notify } = useToast()
const fileId = useId()
const busy = ref(false),
  error = ref(''),
  confirmOpen = ref(false),
  pending = ref(''),
  filename = ref(''),
  count = ref(0)
async function download(): Promise<void> {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    downloadFile(await qaApi.backup(), `qa-reports-backup-${localDate()}.json`)
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}
async function choose(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  pending.value = ''
  error.value = ''
  if (!file || busy.value) return
  busy.value = true
  try {
    if (file.size > 10 * 1024 * 1024) throw new Error('File backup maksimal 10 MB.')
    const text = (await file.text()).replace(/^\uFEFF/, '')
    const data: unknown = JSON.parse(text)
    if (
      !data ||
      typeof data !== 'object' ||
      !('format' in data) ||
      data.format !== 'qa-portal-reports' ||
      !('schema_version' in data) ||
      ![1, 2, 3].includes(Number(data.schema_version)) ||
      !('reports' in data) ||
      !Array.isArray(data.reports) ||
      data.reports.length > 1000
    )
      throw new Error('Gunakan JSON backup QA Reports versi 1, 2, atau 3 (maksimal 1.000 laporan).')
    count.value = data.reports.length
    filename.value = file.name
    pending.value = text
    confirmOpen.value = true
  } catch (cause) {
    error.value = cause instanceof SyntaxError ? 'File bukan JSON yang valid.' : errorMessage(cause)
  } finally {
    busy.value = false
  }
}
async function restore(): Promise<void> {
  if (!pending.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const result = await qaApi.restore(pending.value)
    confirmOpen.value = false
    pending.value = ''
    notify(
      `${result.restored} laporan dipulihkan; ${result.skipped} tanggal yang sudah ada dilewati.`,
    )
    emit('restored')
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <details class="backup-tools">
    <summary>Backup &amp; pemulihan</summary>
    <div class="stack">
      <p class="small muted">
        Backup seluruh laporan, template, aktivitas, dan coverage ke JSON, bukan hanya hasil filter.
        Tanpa akun, password, atau sesi login. File tidak dienkripsi—simpan di tempat aman. Maksimal
        1.000 laporan / 10 MB.
      </p>
      <div class="qa-actions">
        <UiButton
          variant="secondary"
          :loading="busy"
          @click="download"
        >
          Unduh backup JSON
        </UiButton>
      </div>
      <div>
        <label :for="fileId">Pulihkan dari backup JSON</label>
        <input
          :id="fileId"
          type="file"
          accept=".json,application/json"
          :disabled="busy"
          @change="choose"
        />
      </div>
      <UiErrorState
        v-if="error && !confirmOpen"
        :message="error"
      />
    </div>
  </details>
  <UiModal
    v-model="confirmOpen"
    title="Pulihkan laporan dari backup?"
    :description="`${filename}: ${count} laporan. Tanggal dan nama template yang sudah ada akan dilewati, tidak ditimpa. Seluruh file divalidasi sebelum data disimpan. ID laporan yang dipulihkan akan dibuat baru.`"
    :dismissible="!busy"
    size="sm"
  >
    <UiErrorState
      v-if="error"
      :message="error"
    />
    <template #footer>
      <UiButton
        variant="secondary"
        :disabled="busy"
        @click="confirmOpen = false"
      >
        Batal
      </UiButton>
      <UiButton
        :loading="busy"
        @click="restore"
      >
        Pulihkan laporan
      </UiButton>
    </template>
  </UiModal>
</template>
<style scoped>
.backup-tools {
  border-top: 1px solid var(--color-border);
  padding-top: 20px;
}
summary {
  cursor: pointer;
  padding: 12px 0;
  font-weight: 500;
}
.stack {
  margin-top: 12px;
}
label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
}
input {
  width: 100%;
  min-height: 44px;
  font-size: 14px;
}
</style>
