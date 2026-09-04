// Exercise the production worker bundles without a web server or user data.
import assert from 'node:assert/strict'
import { readdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { Worker } from 'node:worker_threads'

const assets = new URL('../dist/assets/', import.meta.url)
const entry = (await readdir(assets)).find((name) => /^worker-.*\.js$/.test(name))
assert.ok(entry, 'Run pnpm build before testing the production worker.')
const worker = new Worker(
  `
  const { parentPort, workerData } = require('node:worker_threads');
  globalThis.self = globalThis;
  globalThis.postMessage = value => parentPort.postMessage(value);
  import(workerData).then(() => {
    parentPort.on('message', data => globalThis.onmessage({ data }));
    parentPort.postMessage({ ready: true });
  }).catch(error => { throw error; });
`,
  { eval: true, workerData: new URL(entry, assets).href },
)

function nextMessage(send) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => done(new Error('Production worker timed out.')), 15000)
    const error = (cause) => done(cause)
    const message = (value) => done(null, value)
    function done(cause, value) {
      clearTimeout(timeout)
      worker.off('error', error)
      worker.off('message', message)
      if (cause) reject(cause)
      else resolve(value)
    }
    worker.once('error', error)
    worker.once('message', message)
    if (send) worker.postMessage(send)
  })
}

try {
  assert.deepEqual(await nextMessage(), { ready: true })
  const json = await nextMessage({
    kind: 'json',
    options: {
      input: 'name: QA\nactive: true',
      source: 'yaml',
      target: 'json',
      indent: '2',
      sort: false,
    },
  })
  assert.equal(json.error, undefined)
  assert.deepEqual(JSON.parse(json.result.output), { name: 'QA', active: true })
  const dummy = await nextMessage({
    kind: 'dummy',
    options: {
      fields: [
        {
          name: 'id',
          type: 'uuid',
          minimum: 0,
          maximum: 100,
          start: '2026-01-01',
          end: '2026-12-31',
          choices: '',
        },
      ],
      count: 3,
      seed: 'worker-smoke-test',
      table: 'test_records',
    },
  })
  assert.equal(dummy.error, undefined)
  assert.equal(JSON.parse(dummy.result.json).length, 3)
  assert.match(dummy.result.sql, /INSERT INTO "test_records"/)
  console.log(`Production worker smoke test passed: ${fileURLToPath(new URL(entry, assets))}`)
} finally {
  await worker.terminate()
}
