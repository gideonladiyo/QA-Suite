import { processJson, type JsonOptions } from './json'
import type { DummyOptions } from './dummy'
self.onmessage = async (
  event: MessageEvent<
    { kind: 'json'; options: JsonOptions } | { kind: 'dummy'; options: DummyOptions }
  >,
) => {
  try {
    const result =
      event.data.kind === 'json'
        ? processJson(event.data.options)
        : (await import('./dummy')).generateDummy(event.data.options)
    self.postMessage({ result })
  } catch (error) {
    self.postMessage({ error: error instanceof Error ? error.message : 'Pemrosesan gagal.' })
  }
}
