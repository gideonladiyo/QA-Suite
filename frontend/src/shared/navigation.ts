import {
  PhSquaresFour,
  PhClipboardText,
  PhBracketsCurly,
  PhDatabase,
  PhLockKey,
  PhSlidersHorizontal,
  PhStack,
  PhGlobe,
  PhShuffle,
  PhKey,
} from '@phosphor-icons/vue'
import type { Component } from 'vue'

export type NavigationItem = { label: string; path: string; icon: Component; keywords: string }
export const primaryNavigation: NavigationItem[] = [
  { label: 'Dashboard', path: '/', icon: PhSquaresFour, keywords: 'home beranda' },
  {
    label: 'QA Reports',
    path: '/qa-reports',
    icon: PhClipboardText,
    keywords: 'laporan testing harian',
  },
  {
    label: 'Micro Tools',
    path: '/micro-utilities',
    icon: PhBracketsCurly,
    keywords: 'utilities alat',
  },
  { label: 'Supabase Hub', path: '/supabase-hub', icon: PhDatabase, keywords: 'koneksi database' },
  { label: 'Vault', path: '/vault', icon: PhLockKey, keywords: 'password secret kata sandi' },
]
export const secondaryNavigation: NavigationItem[] = [
  {
    label: 'Komponen UI',
    path: '/components',
    icon: PhStack,
    keywords: 'button card komponen desain',
  },
  {
    label: 'Settings',
    path: '/settings',
    icon: PhSlidersHorizontal,
    keywords: 'pengaturan tema appearance',
  },
]
export const toolNavigation: NavigationItem[] = [
  {
    label: 'HTTP Client',
    path: '/micro-utilities/http-client',
    icon: PhGlobe,
    keywords: 'request api endpoint',
  },
  {
    label: 'JSONizer',
    path: '/micro-utilities/json',
    icon: PhBracketsCurly,
    keywords: 'json yaml formatter',
  },
  {
    label: 'Dummy Data',
    path: '/micro-utilities/dummy-data',
    icon: PhShuffle,
    keywords: 'fake seed generator',
  },
  {
    label: 'Base64 / JWT',
    path: '/micro-utilities/base64-jwt',
    icon: PhKey,
    keywords: 'jwt token decode encode',
  },
]
export const commandNavigation = [...primaryNavigation, ...toolNavigation, ...secondaryNavigation]

export function matchesCommand(item: NavigationItem, query: string): boolean {
  const haystack = `${item.label} ${item.keywords}`.toLocaleLowerCase()
  return query
    .trim()
    .toLocaleLowerCase()
    .split(/\s+/)
    .every((word) => {
      let at = 0
      for (const char of word) {
        const found = haystack.indexOf(char, at)
        if (found < 0) return false
        at = found + 1
      }
      return true
    })
}
