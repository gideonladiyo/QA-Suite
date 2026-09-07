import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import {
  contrast,
  defaultPalette,
  importPalette,
  loadSavedPalettes,
  normalizeHex,
  normalizePalette,
  palettePresets,
  paletteTokens,
  savedPalettesStorageKey,
  storeSavedPalettes,
} from '../../shared/palettes'
import { useUiStore } from '../../shared/stores/ui'
import WorkspacePalette from './components/WorkspacePalette.vue'
import UiInput from '../../shared/components/ui/UiInput.vue'

const ocean = palettePresets[1]!.colors
beforeEach(() => {
  setActivePinia(createPinia())
  document.documentElement.removeAttribute('style')
  document.documentElement.dataset.theme = 'light'
})
afterEach(() => document.documentElement.removeAttribute('style'))

describe('workspace color palettes', () => {
  it('normalizes only safe hex colors and rejects malformed stored palettes', () => {
    expect(normalizeHex(' #AbC ')).toBe('#aabbcc')
    expect(normalizeHex('1565C0')).toBe('#1565c0')
    for (const input of ['red', '#abcd', '#12345678', 'url(https://example.test)', '#12345g', ''])
      expect(normalizeHex(input)).toBeNull()
    for (const input of [
      null,
      'text',
      [],
      {},
      { ...ocean, ink: 5 },
      { ...ocean, ink: 'var(--color-danger)' },
    ])
      expect(normalizePalette(input)).toBeNull()
    expect(normalizePalette({ ...ocean, extra: 'ignored' })).toEqual(ocean)
  })
  it('imports four HEX colors or supported palette URLs without fetching a page', () => {
    const fetch = vi.spyOn(globalThis, 'fetch')
    for (const input of [
      '#F8B2B2, #AF719D; #8B639B\n#403D88',
      'https://colorhunt.co/palette/f8b2b2af719d8b639b403d88',
      'https://coolors.co/f8b2b2-af719d-8b639b-403d88',
    ])
      expect(importPalette(input)).toEqual(defaultPalette)
    for (const input of [
      '#fff #000',
      '#fff #000 #f00 #0f0 #00f',
      '#bad nope #fff #000',
      'https://evil.test/palette/f8b2b2af719d8b639b403d88',
      'https://colorhunt.co.evil.test/palette/f8b2b2af719d8b639b403d88',
      'https://user:pass@colorhunt.co/palette/f8b2b2af719d8b639b403d88',
      'x'.repeat(2001),
    ])
      expect(() => importPalette(input)).toThrow()
    expect(fetch).not.toHaveBeenCalled()
  })
  it('validates saved palettes from local storage and safely handles blocked writes', () => {
    localStorage.setItem(
      savedPalettesStorageKey,
      JSON.stringify([
        { id: 'ocean', name: ' Ocean ', colors: ocean },
        { id: 'duplicate-name', name: 'ocean', colors: defaultPalette },
        { id: 'invalid', name: 'Broken', colors: { ...ocean, ink: 'red' } },
      ]),
    )
    expect(loadSavedPalettes()).toEqual([{ id: 'ocean', name: 'Ocean', colors: ocean }])
    localStorage.setItem(savedPalettesStorageKey, '{broken')
    expect(loadSavedPalettes()).toEqual([])
    expect(
      storeSavedPalettes([], {
        setItem: () => {
          throw new Error('blocked')
        },
      }),
    ).toBe(false)
  })
  it('keeps text, buttons, highlights and brand marks readable in both modes, even with extreme input', () => {
    const palettes = [
      ...palettePresets.map((preset) => preset.colors),
      ...['#000000', '#ffffff', '#ffff00', '#ff00ff', '#0000ff', '#777777'].map((color) => ({
        ink: color,
        violet: color,
        mauve: color,
        blush: color,
      })),
    ]
    for (const palette of palettes)
      for (const dark of [false, true]) {
        const tokens = paletteTokens(palette, dark)
        for (const bg of ['page', 'surface', 'surface-subtle', 'brand-panel', 'surface-accent']) {
          for (const fg of ['text', 'text-muted', 'primary', 'secondary', 'accent']) {
            expect(
              contrast(tokens[`--color-${fg}`]!, tokens[`--color-${bg}`]!),
              `${palette.ink}, dark=${dark}: ${fg} on ${bg}`,
            ).toBeGreaterThanOrEqual(4.5)
          }
        }
        for (const [fg, bg] of [
          ['on-primary', 'primary'],
          ['on-primary', 'primary-hover'],
          ['text-on-ink', 'ink'],
          ['on-blush', 'blush'],
          ['blush', 'ink'],
        ]) {
          expect(
            contrast(tokens[`--color-${fg}`]!, tokens[`--color-${bg}`]!),
          ).toBeGreaterThanOrEqual(4.5)
        }
        expect(tokens).not.toHaveProperty('--color-danger')
        expect(tokens).not.toHaveProperty('--color-success')
      }
  })
  it('applies, persists and restores a palette, then resets the original CSS without changing theme', () => {
    const ui = useUiStore()
    ui.setTheme('dark')
    ui.setColorPalette(ocean)
    expect(JSON.parse(localStorage.getItem('qa-portal:color-palette')!)).toEqual(ocean)
    const darkPrimary = document.documentElement.style.getPropertyValue('--color-primary')
    expect(darkPrimary).toBe(paletteTokens(ocean, true)['--color-primary'])
    setActivePinia(createPinia())
    const restored = useUiStore()
    const cleanup = restored.initialize()
    expect(restored.colorPalette).toEqual(ocean)
    expect(restored.theme).toBe('dark')
    restored.setTheme('light')
    expect(document.documentElement.style.getPropertyValue('--color-primary')).not.toBe(darkPrimary)
    restored.setColorPalette(defaultPalette)
    expect(restored.colorPalette).toBeNull()
    expect(localStorage.getItem('qa-portal:color-palette')).toBeNull()
    expect(document.documentElement.style.getPropertyValue('--color-primary')).toBe('')
    expect(localStorage.getItem('qa-portal:theme')).toBe('light')
    cleanup()
  })
  it('handles invalid storage and failed persistence without breaking the UI', () => {
    localStorage.setItem('qa-portal:color-palette', '{broken')
    const ui = useUiStore()
    const cleanup = ui.initialize()
    expect(ui.colorPalette).toBeNull()
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(ui.setColorPalette(ocean)).toBe(true)
    expect(ui.colorPaletteError).toContain('selama sesi ini')
    expect(document.documentElement.style.getPropertyValue('--color-primary')).toBeTruthy()
    expect(ui.setColorPalette({ ...ocean, ink: 'bad-color' })).toBe(false)
    expect(ui.colorPalette).toEqual(ocean)
    cleanup()
  })
  it('recomputes palette colors when the system switches light/dark', () => {
    const media = { matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }
    vi.mocked(window.matchMedia).mockReturnValue(media as unknown as MediaQueryList)
    const ui = useUiStore()
    ui.setTheme('system')
    ui.setColorPalette(ocean)
    const cleanup = ui.initialize()
    media.matches = true
    media.addEventListener.mock.calls[0]![1]()
    expect(ui.resolvedTheme).toBe('dark')
    expect(document.documentElement.style.getPropertyValue('--color-primary')).toBe(
      paletteTokens(ocean, true)['--color-primary'],
    )
    cleanup()
    expect(media.removeEventListener).toHaveBeenCalled()
  })
  it('previews presets without applying them until submit, and can cancel or reset', async () => {
    const wrapper = mount(WorkspacePalette, { global: { plugins: [createPinia()] } })
    const ui = useUiStore()
    const choose = async (name: string) =>
      wrapper
        .findAll('button')
        .find((button) => button.text().includes(name))!
        .trigger('click')
    await choose('Ocean')
    expect(ui.colorPalette).toBeNull()
    expect(wrapper.text()).toContain('Preview belum diterapkan')
    await choose('Batalkan perubahan')
    expect(wrapper.get('[aria-label="Preview palet"]').attributes('data-palette')).toBe('original')
    await choose('Ocean')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(ui.colorPalette).toEqual(ocean)
    expect(wrapper.text()).toContain('Palet aktif: Ocean')
    expect(wrapper.text()).toContain('Palet diterapkan dan tersimpan')
    await choose('Portal original')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(ui.colorPalette).toBeNull()
  })
  it('imports custom input, retains the draft on invalid import, and opens invalid fields on submit', async () => {
    const wrapper = mount(WorkspacePalette, {
      attachTo: document.body,
      global: { plugins: [createPinia()] },
    })
    const input = (label: string) =>
      wrapper
        .findAllComponents(UiInput)
        .find((field) => field.props('label') === label)!
        .get('input')
    const load = () =>
      wrapper
        .findAll('button')
        .find((button) => button.text() === 'Muat ke preview')!
        .trigger('click')
    await wrapper.get('textarea').setValue('#000 #333 #ccc #fff')
    await load()
    expect(input('Utama').element.value).toBe('#000000')
    await wrapper.get('textarea').setValue('not a palette')
    await load()
    expect(input('Utama').element.value).toBe('#000000')
    expect(wrapper.text()).toContain('Tempel tepat 4 kode HEX')
    await input('Utama').setValue('#zzzzzz')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('details').element.open).toBe(true)
    expect(document.activeElement).toBe(input('Utama').element)
    expect(useUiStore().colorPalette).toBeNull()
    await input('Utama').setValue('#123456')
    await wrapper.get('form').trigger('submit')
    expect(useUiStore().colorPalette?.ink).toBe('#123456')
  })
  it('adds, previews, edits and deletes named palettes without applying them automatically', async () => {
    const wrapper = mount(WorkspacePalette, {
      attachTo: document.body,
      global: { plugins: [createPinia()] },
    })
    const button = (label: string) =>
      wrapper.findAll('button').find((item) => item.text().includes(label))!
    await button('Ocean').trigger('click')
    await button('Tambah palet').trigger('click')
    const field = (label: string) =>
      wrapper
        .findAllComponents(UiInput)
        .find((input) => input.props('label') === label)!
        .get('input')
    const name = field('Nama palet')
    const submitEditor = () =>
      document
        .querySelector<HTMLFormElement>('#saved-palette-editor-form')!
        .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await name.setValue('Brand QA')
    await field('Primary').setValue('#123456')
    submitEditor()
    await flushPromises()
    expect(useUiStore().colorPalette).toBeNull()
    expect(loadSavedPalettes()).toEqual([
      { id: expect.any(String), name: 'Brand QA', colors: { ...ocean, ink: '#123456' } },
    ])
    expect(wrapper.text()).toContain('Brand QA disimpan')

    await button('Portal original').trigger('click')
    await wrapper.get('[aria-label="Gunakan palet Brand QA"]').trigger('click')
    expect(useUiStore().colorPalette).toBeNull()
    expect(wrapper.get('[aria-label="Preview palet"]').attributes('data-palette')).toBeUndefined()

    await wrapper.get('[aria-label="Edit palet Brand QA"]').trigger('click')
    await field('Nama palet').setValue('Brand Produk')
    submitEditor()
    await flushPromises()
    expect(loadSavedPalettes()).toEqual([
      {
        id: expect.any(String),
        name: 'Brand Produk',
        colors: { ...ocean, ink: '#123456' },
      },
    ])
    expect(wrapper.text()).toContain('Brand Produk diperbarui')

    await wrapper.get('[aria-label="Hapus palet Brand Produk"]').trigger('click')
    await flushPromises()
    const confirm = [...document.body.querySelectorAll('button')].find(
      (item) => item.textContent?.trim() === 'Hapus palet',
    ) as HTMLButtonElement
    confirm.click()
    await flushPromises()
    expect(loadSavedPalettes()).toEqual([])
    expect(wrapper.text()).toContain('Belum ada palet tersimpan')
    wrapper.unmount()
  })
})
