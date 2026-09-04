import { defineStore } from 'pinia'
import { reactive, ref, watch } from 'vue'
import { useAuthStore } from '../../shared/stores/auth'
import type { DummyField, HttpDraft, HttpResult } from './api'
export function blankField(name = ''): DummyField {
  return {
    name,
    type: 'full_name',
    minimum: 0,
    maximum: 100,
    start: '2026-01-01',
    end: '2026-12-31',
    choices: '',
  }
}
export const useMicroStore = defineStore('micro-utilities', () => {
  // Session memory only. Never put payloads, tokens, keys, or response bodies in web storage.
  const http = reactive<HttpDraft>({
    method: 'GET',
    url: '',
    headers: [],
    variables: [],
    body: '',
    body_type: 'json',
    auth_type: 'none',
    username: '',
    password: '',
    token: '',
    timeout: 15,
    allow_private: false,
    history_limit: 50,
  })
  const response = ref<HttpResult>()
  const httpBusy = ref(false)
  const revision = ref(0)
  const json = reactive({
    input: '',
    source: 'json',
    target: 'json',
    indent: '2',
    sort: false,
    search: '',
    tree: false,
  })
  const dummy = reactive({
    fields: [blankField('name'), { ...blankField('email'), type: 'email' as const }],
    count: 50,
    seed: '',
    table: 'test_users',
    presetName: '',
  })
  const encoding = reactive({ text: '', alphabet: 'standard', output: '', token: '', key: '' })
  function clear(): void {
    revision.value++
    httpBusy.value = false
    Object.assign(http, {
      url: '',
      headers: [],
      variables: [],
      body: '',
      username: '',
      password: '',
      token: '',
    })
    response.value = undefined
    json.input = ''
    encoding.text = encoding.output = encoding.token = encoding.key = ''
    dummy.fields = [blankField('name'), { ...blankField('email'), type: 'email' }]
    dummy.seed = dummy.presetName = ''
  }
  const auth = useAuthStore()
  watch(
    () => auth.everAuthenticated,
    (value) => {
      if (!value) clear()
    },
    { flush: 'sync' },
  )
  return { http, httpBusy, revision, response, json, dummy, encoding, clear }
})
