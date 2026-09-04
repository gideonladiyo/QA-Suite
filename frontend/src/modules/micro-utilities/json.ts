import { LineCounter, parseDocument, stringify } from 'yaml'
import { visit } from 'jsonc-parser'

export interface JsonOptions {
  input: string
  source: string
  target: string
  indent: string
  sort: boolean
}
export interface TreeNode {
  id: number
  parent: number
  depth: number
  label: string
  value: string
  container: boolean
}
export interface JsonOutput {
  output: string
  minified: string
  nodes: TreeNode[]
}
export const MAX_INPUT = 2 * 1024 * 1024

export function processJson(options: JsonOptions): JsonOutput {
  if (new TextEncoder().encode(options.input).length > MAX_INPUT)
    throw new Error('Input maksimal 2 MB.')
  let parsed: unknown
  if (options.source === 'yaml') {
    const lineCounter = new LineCounter()
    const doc = parseDocument(options.input, {
      lineCounter,
      stringKeys: true,
      uniqueKeys: true,
      logLevel: 'silent',
      prettyErrors: false,
    })
    if (doc.errors.length || doc.warnings.length) {
      const error = (doc.errors[0] ?? doc.warnings[0])!
      const position = lineCounter.linePos(error.pos[0])
      throw new Error(
        `YAML tidak valid — baris ${position.line}, kolom ${position.col}. ${error.code}`,
      )
    }
    try {
      parsed = doc.toJS({ maxAliasCount: 50 })
    } catch {
      throw new Error('YAML memiliki alias berlebih atau struktur yang tidak didukung.')
    }
  } else {
    try {
      parsed = JSON.parse(options.input)
    } catch {
      // Native SyntaxError messages do not expose positions consistently across engines.
      let depth = 0
      const enter = (): void => {
        if (++depth > 64) throw new Error('Struktur terlalu dalam: maksimal kedalaman 64.')
      }
      visit(
        options.input,
        {
          onObjectBegin: enter,
          onArrayBegin: enter,
          onObjectEnd: () => {
            depth--
          },
          onArrayEnd: () => {
            depth--
          },
          onError: (_code, _offset, _length, line, column) => {
            throw new Error(
              `JSON tidak valid — baris ${line + 1}, kolom ${column + 1}. Periksa tanda kutip, koma, dan kurung.`,
            )
          },
        },
        { disallowComments: true, allowTrailingComma: false, allowEmptyContent: false },
      )
      throw new Error('JSON tidak valid. Periksa struktur input.')
    }
  }
  let visited = 0
  let textBudget = 0
  const ancestors = new Set<object>()
  function normalize(value: unknown, depth: number): unknown {
    if (++visited > 100000 || depth > 64)
      throw new Error('Struktur terlalu besar: maksimal 100.000 nilai dan kedalaman 64.')
    if (typeof value === 'string') textBudget += value.length
    if (textBudget > 4 * MAX_INPUT)
      throw new Error('Ekspansi teks/alias terlalu besar. Kurangi ukuran data.')
    if (value === null || typeof value === 'string' || typeof value === 'boolean') return value
    if (typeof value === 'number' && Number.isFinite(value)) return value
    if (typeof value !== 'object' || value === null || ancestors.has(value))
      throw new Error('Gunakan nilai JSON standar; siklus, NaN, dan Infinity tidak didukung.')
    ancestors.add(value)
    let result: unknown
    if (Array.isArray(value)) result = value.map((item) => normalize(item, depth + 1))
    else {
      const entries = Object.entries(value)
      if (options.sort) entries.sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
      result = Object.fromEntries(entries.map(([key, item]) => [key, normalize(item, depth + 1)]))
    }
    ancestors.delete(value)
    return result
  }
  const value = normalize(parsed, 0)
  const minified = JSON.stringify(value)
  const output =
    options.target === 'yaml'
      ? stringify(value, { indent: Number(options.indent), aliasDuplicateObjects: false })
      : options.target === 'minify'
        ? minified
        : JSON.stringify(value, null, Number(options.indent))
  if (output.length > 20 * 1024 * 1024)
    throw new Error('Output terlalu besar. Kurangi indentasi atau ukuran input.')
  const nodes: TreeNode[] = []
  function flatten(item: unknown, label: string, parent: number, depth: number): void {
    const id = nodes.length
    const container = item !== null && typeof item === 'object'
    nodes.push({
      id,
      parent,
      depth,
      label,
      container,
      value: container
        ? `${Array.isArray(item) ? 'Array' : 'Object'} (${Object.keys(item).length})`
        : JSON.stringify(item),
    })
    if (container)
      for (const [key, child] of Object.entries(item)) flatten(child, key, id, depth + 1)
  }
  flatten(value, '$', -1, 0)
  return { output, minified, nodes }
}
