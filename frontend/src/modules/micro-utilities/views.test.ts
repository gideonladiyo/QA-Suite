import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { defineComponent } from 'vue'
import { microApi, type HttpResult } from './api'
import { useMicroStore } from './store'
import { microUtilityRoutes } from './routes'
import JsonTree from './components/JsonTree.vue'
import { processJson } from './json'
import { encodeBase64 } from './encoding'

async function view(path: string) {
  const pinia = createPinia()
  setActivePinia(pinia)
  vi.spyOn(microApi, 'history').mockResolvedValue([])
  vi.spyOn(microApi, 'collections').mockResolvedValue([])
  vi.spyOn(microApi, 'collectionRequests').mockResolvedValue([])
  vi.spyOn(microApi, 'presets').mockResolvedValue([])
  const router = createRouter({ history: createMemoryHistory(), routes: microUtilityRoutes })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(defineComponent({ template: '<RouterView />' }), {
    attachTo: document.body,
    global: { plugins: [pinia, router], stubs: { Teleport: true } },
  })
  await flushPromises()
  return { wrapper, router, store: useMicroStore() }
}
function button(wrapper: VueWrapper, text: string) {
  return wrapper.findAll('button').find((item) => item.text() === text)!
}
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Micro Tools UI', () => {
  it('routes to all four real tools and preserves input on navigation', async () => {
    const { wrapper, router, store } = await view('/micro-utilities')
    expect(wrapper.get('h1').text()).toBe('HTTP Client')
    store.http.url = 'https://example.test'
    for (const [path, title] of [
      ['json', 'JSONizer'],
      ['dummy-data', 'Dummy Data'],
      ['base64-jwt', 'Base64 / JWT'],
    ]) {
      await router.push(`/micro-utilities/${path}`)
      await flushPromises()
      expect(wrapper.get('h1').text()).toBe(title)
      if (path === 'json') expect(wrapper.get('textarea').attributes('rows')).toBe('18')
      expect(wrapper.get('nav[aria-label="Micro Tools"]').findAll('a')).toHaveLength(4)
      expect(wrapper.get('nav[aria-label="Breadcrumb"]').text()).toContain(title)
    }
    await router.push('/micro-utilities/http-client')
    await flushPromises()
    expect(store.http.url).toBe('https://example.test')
  }, 20000) // Cold compilation of four lazy Vue routes can exceed the default five seconds.
  it('prevents double sends and renders HTML responses only as text', async () => {
    let resolve!: (value: HttpResult) => void
    const send = vi.spyOn(microApi, 'send').mockReturnValue(
      new Promise((done) => {
        resolve = done
      }),
    )
    const { wrapper, store } = await view('/micro-utilities/http-client')
    store.http.url = 'https://example.test'
    await wrapper.get('form').trigger('submit')
    await wrapper.get('form').trigger('submit')
    expect(send).toHaveBeenCalledTimes(1)
    expect(store.httpBusy).toBe(true)
    resolve({
      status: 200,
      elapsed_ms: 10,
      size_bytes: 31,
      body: '<img src=x onerror=alert(1)>',
      headers: [{ key: 'set-cookie', value: 'PRIVATE_TOKEN' }],
      error: '',
      truncated: false,
      history_saved: true,
    })
    await flushPromises()
    expect(store.httpBusy).toBe(false)
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.text()).toContain('<img src=x onerror=alert(1)>')
    expect(wrapper.text()).not.toContain('PRIVATE_TOKEN')
    expect(wrapper.find('.badge-success').exists()).toBe(true)
  })
  it('loads history without sending, masks tokens and asks before clearing', async () => {
    const send = vi.spyOn(microApi, 'send')
    const clear = vi.spyOn(microApi, 'clearHistory').mockResolvedValue()
    const { wrapper, store } = await view('/micro-utilities/http-client')
    vi.mocked(microApi.history).mockResolvedValue([
      {
        id: 'example-id',
        method: 'POST',
        response_status: 200,
        response_time_ms: 12,
        response_size_bytes: 8,
        created_at: '2026-09-02T00:00:00Z',
      },
    ])
    vi.spyOn(microApi, 'loadHistory').mockResolvedValue({
      ...store.http,
      method: 'POST',
      url: 'https://example.test',
      auth_type: 'bearer',
      token: 'PRIVATE_TOKEN',
      allow_private: true,
    })
    await button(wrapper, 'Muat ulang').trigger('click')
    await flushPromises()
    await button(wrapper, 'Muat ke form').trigger('click')
    await flushPromises()
    expect(store.http.token).toBe('PRIVATE_TOKEN')
    expect(store.http.allow_private).toBe(false)
    expect(wrapper.get('input[type="password"]').element).toHaveProperty('value', 'PRIVATE_TOKEN')
    expect(send).not.toHaveBeenCalled()
    await button(wrapper, 'Hapus riwayat').trigger('click')
    await flushPromises()
    expect(clear).not.toHaveBeenCalled()
    const dialog = wrapper.findAll('dialog').find((item) => item.attributes('open') !== undefined)!
    await dialog
      .findAll('button')
      .find((item) => item.text() === 'Hapus')!
      .trigger('click')
    await flushPromises()
    expect(clear).toHaveBeenCalledTimes(1)
  })
  it('creates a collection and saves the current request without sending it', async () => {
    const collection = {
      id: 'collection-1',
      name: 'Payment API',
      description: 'Request pembayaran',
      request_count: 0,
      updated_at: '2026-09-04T00:00:00Z',
    }
    const create = vi.spyOn(microApi, 'createCollection').mockResolvedValue(collection)
    const save = vi.spyOn(microApi, 'saveCollectionRequest').mockResolvedValue({
      id: 'request-1',
      collection_id: collection.id,
      name: 'Create payment',
      method: 'POST',
      updated_at: '2026-09-04T00:00:00Z',
    })
    const send = vi.spyOn(microApi, 'send')
    const { wrapper, store } = await view('/micro-utilities/http-client')
    vi.mocked(microApi.collections).mockResolvedValue([collection])
    await button(wrapper, 'Collection baru').trigger('click')
    await flushPromises()
    const collectionDialog = wrapper
      .findAll('dialog')
      .find((dialog) => dialog.text().includes('Collection baru'))!
    await collectionDialog.get('input').setValue(collection.name)
    await collectionDialog.get('form').trigger('submit')
    await flushPromises()
    expect(create).toHaveBeenCalledWith(collection.name, '')

    store.http.method = 'POST'
    store.http.url = 'https://example.test/payments'
    await flushPromises()
    await button(wrapper, 'Simpan request saat ini').trigger('click')
    await flushPromises()
    const requestDialog = wrapper.findAll('dialog').find((dialog) => dialog.attributes('open') !== undefined)!
    await requestDialog.get('input').setValue('Create payment')
    await requestDialog.get('form').trigger('submit')
    await flushPromises()
    expect(save).toHaveBeenCalledWith(
      collection.id,
      'Create payment',
      expect.objectContaining({ method: 'POST', url: 'https://example.test/payments' }),
    )
    expect(send).not.toHaveBeenCalled()
  })
  it('decodes Base64 / JWT without network calls', async () => {
    const { wrapper, store } = await view('/micro-utilities/base64-jwt')
    const fetch = vi.spyOn(globalThis, 'fetch')
    store.encoding.text = 'Halo 👋'
    await flushPromises()
    await button(wrapper, 'Encode').trigger('click')
    expect(store.encoding.output).toBe(encodeBase64('Halo 👋'))
    store.encoding.token = `${encodeBase64('{"alg":"none"}', true)}.${encodeBase64('{"exp":100}', true)}.`
    await flushPromises()
    expect(wrapper.text()).toContain('Kedaluwarsa')
    expect(wrapper.text()).toContain('Status waktu tidak membuktikan signature')
    expect(fetch).not.toHaveBeenCalled()
  })
  it('warns before large data generation and supports cancelling the worker', async () => {
    const post = vi.fn(),
      terminate = vi.fn()
    class FakeWorker {
      postMessage = post
      terminate = terminate
    }
    vi.stubGlobal('Worker', FakeWorker)
    const { wrapper, store } = await view('/micro-utilities/dummy-data')
    store.dummy.count = 10001
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(post).not.toHaveBeenCalled()
    await button(wrapper, 'Lanjut buat data').trigger('click')
    await flushPromises()
    expect(post).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: 'dummy',
        options: expect.objectContaining({ count: 10001 }),
      }),
    )
    await button(wrapper, 'Batalkan').trigger('click')
    expect(terminate).toHaveBeenCalledTimes(1)
  })
  it('surfaces preset failures without losing schema', async () => {
    vi.spyOn(microApi, 'savePreset').mockRejectedValue(new Error('Nama preset sudah ada.'))
    const { wrapper, store } = await view('/micro-utilities/dummy-data')
    store.dummy.presetName = 'People'
    await flushPromises()
    await button(wrapper, 'Simpan schema sebagai preset').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Nama preset sudah ada.')
    expect(store.dummy.fields).toHaveLength(2)
  })
  it('virtualizes tree rows, collapses containers, and highlights escaped text', async () => {
    const nodes = processJson({
      input: JSON.stringify({
        nested: { html: '<script>test</script>' },
        rows: Array.from({ length: 1000 }, (_, i) => i),
      }),
      source: 'json',
      target: 'json',
      indent: '2',
      sort: false,
    }).nodes
    const wrapper = mount(JsonTree, { props: { nodes, search: '' } })
    await wrapper.get('button[aria-label="Buka rows"]').trigger('click')
    expect(wrapper.findAll('.tree-row').length).toBeLessThanOrEqual(22)
    await wrapper.setProps({ search: '<script>' })
    expect(wrapper.get('mark').text()).toBe('<script>')
    expect(wrapper.find('script').exists()).toBe(false)
    await wrapper.setProps({ search: '' })
    await wrapper.get('button[aria-label="Tutup $"]').trigger('click')
    expect(wrapper.findAll('.tree-row')).toHaveLength(1)
  })
})
