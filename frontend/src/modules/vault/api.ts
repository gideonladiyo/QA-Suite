import { api } from '../../shared/api'

export type VaultCategory = 'password' | 'api_key' | 'token' | 'command' | 'note' | 'other'
export type VaultSort = 'recent' | 'alphabetical' | 'created'

export interface VaultStatus {
  configured: boolean
  unlocked: boolean
}

export interface VaultUnlockResult extends VaultStatus {
  token: string
  auto_lock_minutes: number
}

export interface VaultEntry {
  id: string
  title: string
  username: string | null
  category: VaultCategory
  url: string | null
  last_accessed_at: string | null
  created_at: string
  updated_at: string
}

export interface VaultEntryInput {
  title: string
  username: string
  category: VaultCategory
  url: string
  value: string
  notes: string
}

export interface VaultEntryDetail {
  value: string
  notes: string
}

const base = '/vault'
const options = (token: string, init: RequestInit = {}): RequestInit => ({
  ...init,
  headers: { 'X-Vault-Session': token, ...init.headers },
})

export const vaultApi = {
  status: (): Promise<VaultStatus> => api(`${base}/status`),
  setup: (
    secret: string,
    confirmation: string,
    autoLockMinutes: number,
  ): Promise<VaultUnlockResult> =>
    api(`${base}/setup`, {
      method: 'POST',
      body: JSON.stringify({
        secret,
        confirmation,
        auto_lock_minutes: autoLockMinutes,
      }),
    }),
  unlock: (secret: string, autoLockMinutes: number): Promise<VaultUnlockResult> =>
    api(`${base}/unlock`, {
      method: 'POST',
      body: JSON.stringify({ secret, auto_lock_minutes: autoLockMinutes }),
    }),
  lock: (token: string, keepalive = false): Promise<void> =>
    api(`${base}/lock`, options(token, { method: 'POST', keepalive })),
  touch: (token: string): Promise<void> => api(`${base}/touch`, options(token, { method: 'POST' })),
  list: (
    token: string,
    filters: { search: string; category: string; sort: VaultSort },
  ): Promise<VaultEntry[]> => {
    const query = new URLSearchParams({ search: filters.search, sort: filters.sort })
    if (filters.category) query.set('category', filters.category)
    return api(`${base}?${query}`, options(token))
  },
  create: (token: string, body: VaultEntryInput): Promise<VaultEntry> =>
    api(base, options(token, { method: 'POST', body: JSON.stringify(body) })),
  update: (token: string, id: string, body: VaultEntryInput): Promise<VaultEntry> =>
    api(
      `${base}/${encodeURIComponent(id)}`,
      options(token, { method: 'PUT', body: JSON.stringify(body) }),
    ),
  remove: (token: string, id: string): Promise<void> =>
    api(`${base}/${encodeURIComponent(id)}`, options(token, { method: 'DELETE' })),
  reveal: (token: string, id: string): Promise<VaultEntryDetail> =>
    api(`${base}/${encodeURIComponent(id)}/reveal`, options(token, { method: 'POST' })),
  copy: (token: string, id: string): Promise<{ value: string }> =>
    api(`${base}/${encodeURIComponent(id)}/copy`, options(token, { method: 'POST' })),
}
