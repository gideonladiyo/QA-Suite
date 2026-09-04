<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { downloadFile, errorMessage } from '../../../shared/api'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiConfirmDialog from '../../../shared/components/ui/UiConfirmDialog.vue'
import UiDataTable from '../../../shared/components/ui/UiDataTable.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiModal from '../../../shared/components/ui/UiModal.vue'
import UiSelect from '../../../shared/components/ui/UiSelect.vue'
import UiTextarea from '../../../shared/components/ui/UiTextarea.vue'
import { microApi, type HttpCollection, type HttpDraft, type SavedRequest } from '../api'

const props = withDefaults(defineProps<{ draft: HttpDraft; disabled?: boolean }>(), {
  disabled: false,
})
const emit = defineEmits<{
  load: [request: HttpDraft, label: string]
  notice: [message: string]
}>()

const collections = ref<HttpCollection[]>([])
const requests = ref<SavedRequest[]>([])
const selectedCollectionId = ref('')
const loadedRequest = ref<SavedRequest>()
const busy = ref(false)
const error = ref('')
const collectionModal = ref(false)
const requestModal = ref(false)
const confirmDelete = ref(false)
const editingCollection = ref<HttpCollection>()
const deleting = ref<{ type: 'collection' | 'request'; id: string; name: string }>()
const collectionName = ref('')
const collectionDescription = ref('')
const requestName = ref('')
const requestCollectionId = ref('')
const importInput = ref<HTMLInputElement>()

function clearLoadedRequest(): void {
  loadedRequest.value = undefined
}
defineExpose({ clearLoadedRequest })

const selectedCollection = computed(() =>
  collections.value.find((entry) => entry.id === selectedCollectionId.value),
)
const collectionOptions = computed(() =>
  collections.value.map((entry) => ({ value: entry.id, label: entry.name })),
)
const collectionColumns = [
  { key: 'name', label: 'Collection', sortable: true },
  { key: 'request_count', label: 'Request', sortable: true },
  { key: 'updated_at', label: 'Diperbarui', sortable: true },
  { key: 'id', label: 'Aksi' },
] as const
const requestColumns = [
  { key: 'method', label: 'Method', sortable: true },
  { key: 'name', label: 'Request', sortable: true },
  { key: 'updated_at', label: 'Diperbarui', sortable: true },
  { key: 'id', label: 'Aksi' },
] as const

async function refreshCollections(selectId = selectedCollectionId.value): Promise<void> {
  error.value = ''
  busy.value = true
  try {
    collections.value = await microApi.collections()
    selectedCollectionId.value = collections.value.some((entry) => entry.id === selectId)
      ? selectId
      : ''
    if (selectedCollectionId.value) await refreshRequests()
    else requests.value = []
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}

async function refreshRequests(): Promise<void> {
  if (!selectedCollectionId.value) return
  requests.value = await microApi.collectionRequests(selectedCollectionId.value)
}

async function openCollection(entry: HttpCollection): Promise<void> {
  if (busy.value) return
  if (selectedCollectionId.value !== entry.id) loadedRequest.value = undefined
  selectedCollectionId.value = entry.id
  error.value = ''
  busy.value = true
  try {
    await refreshRequests()
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}

function newCollection(): void {
  editingCollection.value = undefined
  collectionName.value = ''
  collectionDescription.value = ''
  error.value = ''
  collectionModal.value = true
}

function editCollection(entry: HttpCollection): void {
  editingCollection.value = entry
  collectionName.value = entry.name
  collectionDescription.value = entry.description
  error.value = ''
  collectionModal.value = true
}

async function saveCollection(): Promise<void> {
  if (busy.value || !collectionName.value.trim()) return
  busy.value = true
  error.value = ''
  try {
    const saved = editingCollection.value
      ? await microApi.updateCollection(
          editingCollection.value.id,
          collectionName.value,
          collectionDescription.value,
        )
      : await microApi.createCollection(collectionName.value, collectionDescription.value)
    collectionModal.value = false
    await refreshCollections(saved.id)
    emit('notice', editingCollection.value ? 'Collection diperbarui.' : 'Collection dibuat.')
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}

function openSaveRequest(): void {
  requestName.value = loadedRequest.value?.name ?? ''
  requestCollectionId.value = loadedRequest.value?.collection_id ?? selectedCollectionId.value
  error.value = ''
  requestModal.value = true
}

async function saveRequest(): Promise<void> {
  if (
    busy.value ||
    !requestCollectionId.value ||
    !requestName.value.trim() ||
    !props.draft.url.trim()
  )
    return
  busy.value = true
  error.value = ''
  try {
    const saved =
      loadedRequest.value?.collection_id === requestCollectionId.value
        ? await microApi.updateCollectionRequest(
            requestCollectionId.value,
            loadedRequest.value.id,
            requestName.value,
            props.draft,
          )
        : await microApi.saveCollectionRequest(
            requestCollectionId.value,
            requestName.value,
            props.draft,
          )
    loadedRequest.value = saved
    selectedCollectionId.value = requestCollectionId.value
    requestModal.value = false
    await refreshCollections(requestCollectionId.value)
    emit('notice', 'Request tersimpan di collection. Izin localhost/LAN tidak disimpan aktif.')
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}

async function loadRequest(entry: SavedRequest): Promise<void> {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const detail = await microApi.loadCollectionRequest(entry.collection_id, entry.id)
    loadedRequest.value = entry
    emit(
      'load',
      { ...detail.request, allow_private: false },
      `${selectedCollection.value?.name} / ${entry.name}`,
    )
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}

function askDeleteCollection(entry: HttpCollection): void {
  deleting.value = { type: 'collection', id: entry.id, name: entry.name }
  error.value = ''
  confirmDelete.value = true
}

function askDeleteRequest(entry: SavedRequest): void {
  deleting.value = { type: 'request', id: entry.id, name: entry.name }
  error.value = ''
  confirmDelete.value = true
}

async function remove(): Promise<void> {
  if (!deleting.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    if (deleting.value.type === 'collection') {
      await microApi.deleteCollection(deleting.value.id)
      if (selectedCollectionId.value === deleting.value.id) selectedCollectionId.value = ''
      if (loadedRequest.value?.collection_id === deleting.value.id) loadedRequest.value = undefined
    } else {
      await microApi.deleteCollectionRequest(selectedCollectionId.value, deleting.value.id)
      if (loadedRequest.value?.id === deleting.value.id) loadedRequest.value = undefined
    }
    confirmDelete.value = false
    await refreshCollections()
    emit('notice', 'Data collection berhasil dihapus.')
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}

async function exportSelected(): Promise<void> {
  if (!selectedCollection.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const document = await microApi.exportCollection(selectedCollection.value.id)
    const filename = `${
      selectedCollection.value.name
        .replace(/[^a-z0-9]+/gi, '-')
        .replace(/^-|-$/g, '')
        .toLowerCase() || 'collection'
    }.http-collection.json`
    downloadFile(
      new Blob([JSON.stringify(document, null, 2)], { type: 'application/json;charset=utf-8' }),
      filename,
    )
    emit(
      'notice',
      'Collection diekspor. File dapat berisi header, token, atau password dalam teks biasa.',
    )
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}

async function importFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || busy.value) return
  if (file.size > 60_000_000) {
    error.value = 'File import maksimal 60 MB.'
    return
  }
  busy.value = true
  error.value = ''
  try {
    const document: unknown = JSON.parse(await file.text())
    const saved = await microApi.importCollection(document)
    await refreshCollections(saved.id)
    emit('notice', `Collection “${saved.name}” berhasil diimpor.`)
  } catch (cause) {
    error.value = cause instanceof SyntaxError ? 'File bukan JSON yang valid.' : errorMessage(cause)
  } finally {
    busy.value = false
  }
}

onMounted(refreshCollections)
</script>

<template>
  <section
    class="collection-browser tool-section"
    aria-labelledby="collection-title"
  >
    <div class="collection-heading">
      <div>
        <h2 id="collection-title">Collections</h2>
        <p class="small muted">Kelompokkan dan gunakan ulang request tanpa langsung mengirimnya.</p>
      </div>
      <div class="tool-actions">
        <UiButton
          variant="secondary"
          :disabled="disabled || busy"
          @click="newCollection"
        >
          Collection baru
        </UiButton>
        <UiButton
          variant="secondary"
          :disabled="disabled || busy"
          @click="importInput?.click()"
        >
          Import JSON
        </UiButton>
        <input
          ref="importInput"
          class="sr-only"
          type="file"
          accept=".json,application/json"
          aria-label="Pilih file collection JSON"
          @change="importFile"
        />
      </div>
    </div>
    <p
      v-if="error"
      role="alert"
      class="field-error"
    >
      {{ error }}
    </p>
    <UiDataTable
      :rows="collections"
      :columns="collectionColumns"
      row-key="id"
      caption="Daftar HTTP collection"
      :loading="busy && !collections.length"
      :page-size="8"
      @retry="refreshCollections()"
    >
      <template #cell-name="{ row }">
        <div class="collection-name">
          <strong>{{ row.name }}</strong>
          <span v-if="row.description">{{ row.description }}</span>
        </div>
      </template>
      <template #cell-request_count="{ value }">{{ value }} request</template>
      <template #cell-updated_at="{ value }">
        {{ new Date(String(value)).toLocaleString('id-ID') }}
      </template>
      <template #cell-id="{ row }">
        <div class="table-actions">
          <UiButton
            size="sm"
            variant="secondary"
            :disabled="disabled || busy"
            @click="openCollection(row)"
          >
            Buka
          </UiButton>
          <UiButton
            size="sm"
            variant="ghost"
            :disabled="disabled || busy"
            @click="editCollection(row)"
          >
            Edit
          </UiButton>
          <UiButton
            size="sm"
            variant="danger"
            :disabled="disabled || busy"
            @click="askDeleteCollection(row)"
          >
            Hapus
          </UiButton>
        </div>
      </template>
    </UiDataTable>

    <div
      v-if="selectedCollection"
      class="saved-requests"
    >
      <div class="collection-heading">
        <div>
          <h3>{{ selectedCollection.name }}</h3>
          <p class="small muted">Request tersimpan ditampilkan tanpa URL atau nilai rahasia.</p>
        </div>
        <div class="tool-actions">
          <UiButton
            variant="secondary"
            :disabled="disabled || busy || !draft.url.trim()"
            @click="openSaveRequest"
          >
            {{ loadedRequest ? 'Perbarui request tersimpan' : 'Simpan request saat ini' }}
          </UiButton>
          <UiButton
            variant="secondary"
            :disabled="disabled || busy"
            @click="exportSelected"
          >
            Export JSON
          </UiButton>
        </div>
      </div>
      <p class="small muted">
        File export berisi detail request dalam teks biasa. Simpan sebagai data sensitif.
      </p>
      <UiDataTable
        :rows="requests"
        :columns="requestColumns"
        row-key="id"
        :caption="`Request dalam collection ${selectedCollection.name}`"
        :page-size="8"
      >
        <template #cell-method="{ value }">
          <code>{{ value }}</code>
        </template>
        <template #cell-updated_at="{ value }">
          {{ new Date(String(value)).toLocaleString('id-ID') }}
        </template>
        <template #cell-id="{ row }">
          <div class="table-actions">
            <UiButton
              size="sm"
              variant="secondary"
              :disabled="disabled || busy"
              @click="loadRequest(row)"
            >
              Muat ke form
            </UiButton>
            <UiButton
              size="sm"
              variant="danger"
              :disabled="disabled || busy"
              @click="askDeleteRequest(row)"
            >
              Hapus
            </UiButton>
          </div>
        </template>
      </UiDataTable>
    </div>
  </section>

  <UiModal
    v-model="collectionModal"
    :title="editingCollection ? 'Edit collection' : 'Collection baru'"
    description="Collection menyimpan kelompok request di database lokal."
    size="sm"
    :dismissible="!busy"
  >
    <form
      class="tool-section"
      @submit.prevent="saveCollection"
    >
      <UiInput
        v-model="collectionName"
        label="Nama collection"
        required
        maxlength="255"
        autofocus
      />
      <UiTextarea
        v-model="collectionDescription"
        label="Deskripsi"
        rows="3"
        maxlength="2000"
      />
      <p
        v-if="error"
        role="alert"
        class="field-error"
      >
        {{ error }}
      </p>
      <div class="modal-actions">
        <UiButton
          variant="secondary"
          :disabled="busy"
          @click="collectionModal = false"
        >
          Batal
        </UiButton>
        <UiButton
          type="submit"
          :loading="busy"
          :disabled="!collectionName.trim()"
        >
          {{ editingCollection ? 'Simpan perubahan' : 'Buat collection' }}
        </UiButton>
      </div>
    </form>
  </UiModal>

  <UiModal
    v-model="requestModal"
    title="Simpan request"
    description="URL, body, headers, variabel, dan autentikasi disimpan terenkripsi."
    size="sm"
    :dismissible="!busy"
  >
    <form
      class="tool-section"
      @submit.prevent="saveRequest"
    >
      <UiSelect
        v-model="requestCollectionId"
        label="Collection"
        :options="collectionOptions"
        required
      />
      <UiInput
        v-model="requestName"
        label="Nama request"
        required
        maxlength="255"
        autofocus
      />
      <p
        v-if="error"
        role="alert"
        class="field-error"
      >
        {{ error }}
      </p>
      <div class="modal-actions">
        <UiButton
          variant="secondary"
          :disabled="busy"
          @click="requestModal = false"
        >
          Batal
        </UiButton>
        <UiButton
          type="submit"
          :loading="busy"
          :disabled="!requestCollectionId || !requestName.trim()"
        >
          {{
            loadedRequest?.collection_id === requestCollectionId
              ? 'Perbarui request'
              : 'Simpan request'
          }}
        </UiButton>
      </div>
    </form>
  </UiModal>

  <UiConfirmDialog
    v-model="confirmDelete"
    :title="deleting?.type === 'collection' ? 'Hapus collection?' : 'Hapus request tersimpan?'"
    :description="
      deleting?.type === 'collection'
        ? `Collection ${deleting?.name ?? ''} dan seluruh request di dalamnya akan dihapus permanen.`
        : `Request ${deleting?.name ?? ''} akan dihapus permanen dari collection.`
    "
    :busy="busy"
    :error="error"
    @confirm="remove"
  />
</template>

<style scoped>
.collection-browser {
  padding-bottom: 32px;
  border-bottom: 1px solid var(--color-border);
}
.collection-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}
.collection-name {
  display: grid;
  gap: 4px;
  max-width: 32rem;
  white-space: normal;
}
.collection-name span {
  color: var(--color-text-muted);
  font-size: 13px;
}
.saved-requests {
  display: grid;
  gap: 16px;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid var(--color-border);
}
.table-actions,
.modal-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}
@media (max-width: 720px) {
  .collection-heading {
    flex-direction: column;
  }
  .collection-heading .tool-actions,
  .collection-heading .tool-actions > * {
    width: 100%;
  }
}
</style>
