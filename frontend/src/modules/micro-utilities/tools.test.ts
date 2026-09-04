import { beforeEach, describe, expect, it, vi } from 'vitest'
import { webcrypto } from 'node:crypto'
import { createPinia, setActivePinia } from 'pinia'
import { csvCell, generateDummy, sqlCell, validateSchema } from './dummy'
import {
  decodeBase64,
  decodeBytes,
  decodeJwt,
  encodeBase64,
  jwtTimeStatus,
  verifyJwt,
} from './encoding'
import { processJson } from './json'
import { blankField, useMicroStore } from './store'
import { fieldTypes } from './api'
import { useAuthStore } from '../../shared/stores/auth'

beforeEach(() => {
  setActivePinia(createPinia())
})
describe('JSON / YAML processing', () => {
  const options = { source: 'json', target: 'json', indent: '2', sort: false }
  it('formats, minifies, recursively sorts and indexes a tree', () => {
    const result = processJson({
      ...options,
      input: '{"z":{"b":2,"a":1},"a":[true,null]}',
      sort: true,
    })
    expect(result.output).toContain('\n  "a": [')
    expect(result.minified).toBe('{"a":[true,null],"z":{"a":1,"b":2}}')
    expect(result.nodes[1]).toMatchObject({ parent: 0, label: 'a', container: true })
    expect(result.nodes[2]).toMatchObject({ parent: 1, label: '0', value: 'true' })
  })
  it('converts both directions and preserves JSON scalar types', () => {
    const yaml = processJson({
      ...options,
      input: '{"text":"true","yes":true,"items":[1,2]}',
      target: 'yaml',
    }).output
    expect(JSON.parse(processJson({ ...options, source: 'yaml', input: yaml }).output)).toEqual({
      text: 'true',
      yes: true,
      items: [1, 2],
    })
    expect(processJson({ ...options, input: 'null', target: 'minify' }).output).toBe('null')
  })
  it('gives line/column errors without echoing private contents', () => {
    expect(() => processJson({ ...options, input: '{\n"SECRET":\n}' })).toThrow(/baris 3, kolom 1/)
    expect(() => processJson({ ...options, source: 'yaml', input: 'a: 1\na: 2' })).toThrow(
      /baris 2/,
    )
  })
  it('rejects oversized, deeply nested, cyclic and non-JSON values', () => {
    expect(() => processJson({ ...options, input: `"${'é'.repeat(1100000)}"` })).toThrow(/2 MB/)
    expect(() => processJson({ ...options, input: '['.repeat(66) + '1' + ']'.repeat(66) })).toThrow(
      /kedalaman/,
    )
    expect(() => processJson({ ...options, source: 'yaml', input: 'a: &a [*a]' })).toThrow()
    expect(() => processJson({ ...options, source: 'yaml', input: 'value: .nan' })).toThrow(/NaN/)
  })
  it('retains prototype-like keys as data, without polluting objects', () => {
    const result = processJson({ ...options, input: '{"__proto__":{"polluted":true}}' })
    expect(result.minified).toContain('__proto__')
    expect('polluted' in {}).toBe(false)
  })
})
describe('dummy data', () => {
  const options = {
    fields: [
      { ...blankField('id'), type: 'uuid' as const },
      { ...blankField('email'), type: 'email' as const },
    ],
    count: 5,
    seed: 'reproducible',
    table: 'test_users',
  }
  it('repeats exact data for a seed, changes for another seed, and exports all formats', () => {
    const first = generateDummy(options)
    expect(generateDummy(options)).toEqual(first)
    expect(generateDummy({ ...options, seed: 'different' }).json).not.toBe(first.json)
    expect(JSON.parse(first.json)).toHaveLength(5)
    expect(first.csv.split('\r\n')).toHaveLength(6)
    expect(first.sql.split('\n')).toHaveLength(5)
    expect(first.sql).toContain('INSERT INTO "test_users" ("id", "email")')
    expect(first.json).toContain('@example.test')
  })
  it('supports every field type with constrained integers, dates and enum choices', () => {
    const fields = fieldTypes.map((type) => ({
      ...blankField(type),
      type,
      minimum: 7,
      maximum: 7,
      start: '2026-09-02',
      end: '2026-09-02',
      choices: 'one',
    }))
    const row = JSON.parse(generateDummy({ ...options, fields, count: 1 }).json)[0]
    expect(Object.keys(row)).toHaveLength(fieldTypes.length)
    expect(row.integer).toBe(7)
    expect(row.date).toBe('2026-09-02')
    expect(row.enum).toBe('one')
    expect(typeof row.boolean).toBe('boolean')
  })
  it('escapes SQL values and CSV formulas / quotes', () => {
    expect(sqlCell("O'Brien")).toBe("'O''Brien'")
    expect(csvCell('=1+1')).toBe('"\'=1+1"')
    expect(csvCell(' \t@SUM(A1)')).toBe('"\' \t@SUM(A1)"')
    expect(csvCell('a,"b"')).toBe('"a,""b"""')
    expect(csvCell(-5)).toBe('"-5"')
  })
  it('rejects invalid identifiers, duplicate fields, bad ranges and oversized requests', () => {
    expect(() => generateDummy({ ...options, table: 'users; DROP TABLE users' })).toThrow(
      /Nama tabel/,
    )
    expect(() => validateSchema([blankField('same'), blankField('same')])).toThrow(/unik/)
    expect(() =>
      validateSchema([{ ...blankField('n'), type: 'integer', minimum: 5, maximum: 1 }]),
    ).toThrow(/Rentang/)
    expect(() => generateDummy({ ...options, count: 100001 })).toThrow(/100.000/)
  })
})
describe('Base64 / JWT', () => {
  it('round-trips Unicode in both alphabets', () => {
    for (const urlSafe of [false, true])
      expect(decodeBase64(encodeBase64('Halo 👋 日本語', urlSafe), urlSafe)).toBe('Halo 👋 日本語')
    expect(encodeBase64('😀', true)).not.toMatch(/[+/=]/)
  })
  it('rejects invalid padding/alphabet, non-UTF8 bytes, and excessive input', () => {
    for (const invalid of ['a', 'abc===', 'ab=c', '????'])
      expect(() => decodeBytes(invalid)).toThrow()
    expect(() => decodeBase64('/w==')).toThrow(/UTF-8/)
    expect(() => encodeBase64('é'.repeat(600000))).toThrow(/1 MB/)
  })
  it('decodes claims without claiming trust and evaluates NumericDate', () => {
    const token = `${encodeBase64('{"alg":"none"}', true)}.${encodeBase64('{"exp":100}', true)}.`
    expect(decodeJwt(token).payload.exp).toBe(100)
    expect(jwtTimeStatus({ exp: 100 }, 100000)).toBe('Kedaluwarsa')
    expect(jwtTimeStatus({ exp: 101 }, 100000)).toContain('bukan bukti valid')
    expect(jwtTimeStatus({ nbf: 101 }, 100000)).toContain('Belum aktif')
    expect(jwtTimeStatus({ exp: '100' }, 0)).toContain('tidak valid')
    expect(() => decodeJwt('invalid')).toThrow(/tiga segmen/)
    expect(() => decodeJwt(`${encodeBase64('[]', true)}.${encodeBase64('{}', true)}.`)).toThrow(
      /objek JSON/,
    )
  })
  it('verifies HS256 with an explicit expected algorithm and rejects tampering', async () => {
    vi.stubGlobal('crypto', webcrypto)
    try {
      const data = `${encodeBase64('{"alg":"HS256"}', true)}.${encodeBase64('{"sub":"test"}', true)}`
      const key = await crypto.subtle.importKey(
        'raw',
        new TextEncoder().encode('test-secret'),
        { name: 'HMAC', hash: 'SHA-256' },
        false,
        ['sign'],
      )
      const bytes = new Uint8Array(
        await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(data)),
      )
      const signature = btoa(String.fromCharCode(...bytes))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '')
      const token = `${data}.${signature}`
      expect(await verifyJwt(token, 'test-secret', 'HS256')).toBe(true)
      expect(await verifyJwt(token, 'wrong-key', 'HS256')).toBe(false)
      await expect(verifyJwt(token, 'test-secret', 'RS256')).rejects.toThrow(/Algoritma/)
      await expect(verifyJwt(token, '-----BEGIN PUBLIC KEY-----', 'HS256')).rejects.toThrow(
        /bukan public key/,
      )
    } finally {
      vi.unstubAllGlobals()
    }
  })
  it('verifies RS256 using a public key and never needs a private key in the tool', async () => {
    vi.stubGlobal('crypto', webcrypto)
    try {
      const keys = await crypto.subtle.generateKey(
        {
          name: 'RSASSA-PKCS1-v1_5',
          modulusLength: 2048,
          publicExponent: new Uint8Array([1, 0, 1]),
          hash: 'SHA-256',
        },
        true,
        ['sign', 'verify'],
      )
      const base64url = (value: ArrayBuffer): string =>
        btoa(String.fromCharCode(...new Uint8Array(value)))
          .replace(/\+/g, '-')
          .replace(/\//g, '_')
          .replace(/=+$/, '')
      const data = `${encodeBase64('{"alg":"RS256"}', true)}.${encodeBase64('{"sub":"test"}', true)}`
      const signature = base64url(
        await crypto.subtle.sign(
          'RSASSA-PKCS1-v1_5',
          keys.privateKey,
          new TextEncoder().encode(data),
        ),
      )
      const pem = `-----BEGIN PUBLIC KEY-----\n${btoa(String.fromCharCode(...new Uint8Array(await crypto.subtle.exportKey('spki', keys.publicKey))))}\n-----END PUBLIC KEY-----`
      expect(await verifyJwt(`${data}.${signature}`, pem, 'RS256')).toBe(true)
    } finally {
      vi.unstubAllGlobals()
    }
  })
})
it('keeps drafts in memory, clears sensitive data on explicit logout, not session expiry', () => {
  const auth = useAuthStore()
  auth.everAuthenticated = true
  const store = useMicroStore()
  store.http.token = 'test-token'
  store.json.input = '{"test":true}'
  store.encoding.key = 'test-secret'
  auth.authenticated = false
  expect(store.http.token).toBe('test-token')
  auth.everAuthenticated = false
  expect(store.http.token).toBe('')
  expect(store.json.input).toBe('')
  expect(store.encoding.key).toBe('')
  expect(localStorage.length).toBe(0)
  expect(sessionStorage.length).toBe(0)
})
