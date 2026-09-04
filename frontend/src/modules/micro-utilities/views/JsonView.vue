<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'
import ToolLayout from '../components/ToolLayout.vue'
import JsonTree from '../components/JsonTree.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiSelect from '../../../shared/components/ui/UiSelect.vue'
import UiTextarea from '../../../shared/components/ui/UiTextarea.vue'
import UiCheckbox from '../../../shared/components/ui/UiCheckbox.vue'
import UiCodeBlock from '../../../shared/components/ui/UiCodeBlock.vue'
import UiCopyButton from '../../../shared/components/ui/UiCopyButton.vue'
import { downloadFile } from '../../../shared/api'
import { useMicroStore } from '../store'
import { useToolWorker } from '../useToolWorker'
import type { JsonOutput } from '../json'
const state = useMicroStore().json
const { result, error, busy, run, reset } = useToolWorker<JsonOutput>()
let timer: ReturnType<typeof setTimeout> | undefined
watch(
  () => [state.input, state.source, state.target, state.indent, state.sort],
  () => {
    clearTimeout(timer)
    reset()
    if (state.input.trim()) timer = setTimeout(() => run('json', state), 300)
  },
  { immediate: true },
)
onBeforeUnmount(() => clearTimeout(timer))
function download(): void {
  if (result.value)
    downloadFile(
      new Blob([result.value.output], { type: 'text/plain;charset=utf-8' }),
      `formatted.${state.target === 'yaml' ? 'yaml' : 'json'}`,
    )
}
</script>
<template>
  <ToolLayout
    title="JSONizer"
    description="Format, validasi, konversi, dan jelajahi struktur data. Seluruh pemrosesan tetap di browser."
  >
    <div class="tool-grid">
      <section
        class="tool-section"
        aria-label="Input JSONizer"
      >
        <h2>Input</h2>
        <div class="tool-actions">
          <UiSelect
            v-model="state.source"
            label="Format input"
            :options="[
              { value: 'json', label: 'JSON' },
              { value: 'yaml', label: 'YAML' },
            ]"
          />
          <UiButton
            variant="secondary"
            :disabled="!state.input"
            @click="state.input = ''"
          >
            Kosongkan input
          </UiButton>
        </div>
        <UiTextarea
          v-model="state.input"
          label="Data sumber"
          class="tool-code"
          rows="18"
          spellcheck="false"
          maxlength="2097152"
          hint="Maksimal 2 MB UTF-8, 100.000 nilai, kedalaman 64. Tidak dikirim ke server."
        />
        <p
          v-if="error"
          role="alert"
          class="field-error"
        >
          {{ error }}
        </p>
      </section>
      <section
        class="tool-section"
        aria-label="Hasil JSONizer"
      >
        <h2>Hasil</h2>
        <div class="tool-actions">
          <UiSelect
            v-model="state.target"
            label="Format output"
            :options="[
              { value: 'json', label: 'Pretty JSON' },
              { value: 'minify', label: 'Minified JSON' },
              { value: 'yaml', label: 'YAML' },
            ]"
          />
          <UiSelect
            v-model="state.indent"
            label="Indentasi"
            :options="[
              { value: '2', label: '2 spasi' },
              { value: '4', label: '4 spasi' },
            ]"
          />
          <UiCheckbox
            v-model="state.sort"
            label="Urutkan key rekursif"
          />
        </div>
        <p
          v-if="busy"
          role="status"
        >
          Memproses data…
        </p>
        <template v-else-if="result">
          <div class="tool-actions">
            <UiCopyButton
              :value="result.output"
              label="Salin output"
            />
            <UiCopyButton
              :value="result.minified"
              label="Salin minified JSON"
            />
            <UiButton
              variant="secondary"
              @click="download"
            >
              Unduh
            </UiButton>
          </div>
          <UiCheckbox
            v-model="state.tree"
            label="Tampilkan tree"
          />
          <template v-if="state.tree">
            <UiInput
              v-model="state.search"
              label="Cari key atau nilai"
              type="search"
              maxlength="200"
            />
            <JsonTree
              :nodes="result.nodes"
              :search="state.search"
            />
          </template>
          <template v-else>
            <UiCodeBlock
              :code="result.output.slice(0, 100000)"
              :label="state.target === 'yaml' ? 'YAML' : 'JSON'"
              :copyable="false"
            />
            <p
              v-if="result.output.length > 100000"
              class="small muted"
            >
              Pratinjau dibatasi 100.000 karakter. Salin/unduh mencakup seluruh output.
            </p>
          </template>
        </template>
        <p
          v-else
          class="tool-notice"
        >
          {{
            error
              ? 'Perbaiki input untuk melihat hasil.'
              : 'Tempel data pada kolom input. Hasil diperbarui otomatis.'
          }}
        </p>
      </section>
    </div>
    <p class="small muted json-note">
      Konversi mempertahankan nilai JSON standar, bukan komentar/anchor YAML. Angka mengikuti
      presisi Number JavaScript; simpan ID panjang sebagai string.
    </p>
  </ToolLayout>
</template>
<style scoped>
.json-note {
  margin-top: 24px;
}
</style>
