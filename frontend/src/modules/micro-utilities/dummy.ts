import { Faker, en } from '@faker-js/faker'
import type { DummyField } from './api'

export interface DummyOptions {
  fields: DummyField[]
  count: number
  seed: string
  table: string
}
export interface DummyOutput {
  json: string
  csv: string
  sql: string
  seed: string
  count: number
}
type Cell = string | number | boolean

export function validateSchema(fields: DummyField[]): void {
  if (!fields.length || fields.length > 30) throw new Error('Gunakan 1–30 field.')
  const names = new Set<string>()
  for (const field of fields) {
    if (!/^[A-Za-z_][A-Za-z0-9_]{0,62}$/.test(field.name) || names.has(field.name))
      throw new Error(
        'Nama field harus unik, diawali huruf/underscore, dan hanya berisi huruf, angka, atau underscore (maks. 63).',
      )
    names.add(field.name)
    if (
      field.type === 'integer' &&
      (!Number.isInteger(field.minimum) ||
        !Number.isInteger(field.maximum) ||
        field.minimum > field.maximum ||
        field.minimum < -1e9 ||
        field.maximum > 1e9)
    )
      throw new Error('Rentang integer tidak valid (batas ±1 miliar).')
    if (
      field.type === 'date' &&
      (!/^\d{4}-\d{2}-\d{2}$/.test(field.start) ||
        !/^\d{4}-\d{2}-\d{2}$/.test(field.end) ||
        !Number.isFinite(Date.parse(field.start)) ||
        !Number.isFinite(Date.parse(field.end)) ||
        new Date(field.start).toISOString().slice(0, 10) !== field.start ||
        new Date(field.end).toISOString().slice(0, 10) !== field.end ||
        field.start > field.end)
    )
      throw new Error('Rentang tanggal tidak valid.')
    if (
      field.type === 'enum' &&
      (!field.choices.trim() || field.choices.length > 2000 || field.choices.includes('\0'))
    )
      throw new Error('Isi pilihan enum, satu nilai per baris (maks. 2.000 karakter).')
  }
}
export function csvCell(value: Cell): string {
  let text = String(value)
  // Spreadsheet formula protection for text cells; numeric negatives stay numeric.
  if (typeof value === 'string' && /^[\s]*[=+@-]/.test(text)) text = `'${text}`
  return `"${text.replace(/"/g, '""')}"`
}
export function sqlCell(value: Cell): string {
  return typeof value === 'string' ? `'${value.replace(/'/g, "''")}'` : String(value)
}
export function generateDummy(options: DummyOptions): DummyOutput {
  validateSchema(options.fields)
  if (
    !Number.isInteger(options.count) ||
    options.count < 1 ||
    options.count > 100000 ||
    options.count * options.fields.length > 1000000
  )
    throw new Error('Gunakan 1–100.000 baris, maksimal 1 juta sel.')
  if (!/^[A-Za-z_][A-Za-z0-9_]{0,62}$/.test(options.table))
    throw new Error('Nama tabel SQL harus berupa identifier, maksimal 63 karakter.')
  if (options.seed.length > 200) throw new Error('Seed maksimal 200 karakter.')
  const seed = options.seed || String(crypto.getRandomValues(new Uint32Array(1))[0])
  const faker = new Faker({ locale: [en] })
  faker.seed(Array.from(new TextEncoder().encode(seed)))
  function cell(field: DummyField): Cell {
    switch (field.type) {
      case 'full_name':
        return faker.person.fullName()
      case 'first_name':
        return faker.person.firstName()
      case 'last_name':
        return faker.person.lastName()
      case 'email':
        return `${faker.string.alphanumeric(12).toLowerCase()}@example.test`
      case 'phone':
        return `+1-202-555-01${String(faker.number.int({ min: 0, max: 99 })).padStart(2, '0')}`
      case 'address':
        return faker.location.streetAddress()
      case 'company':
        return faker.company.name()
      case 'uuid':
        return faker.string.uuid()
      case 'integer':
        return faker.number.int({ min: field.minimum, max: field.maximum })
      case 'boolean':
        return faker.datatype.boolean()
      case 'date':
        return faker.date
          .between({ from: `${field.start}T00:00:00.000Z`, to: `${field.end}T23:59:59.999Z` })
          .toISOString()
          .slice(0, 10)
      case 'lorem':
        return faker.lorem.sentence()
      case 'enum':
        return faker.helpers.arrayElement(
          field.choices
            .split('\n')
            .map((value) => value.trim())
            .filter(Boolean),
        )
      default:
        throw new Error('Tipe field tidak didukung.')
    }
  }
  const rows: Record<string, Cell>[] = []
  const csv = [options.fields.map((field) => csvCell(field.name)).join(',')]
  const sql: string[] = []
  const prefix = `INSERT INTO "${options.table}" (${options.fields.map((field) => `"${field.name}"`).join(', ')}) VALUES `
  let size = 0
  for (let index = 0; index < options.count; index++) {
    const values = options.fields.map(cell)
    const row = Object.fromEntries(
      options.fields.map((field, index) => [field.name, values[index]!]),
    )
    const csvRow = values.map(csvCell).join(',')
    const sqlRow = `${prefix}(${values.map(sqlCell).join(', ')});`
    size += new TextEncoder().encode(JSON.stringify(row) + csvRow + sqlRow).length
    if (size > 20 * 1024 * 1024)
      throw new Error('Total output melebihi 20 MB. Kurangi jumlah baris atau field.')
    rows.push(row)
    csv.push(csvRow)
    sql.push(sqlRow)
  }
  const output = {
    json: JSON.stringify(rows, null, 2),
    csv: csv.join('\r\n'),
    sql: sql.join('\n'),
    seed,
    count: rows.length,
  }
  if (new TextEncoder().encode(output.json + output.csv + output.sql).length > 20 * 1024 * 1024)
    throw new Error('Total output melebihi 20 MB. Kurangi jumlah baris atau field.')
  return output
}
