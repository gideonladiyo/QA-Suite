<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ToolLayout from '../components/ToolLayout.vue'
import PairEditor from '../components/PairEditor.vue'
import HttpCollections from '../components/HttpCollections.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiBadge from '../../../shared/components/ui/UiBadge.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiSelect from '../../../shared/components/ui/UiSelect.vue'
import UiTextarea from '../../../shared/components/ui/UiTextarea.vue'
import UiCheckbox from '../../../shared/components/ui/UiCheckbox.vue'
import UiCodeBlock from '../../../shared/components/ui/UiCodeBlock.vue'
import UiCopyButton from '../../../shared/components/ui/UiCopyButton.vue'
import UiConfirmDialog from '../../../shared/components/ui/UiConfirmDialog.vue'
import { downloadFile, errorMessage } from '../../../shared/api'
import { microApi, type HistoryEntry } from '../api'
import { useMicroStore } from '../store'
const store = useMicroStore()
const collectionsPanel = ref<{ clearLoadedRequest: () => void }>()
const responseTone = computed(() => {
  const status = store.response?.status ?? 0
  return status >= 400 || status === 0 ? 'danger' : status >= 300 ? 'warning' : 'success'
})
const draft = store.http
const history = ref<HistoryEntry[]>([])
const error = ref(''),
  historyError = ref(''),
  notice = ref('')
const showSecrets = ref(false),
  pretty = ref(true),
  showResponseHeaders = ref(false)
const clearing = ref(false),
  confirmClear = ref(false),
  historyBusy = ref(false)
const responseText = computed(() => {
  const body = store.response?.body ?? ''
  if (pretty.value && !store.response?.truncated) {
    try {
      return JSON.stringify(JSON.parse(body), null, 2)
    } catch {
      /* Text response stays text. */
    }
  }
  return body
})
function downloadResponse(): void {
  downloadFile(
    new Blob([responseText.value], { type: 'text/plain;charset=utf-8' }),
    'http-response.txt',
  )
}
async function refreshHistory(): Promise<void> {
  historyError.value = ''
  historyBusy.value = true
  try {
    history.value = await microApi.history()
  } catch (cause) {
    historyError.value = errorMessage(cause)
  } finally {
    historyBusy.value = false
  }
}
async function send(): Promise<void> {
  if (store.httpBusy) return
  const revision = store.revision
  error.value = ''
  notice.value = ''
  store.response = undefined
  store.httpBusy = true
  try {
    const result = await microApi.send(draft)
    if (store.revision !== revision) return
    store.response = result
    if (!result.history_saved)
      notice.value =
        'Respons diterima, tetapi riwayat gagal disimpan. Jangan kirim ulang hanya untuk menyimpan riwayat.'
    await refreshHistory()
  } catch (cause) {
    if (store.revision === revision)
      error.value = `${errorMessage(cause)} Jika koneksi terputus, endpoint mungkin sudah menerima request; periksa sebelum mengirim ulang.`
  } finally {
    if (store.revision === revision) store.httpBusy = false
  }
}
async function load(entry: HistoryEntry): Promise<void> {
  if (store.httpBusy || historyBusy.value) return
  historyBusy.value = true
  historyError.value = ''
  const revision = store.revision
  try {
    const saved = await microApi.loadHistory(entry.id)
    if (store.revision !== revision) return
    Object.assign(draft, saved, { allow_private: false })
    collectionsPanel.value?.clearLoadedRequest()
    showSecrets.value = false
    store.response = undefined
    notice.value =
      'Request dimuat, belum dikirim. Periksa URL/body dan aktifkan ulang izin lokal bila diperlukan.'
  } catch (cause) {
    historyError.value = errorMessage(cause)
  } finally {
    historyBusy.value = false
  }
}
function loadSaved(request: typeof draft, label: string): void {
  Object.assign(draft, request, { allow_private: false })
  showSecrets.value = false
  store.response = undefined
  error.value = ''
  notice.value = `${label} dimuat, belum dikirim. Periksa detail request sebelum mengirim.`
}
async function clearHistory(): Promise<void> {
  clearing.value = true
  historyError.value = ''
  try {
    await microApi.clearHistory()
    history.value = []
    confirmClear.value = false
  } catch (cause) {
    historyError.value = errorMessage(cause)
  } finally {
    clearing.value = false
  }
}
onMounted(refreshHistory)
</script>
<template>
  <ToolLayout
    title="HTTP Client"
    description="Susun request, kirim sekali, lalu periksa responsnya. Riwayat request disimpan terenkripsi di server lokal."
  >
    <HttpCollections
      ref="collectionsPanel"
      :draft="draft"
      :disabled="store.httpBusy || historyBusy"
      @load="loadSaved"
      @notice="notice = $event"
    />
    <div class="tool-grid">
      <form
        class="tool-section"
        @submit.prevent="send"
      >
        <h2>Request</h2>
        <fieldset
          :disabled="store.httpBusy"
          class="tool-section"
        >
          <div class="http-url-row">
            <UiSelect
              v-model="draft.method"
              label="Method"
              :options="
                ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((value) => ({ value, label: value }))
              "
            />
            <UiInput
              v-model="draft.url"
              label="URL endpoint"
              placeholder="https://api.example.test/items"
              required
              maxlength="8192"
              autocomplete="off"
              spellcheck="false"
            />
          </div>
          <p class="small muted">
            Request dikirim dari backend. Pastikan tujuan dan datanya benar, terutama untuk POST,
            PUT, PATCH, dan DELETE. Redirect tidak diikuti.
          </p>
          <details class="tool-details">
            <summary>Headers & autentikasi</summary>
            <div class="tool-section">
              <UiCheckbox
                v-model="showSecrets"
                label="Tampilkan nilai header, variabel, dan token"
              />
              <PairEditor
                v-model="draft.headers"
                label="Headers"
                :secret="!showSecrets"
              />
              <UiSelect
                v-model="draft.auth_type"
                label="Autentikasi"
                :options="[
                  { value: 'none', label: 'Tidak ada / header manual' },
                  { value: 'bearer', label: 'Bearer token' },
                  { value: 'basic', label: 'Basic Auth' },
                ]"
              />
              <UiInput
                v-if="draft.auth_type === 'bearer'"
                v-model="draft.token"
                label="Bearer token"
                :type="showSecrets ? 'text' : 'password'"
                autocomplete="off"
                maxlength="10000"
              />
              <template v-if="draft.auth_type === 'basic'">
                <UiInput
                  v-model="draft.username"
                  label="Username API"
                  autocomplete="off"
                  maxlength="255"
                />
                <UiInput
                  v-model="draft.password"
                  label="Password API"
                  :type="showSecrets ? 'text' : 'password'"
                  autocomplete="new-password"
                  maxlength="10000"
                />
              </template>
              <p
                v-if="draft.auth_type !== 'none'"
                class="small muted"
              >
                Helper ini menggantikan header Authorization manual.
              </p>
            </div>
          </details>
          <details
            class="tool-details"
            :open="!!draft.body"
          >
            <summary>Body request</summary>
            <div class="tool-section">
              <UiSelect
                v-model="draft.body_type"
                label="Format body"
                :options="[
                  { value: 'json', label: 'Raw JSON' },
                  { value: 'form', label: 'Form URL-encoded' },
                  { value: 'text', label: 'Teks' },
                ]"
              />
              <UiTextarea
                v-model="draft.body"
                label="Body"
                class="tool-code"
                rows="8"
                maxlength="524288"
                spellcheck="false"
                :hint="
                  draft.method === 'GET'
                    ? 'GET harus tanpa body.'
                    : draft.body_type === 'form'
                      ? 'Contoh: name=Gideon&message=hello%20world. Encode nilai form sebelum ditempel.'
                      : 'Maksimal 512 ribu karakter; 1 MB setelah substitusi.'
                "
              />
            </div>
          </details>
          <details class="tool-details">
            <summary>Variabel & pengaturan</summary>
            <div class="tool-section">
              <p class="small muted">
                Gunakan
                <code v-pre>{{ nama }}</code>
                pada URL, body, atau nilai autentikasi/header. Variabel tersimpan bersama request
                dalam riwayat terenkripsi.
              </p>
              <PairEditor
                v-model="draft.variables"
                label="Variabel"
                :secret="!showSecrets"
              />
              <div class="tool-grid">
                <UiInput
                  :model-value="String(draft.timeout)"
                  label="Timeout (detik)"
                  type="number"
                  min="1"
                  max="30"
                  required
                  @update:model-value="draft.timeout = Number($event)"
                />
                <UiInput
                  :model-value="String(draft.history_limit)"
                  label="Simpan N riwayat terakhir"
                  type="number"
                  min="1"
                  max="200"
                  required
                  @update:model-value="draft.history_limit = Number($event)"
                />
              </div>
              <UiCheckbox
                v-model="draft.allow_private"
                label="Izinkan endpoint localhost / LAN untuk request ini"
              />
              <p class="small muted">
                Aktifkan hanya untuk layanan milikmu. Di Docker, localhost berarti container
                backend; gunakan host.docker.internal untuk layanan host. Alamat metadata/link-local
                tetap ditolak.
              </p>
            </div>
          </details>
        </fieldset>
        <p
          v-if="error"
          role="alert"
          class="field-error"
        >
          {{ error }}
        </p>
        <p
          v-if="notice"
          role="status"
          class="tool-notice"
        >
          {{ notice }}
        </p>
        <div class="tool-actions">
          <UiButton
            type="submit"
            :loading="store.httpBusy"
            :disabled="!draft.url.trim() || historyBusy"
          >
            Kirim request
          </UiButton>
          <span
            v-if="store.httpBusy"
            role="status"
            class="small muted"
          >
            Menunggu respons; jangan kirim ulang.
          </span>
        </div>
      </form>
      <section
        class="tool-section"
        aria-labelledby="response-title"
      >
        <h2 id="response-title">Respons</h2>
        <p
          v-if="!store.response"
          class="tool-notice"
        >
          {{
            store.httpBusy
              ? 'Request sedang diproses…'
              : 'Belum ada respons. Isi URL lalu kirim request.'
          }}
        </p>
        <template v-else>
          <div
            class="http-metrics"
            role="status"
          >
            <UiBadge :tone="responseTone">
              HTTP
              <strong>{{ store.response.status ?? '—' }}</strong>
            </UiBadge>
            <span>{{ store.response.elapsed_ms.toLocaleString() }} ms</span>
            <span>{{ store.response.size_bytes.toLocaleString() }} byte diterima</span>
          </div>
          <p
            v-if="store.response.error"
            role="alert"
            class="field-error"
          >
            {{ store.response.error }}
          </p>
          <p
            v-if="store.response.truncated"
            role="alert"
            class="tool-notice"
          >
            Respons dipotong pada 2 MB. Salinan dan unduhan juga hanya berisi bagian ini.
          </p>
          <div class="tool-actions">
            <UiCheckbox
              v-model="pretty"
              label="Pretty JSON jika valid"
            />
            <UiCopyButton
              :value="responseText"
              label="Salin respons"
            />
            <UiButton
              variant="secondary"
              @click="downloadResponse"
            >
              Unduh .txt
            </UiButton>
          </div>
          <UiCodeBlock
            :code="responseText.slice(0, 100000) || '(body kosong)'"
            label="Body respons · teks UTF-8"
            :copyable="false"
          />
          <p
            v-if="responseText.length > 100000"
            class="small muted"
          >
            Pratinjau menampilkan 100.000 karakter pertama. Gunakan salin/unduh untuk seluruh
            respons yang diterima.
          </p>
          <details class="tool-details">
            <summary>Headers respons ({{ store.response.headers.length }})</summary>
            <UiCheckbox
              v-model="showResponseHeaders"
              label="Tampilkan nilai header respons (dapat berisi cookie/token)"
            />
            <UiCodeBlock
              :code="
                store.response.headers
                  .map(
                    (header) => `${header.key}: ${showResponseHeaders ? header.value : '••••••'}`,
                  )
                  .join('\n')
              "
              label="Headers respons"
              :copyable="showResponseHeaders"
            />
          </details>
          <p class="small muted">
            Respons hanya ada di memori tab, tidak disimpan dalam riwayat. Unduh hanya bila
            diperlukan.
          </p>
        </template>
      </section>
    </div>
    <section
      class="http-history tool-section"
      aria-labelledby="history-title"
    >
      <div class="tool-actions">
        <h2 id="history-title">Riwayat request</h2>
        <UiButton
          variant="secondary"
          :loading="historyBusy"
          :disabled="store.httpBusy || clearing"
          @click="refreshHistory"
        >
          Muat ulang
        </UiButton>
        <UiButton
          variant="danger"
          :disabled="!history.length || store.httpBusy || historyBusy"
          @click="confirmClear = true"
        >
          Hapus riwayat
        </UiButton>
      </div>
      <p class="small muted">
        Terbaru di atas. Detail sensitif disembunyikan; “Muat ke form” membuka request tanpa
        mengirimnya dan mengganti isian saat ini.
      </p>
      <p
        v-if="historyError"
        role="alert"
        class="field-error"
      >
        {{ historyError }}
      </p>
      <p v-if="!history.length && !historyBusy">Belum ada riwayat request.</p>
      <ol class="history-list">
        <li
          v-for="entry in history"
          :key="entry.id"
        >
          <div>
            <strong>{{ entry.method }}</strong>
            · {{ new Date(entry.created_at).toLocaleString('id-ID') }}
            <span class="small muted">
              HTTP {{ entry.response_status ?? 'gagal' }} · {{ entry.response_time_ms }} ms ·
              {{ entry.response_size_bytes.toLocaleString() }} byte
            </span>
          </div>
          <UiButton
            variant="secondary"
            size="sm"
            :disabled="store.httpBusy || historyBusy || clearing"
            @click="load(entry)"
          >
            Muat ke form
          </UiButton>
        </li>
      </ol>
    </section>
    <UiConfirmDialog
      v-model="confirmClear"
      title="Hapus seluruh riwayat HTTP?"
      description="Riwayat request terenkripsi akan dihapus permanen. Isian form saat ini tetap ada. Backup laporan QA tidak mencakup riwayat HTTP."
      :busy="clearing"
      :error="historyError"
      @confirm="clearHistory"
    />
  </ToolLayout>
</template>
<style scoped>
fieldset {
  border: 0;
  padding: 0;
  margin: 0;
  min-width: 0;
}
.http-url-row {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 12px;
}
.http-metrics {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  padding: 14px 0;
  border-block: 1px solid var(--color-border);
  font-family: var(--font-mono);
  font-size: 13px;
}
.http-history {
  margin-top: 40px;
  border-top: 1px solid var(--color-border);
  padding-top: 24px;
}
.history-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 440px;
  overflow: auto;
}
.history-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid var(--color-border);
}
.history-list li span {
  display: block;
  margin-top: 4px;
}
@media (max-width: 560px) {
  .http-url-row {
    grid-template-columns: 1fr;
  }
  .history-list li {
    align-items: start;
    flex-direction: column;
  }
}
</style>
