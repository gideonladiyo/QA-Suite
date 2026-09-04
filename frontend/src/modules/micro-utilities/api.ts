import { api } from '../../shared/api'
export interface Pair {
  key: string
  value: string
}
export interface HttpDraft {
  method: string
  url: string
  headers: Pair[]
  variables: Pair[]
  body: string
  body_type: string
  auth_type: string
  username: string
  password: string
  token: string
  timeout: number
  allow_private: boolean
  history_limit: number
}
export interface HttpResult {
  status: number | null
  elapsed_ms: number
  size_bytes: number
  headers: Pair[]
  body: string
  error: string
  truncated: boolean
  history_saved: boolean
}
export interface HistoryEntry {
  id: string
  method: string
  response_status: number | null
  response_time_ms: number
  response_size_bytes: number
  created_at: string
}
export interface HttpCollection {
  id: string
  name: string
  description: string
  request_count: number
  updated_at: string
}
export interface SavedRequest {
  id: string
  collection_id: string
  name: string
  method: string
  updated_at: string
}
export interface SavedRequestDetail extends SavedRequest {
  request: HttpDraft
}
export interface CollectionDocument {
  format: 'qa-portal-http-collection'
  schema_version: 1
  exported_at: string
  collection: {
    name: string
    description: string
    requests: { name: string; request: HttpDraft }[]
  }
}
export const fieldTypes = [
  'full_name',
  'first_name',
  'last_name',
  'email',
  'phone',
  'address',
  'company',
  'uuid',
  'integer',
  'boolean',
  'date',
  'lorem',
  'enum',
] as const
export type FieldType = (typeof fieldTypes)[number]
export interface DummyField {
  name: string
  type: FieldType
  minimum: number
  maximum: number
  start: string
  end: string
  choices: string
}
export interface Preset {
  id: string
  name: string
  fields: DummyField[]
}
export const microApi = {
  send: (body: HttpDraft): Promise<HttpResult> =>
    api('/micro-utilities/http/send', { method: 'POST', body: JSON.stringify(body) }),
  history: (): Promise<HistoryEntry[]> => api('/micro-utilities/http/history'),
  loadHistory: (id: string): Promise<HttpDraft> =>
    api(`/micro-utilities/http/history/${encodeURIComponent(id)}`),
  clearHistory: (): Promise<void> => api('/micro-utilities/http/history', { method: 'DELETE' }),
  collections: (): Promise<HttpCollection[]> => api('/micro-utilities/http/collections'),
  createCollection: (name: string, description: string): Promise<HttpCollection> =>
    api('/micro-utilities/http/collections', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    }),
  updateCollection: (id: string, name: string, description: string): Promise<HttpCollection> =>
    api(`/micro-utilities/http/collections/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: JSON.stringify({ name, description }),
    }),
  deleteCollection: (id: string): Promise<void> =>
    api(`/micro-utilities/http/collections/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  collectionRequests: (id: string): Promise<SavedRequest[]> =>
    api(`/micro-utilities/http/collections/${encodeURIComponent(id)}/requests`),
  saveCollectionRequest: (
    collectionId: string,
    name: string,
    request: HttpDraft,
  ): Promise<SavedRequest> =>
    api(`/micro-utilities/http/collections/${encodeURIComponent(collectionId)}/requests`, {
      method: 'POST',
      body: JSON.stringify({ name, request }),
    }),
  loadCollectionRequest: (collectionId: string, requestId: string): Promise<SavedRequestDetail> =>
    api(
      `/micro-utilities/http/collections/${encodeURIComponent(collectionId)}/requests/${encodeURIComponent(requestId)}`,
    ),
  updateCollectionRequest: (
    collectionId: string,
    requestId: string,
    name: string,
    request: HttpDraft,
  ): Promise<SavedRequest> =>
    api(
      `/micro-utilities/http/collections/${encodeURIComponent(collectionId)}/requests/${encodeURIComponent(requestId)}`,
      { method: 'PUT', body: JSON.stringify({ name, request }) },
    ),
  deleteCollectionRequest: (collectionId: string, requestId: string): Promise<void> =>
    api(
      `/micro-utilities/http/collections/${encodeURIComponent(collectionId)}/requests/${encodeURIComponent(requestId)}`,
      { method: 'DELETE' },
    ),
  exportCollection: (id: string): Promise<CollectionDocument> =>
    api(`/micro-utilities/http/collections/${encodeURIComponent(id)}/export`),
  importCollection: (document: unknown): Promise<HttpCollection> =>
    api('/micro-utilities/http/collections/import', {
      method: 'POST',
      body: JSON.stringify(document),
    }),
  presets: (): Promise<Preset[]> => api('/micro-utilities/presets'),
  savePreset: (name: string, fields: DummyField[]): Promise<Preset> =>
    api('/micro-utilities/presets', { method: 'POST', body: JSON.stringify({ name, fields }) }),
  deletePreset: (id: string): Promise<void> =>
    api(`/micro-utilities/presets/${encodeURIComponent(id)}`, { method: 'DELETE' }),
}
