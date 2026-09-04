import { afterEach, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { useToolWorker } from './useToolWorker'
afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

it('terminates superseded workers and ignores late results', () => {
  const workers: FakeWorker[] = []
  class FakeWorker {
    onmessage?: (event: { data: { result: string } }) => void
    postMessage = vi.fn()
    terminate = vi.fn()
    constructor() {
      workers.push(this)
    }
  }
  vi.stubGlobal('Worker', FakeWorker)
  const scope = effectScope()
  const tool = scope.run(() => useToolWorker<string>())!
  const options = { input: '{}', source: 'json', target: 'json', indent: '2', sort: false }
  tool.run('json', options)
  tool.run('json', options)
  expect(workers[0]!.terminate).toHaveBeenCalledOnce()
  workers[0]!.onmessage!({ data: { result: 'stale' } })
  expect(tool.result.value).toBeUndefined()
  expect(tool.busy.value).toBe(true)
  workers[1]!.onmessage!({ data: { result: 'current' } })
  expect(tool.result.value).toBe('current')
  expect(tool.busy.value).toBe(false)
  scope.stop()
})
it('enforces a timeout and cleans up on scope disposal', () => {
  vi.useFakeTimers()
  const terminate = vi.fn()
  class FakeWorker {
    postMessage = vi.fn()
    terminate = terminate
  }
  vi.stubGlobal('Worker', FakeWorker)
  const scope = effectScope()
  const tool = scope.run(() => useToolWorker<string>())!
  const options = { input: '{}', source: 'json', target: 'json', indent: '2', sort: false }
  tool.run('json', options)
  vi.advanceTimersByTime(30000)
  expect(tool.error.value).toContain('30 detik')
  expect(tool.busy.value).toBe(false)
  tool.run('json', options)
  scope.stop()
  expect(terminate).toHaveBeenCalledTimes(2)
})
