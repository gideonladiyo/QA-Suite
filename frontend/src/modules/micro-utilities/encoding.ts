export function encodeBase64(value: string, urlSafe = false): string {
  const bytes = new TextEncoder().encode(value)
  if (bytes.length > 1048576) throw new Error('Input maksimal 1 MB UTF-8.')
  let binary = ''
  for (let start = 0; start < bytes.length; start += 8192)
    binary += String.fromCharCode(...bytes.subarray(start, start + 8192))
  const result = btoa(binary)
  return urlSafe ? result.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '') : result
}
export function decodeBytes(value: string, urlSafe = false): Uint8Array<ArrayBuffer> {
  if (value.length > 1048576) throw new Error('Input maksimal 1 MB.')
  const compact = value.replace(/\s/g, '')
  if (
    !(urlSafe ? /^[A-Za-z0-9_-]*={0,2}$/ : /^[A-Za-z0-9+/]*={0,2}$/).test(compact) ||
    compact.replace(/=/g, '').length % 4 === 1 ||
    (compact.includes('=') && compact.length % 4 !== 0)
  )
    throw new Error('Base64 tidak valid: periksa alfabet dan padding.')
  try {
    const normalized = compact.replace(/-/g, '+').replace(/_/g, '/')
    return Uint8Array.from(
      atob(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')),
      (char) => char.charCodeAt(0),
    )
  } catch {
    throw new Error('Base64 tidak valid.')
  }
}
export function decodeBase64(value: string, urlSafe = false): string {
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(decodeBytes(value, urlSafe))
  } catch {
    throw new Error(
      'Input bukan Base64 berisi teks UTF-8 yang valid. Data biner tidak ditampilkan sebagai teks.',
    )
  }
}
export interface DecodedJwt {
  header: Record<string, unknown>
  payload: Record<string, unknown>
  segments: string[]
}
export function decodeJwt(token: string): DecodedJwt {
  if (token.length > 1048576) throw new Error('JWT maksimal 1 MB.')
  const segments = token.trim().split('.')
  if (
    segments.length !== 3 ||
    !segments[0] ||
    !segments[1] ||
    segments.some((segment) => !/^[A-Za-z0-9_-]*$/.test(segment))
  )
    throw new Error('Struktur JWT tidak valid: diperlukan tiga segmen Base64URL.')
  try {
    const header: unknown = JSON.parse(decodeBase64(segments[0], true))
    const payload: unknown = JSON.parse(decodeBase64(segments[1], true))
    if (
      !header ||
      !payload ||
      typeof header !== 'object' ||
      typeof payload !== 'object' ||
      Array.isArray(header) ||
      Array.isArray(payload)
    )
      throw new Error()
    return {
      header: header as Record<string, unknown>,
      payload: payload as Record<string, unknown>,
      segments,
    }
  } catch {
    throw new Error('Header dan payload JWT harus berupa objek JSON yang valid.')
  }
}
export function jwtTimeStatus(payload: Record<string, unknown>, now = Date.now()): string {
  for (const key of ['exp', 'iat', 'nbf']) {
    if (
      key in payload &&
      (typeof payload[key] !== 'number' ||
        !Number.isFinite(payload[key]) ||
        Math.abs(payload[key] as number) > 8640000000000)
    )
      return 'Claim waktu tidak valid'
  }
  if (typeof payload.exp === 'number' && payload.exp <= now / 1000) return 'Kedaluwarsa'
  if (typeof payload.nbf === 'number' && payload.nbf > now / 1000) return 'Belum aktif (nbf)'
  return typeof payload.exp === 'number'
    ? 'Belum kedaluwarsa — bukan bukti valid'
    : 'Tanpa exp — waktu kedaluwarsa tidak diketahui'
}
export async function verifyJwt(
  token: string,
  key: string,
  expectedAlgorithm: string,
): Promise<boolean> {
  const jwt = decodeJwt(token)
  if (jwt.header.alg !== expectedAlgorithm)
    throw new Error('Algoritma header tidak cocok dengan algoritma yang diharapkan.')
  if (key.length > 16384) throw new Error('Key maksimal 16.384 karakter.')
  if (!key || !jwt.segments[2]) throw new Error('Isi key dan gunakan JWT dengan signature.')
  if ('crit' in jwt.header || 'b64' in jwt.header)
    throw new Error('Ekstensi header JWT ini tidak didukung.')
  if (!crypto.subtle) throw new Error('Web Crypto memerlukan localhost atau HTTPS.')
  let imported: CryptoKey
  let algorithm: AlgorithmIdentifier
  if (jwt.header.alg === 'HS256') {
    if (key.includes('-----BEGIN'))
      throw new Error('HS256 memerlukan secret, bukan public key PEM.')
    algorithm = { name: 'HMAC' }
    imported = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(key),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['verify'],
    )
  } else if (jwt.header.alg === 'RS256') {
    if (
      !key.trim().startsWith('-----BEGIN PUBLIC KEY-----') ||
      !key.trim().endsWith('-----END PUBLIC KEY-----')
    )
      throw new Error('RS256 memerlukan public key PEM (BEGIN PUBLIC KEY / SPKI).')
    const der = decodeBytes(
      key.replace('-----BEGIN PUBLIC KEY-----', '').replace('-----END PUBLIC KEY-----', ''),
    )
    algorithm = { name: 'RSASSA-PKCS1-v1_5' }
    imported = await crypto.subtle.importKey(
      'spki',
      der,
      { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
      false,
      ['verify'],
    )
  } else
    throw new Error('Verifikasi hanya mendukung HS256 dan RS256; algoritma lain tidak dipercaya.')
  return crypto.subtle.verify(
    algorithm,
    imported,
    decodeBytes(jwt.segments[2], true),
    new TextEncoder().encode(jwt.segments.slice(0, 2).join('.')),
  )
}
