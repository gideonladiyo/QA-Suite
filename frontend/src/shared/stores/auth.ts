import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api'

interface AuthState {
  authenticated: boolean
  setup_required: boolean
  username: string | null
  auth_disabled: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const authenticated = ref(false)
  const setupRequired = ref(false)
  const username = ref('')
  const authDisabled = ref(false)
  const everAuthenticated = ref(false)
  function update(state: AuthState): void {
    authenticated.value = state.authenticated
    setupRequired.value = state.setup_required
    username.value = state.username ?? ''
    authDisabled.value = state.auth_disabled
    if (state.authenticated) everAuthenticated.value = true
  }
  async function check(): Promise<void> {
    update(await api<AuthState>('/auth/status'))
  }
  async function login(name: string, password: string): Promise<void> {
    update(
      await api<AuthState>(`/auth/${setupRequired.value ? 'setup' : 'login'}`, {
        method: 'POST',
        body: JSON.stringify({ username: name, password }),
      }),
    )
  }
  async function logout(): Promise<void> {
    if (authDisabled.value) return
    await api<void>('/auth/logout', { method: 'POST' })
    authenticated.value = false
    everAuthenticated.value = false
    username.value = ''
  }
  return {
    authenticated,
    setupRequired,
    username,
    authDisabled,
    everAuthenticated,
    check,
    login,
    logout,
  }
})
