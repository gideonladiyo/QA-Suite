export const paletteRoles = [
  { key: 'ink', label: 'Utama', hint: 'Tombol utama dan navigasi aktif.' },
  { key: 'violet', label: 'Sekunder', hint: 'Penanda dan elemen pendukung.' },
  { key: 'mauve', label: 'Aksen', hint: 'Penekanan tambahan.' },
  { key: 'blush', label: 'Highlight', hint: 'Sorotan dan permukaan lembut.' },
] as const
export type Palette = Record<(typeof paletteRoles)[number]['key'], string>
export const defaultPalette: Palette = {
  ink: '#403d88',
  violet: '#8b639b',
  mauve: '#af719d',
  blush: '#f8b2b2',
}
// Curated combinations of Material 2014 swatches, not complete Material themes.
export const palettePresets = [
  { name: 'Portal original', colors: defaultPalette },
  {
    name: 'Ocean',
    colors: { ink: '#1565c0', violet: '#00838f', mauve: '#5e35b1', blush: '#b3e5fc' },
  },
  {
    name: 'Forest',
    colors: { ink: '#00695c', violet: '#558b2f', mauve: '#8d6e63', blush: '#c8e6c9' },
  },
  {
    name: 'Sunset',
    colors: { ink: '#bf360c', violet: '#ef6c00', mauve: '#8d6e63', blush: '#ffe0b2' },
  },
  {
    name: 'Slate',
    colors: { ink: '#37474f', violet: '#546e7a', mauve: '#607d8b', blush: '#cfd8dc' },
  },
] satisfies { name: string; colors: Palette }[]

export function normalizeHex(value: string): string | null {
  const hex = value.trim().replace(/^#/, '')
  if (/^[\da-f]{6}$/i.test(hex)) return `#${hex.toLowerCase()}`
  if (/^[\da-f]{3}$/i.test(hex))
    return '#' + [...hex.toLowerCase()].map((char) => char + char).join('')
  return null
}
export function normalizePalette(value: unknown): Palette | null {
  if (!value || typeof value !== 'object') return null
  const colors = value as Record<string, unknown>
  const entries = paletteRoles.map(({ key }) => [
    key,
    typeof colors[key] === 'string' ? normalizeHex(colors[key]) : null,
  ])
  return entries.every(([, color]) => color) ? (Object.fromEntries(entries) as Palette) : null
}
export function samePalette(a: Palette, b: Palette): boolean {
  return paletteRoles.every(({ key }) => a[key] === b[key])
}
function rgb(hex: string): number[] {
  return [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16))
}
function luminance(hex: string): number {
  const [r = 0, g = 0, b = 0] = rgb(hex).map((value) => {
    const channel = value / 255
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
  })
  return r * 0.2126 + g * 0.7152 + b * 0.0722
}
export function contrast(a: string, b: string): number {
  const x = luminance(a),
    y = luminance(b)
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05)
}
function mix(color: string, target: string, amount: number): string {
  const destination = rgb(target)
  return (
    '#' +
    rgb(color)
      .map((value, index) =>
        Math.round(value + (destination[index]! - value) * amount)
          .toString(16)
          .padStart(2, '0'),
      )
      .join('')
  )
}
function readable(color: string, backgrounds: string[], dark: boolean): string {
  for (let step = 0; step <= 100; step++) {
    const candidate = mix(color, dark ? '#ffffff' : '#000000', step / 100)
    if (backgrounds.every((background) => contrast(candidate, background) >= 4.5)) return candidate
  }
  return dark ? '#ffffff' : '#000000'
}
function onColor(color: string): string {
  return contrast(color, '#ffffff') > contrast(color, '#000000') ? '#ffffff' : '#000000'
}

export function paletteTokens(palette: Palette, dark: boolean): Record<string, string> {
  const page = dark ? '#151719' : '#fafafa'
  const surface = dark ? '#202124' : '#ffffff'
  const subtle = mix(palette.ink, surface, dark ? 0.88 : 0.96)
  const panel = mix(palette.mauve, surface, dark ? 0.82 : 0.92)
  const highlight = mix(palette.blush, '#ffffff', 0.65)
  const accentSurface = dark ? mix(palette.blush, surface, 0.84) : highlight
  const backgrounds = [page, surface, subtle, panel, accentSurface]
  const primary = readable(palette.ink, backgrounds, dark)
  const secondary = readable(palette.violet, backgrounds, dark)
  const accent = readable(palette.mauve, backgrounds, dark)
  const ink = readable(palette.ink, ['#ffffff', highlight], false)
  return {
    '--color-ink': ink,
    '--color-violet': palette.violet,
    '--color-mauve': palette.mauve,
    '--color-blush': highlight,
    '--color-page': page,
    '--color-surface': surface,
    '--color-surface-subtle': subtle,
    '--color-surface-accent': accentSurface,
    '--color-text': dark ? '#f1f3f4' : '#202124',
    '--color-text-muted': readable(dark ? '#bdc1c6' : '#5f6368', backgrounds, dark),
    '--color-text-on-ink': '#ffffff',
    '--color-border': dark ? '#454a52' : '#dadce0',
    '--color-border-strong': dark ? '#646b75' : '#aeb4bc',
    '--color-primary': primary,
    '--color-primary-hover': mix(primary, dark ? '#ffffff' : '#000000', 0.12),
    '--color-on-primary': onColor(primary),
    '--color-secondary': secondary,
    '--color-accent': accent,
    '--color-focus': primary,
    '--color-brand-text': primary,
    '--color-brand-muted': secondary,
    '--color-brand-panel': panel,
    '--color-on-blush': onColor(highlight),
  }
}

export function importPalette(text: string): Palette {
  const invalid = 'Tempel tepat 4 kode HEX, atau tautan palet Color Hunt/Coolors berisi 4 warna.'
  if (text.length > 2000) throw new Error(invalid)
  let source = text.trim()
  if (/^https:\/\//i.test(source)) {
    const url = new URL(source)
    if (url.username || url.password || url.port) throw new Error(invalid)
    if (
      ['colorhunt.co', 'www.colorhunt.co'].includes(url.hostname) &&
      /^\/palette\/[\da-f]{24}\/?$/i.test(url.pathname)
    ) {
      source = url.pathname.split('/')[2]!.match(/.{6}/g)!.join(' ')
    } else if (
      ['coolors.co', 'www.coolors.co'].includes(url.hostname) &&
      /^\/[\da-f]{6}(?:-[\da-f]{6}){3}\/?$/i.test(url.pathname)
    ) {
      source = url.pathname.slice(1).replace(/\/$/, '').replaceAll('-', ' ')
    } else throw new Error(invalid)
  }
  const colors = source
    .split(/[\s,;]+/)
    .filter(Boolean)
    .map(normalizeHex)
  if (colors.length !== 4 || colors.some((color) => !color)) throw new Error(invalid)
  const sorted = (colors as string[]).sort((a, b) => luminance(a) - luminance(b))
  return Object.fromEntries(paletteRoles.map(({ key }, index) => [key, sorted[index]!])) as Palette
}
