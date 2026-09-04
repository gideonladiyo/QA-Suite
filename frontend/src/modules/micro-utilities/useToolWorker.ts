import { onScopeDispose, ref, shallowRef } from 'vue'
import type { DummyOptions } from './dummy'
import type { JsonOptions } from './json'

export function useToolWorker<T>() {
  const result = shallowRef<T>()
  const error = ref('')
  const busy = ref(false)
  let worker: Worker | undefined
  let timeout: ReturnType<typeof setTimeout> | undefined
  function cancel(): void {
    worker?.terminate()
    worker = undefined
    clearTimeout(timeout)
    busy.value = false
  }
  function reset(): void {
    cancel()
    result.value = undefined
    error.value = ''
  }
  function run(kind: 'json' | 'dummy', options: JsonOptions | DummyOptions): void {
    reset()
    busy.value = true
    try {
      worker = new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' })
      const current = worker
      worker.onmessage = (event: MessageEvent<{ result?: T; error?: string }>) => {
        if (worker !== current) return
        result.value = event.data.result
        error.value = event.data.error ?? ''
        cancel()
      }
      worker.onerror = () => {
        if (worker !== current) return
        error.value = 'Worker gagal memproses input. Coba kurangi ukuran data.'
        cancel()
      }
      timeout = setTimeout(() => {
        error.value = 'Pemrosesan dihentikan setelah 30 detik. Kurangi ukuran data.'
        cancel()
      }, 30000)
      worker.postMessage({ kind, options: JSON.parse(JSON.stringify(options)) })
    } catch {
      error.value = 'Worker tidak tersedia di browser ini.'
      cancel()
    }
  }
  onScopeDispose(cancel)
  return { result, error, busy, run, cancel, reset }
}
