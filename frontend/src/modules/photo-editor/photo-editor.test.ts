import { describe, expect, it } from 'vitest'
import {
  assertProject,
  clipboardImageFile,
  exportFilename,
  fitLayerSize,
  fitZoom,
  normalizedSelection,
  resizeLayerBounds,
  sanitizeProjectName,
  serializeProject,
  removeEdgeBackgroundPixels,
  validateDocumentSize,
  wheelZoom,
} from './editor'

describe('photo editor document rules', () => {
  it('guards invalid and oversized documents', () => {
    expect(validateDocumentSize(1600, 900)).toBe('')
    expect(validateDocumentSize(0, 900)).toContain('minimum')
    expect(validateDocumentSize(8192, 8192)).toContain('64 megapixel')
    expect(validateDocumentSize(9000, 100)).toContain('maksimum')
  })

  it('normalizes a selection dragged in any direction', () => {
    expect(normalizedSelection(80, 60, 20, 10)).toEqual({ x: 20, y: 10, width: 60, height: 50 })
  })

  it('keeps generated filenames portable', () => {
    expect(sanitizeProjectName('  report: final?.png ')).toBe('report- final-')
    expect(exportFilename('sample.png', 'jpeg')).toBe('sample-edited.jpg')
  })

  it('reads a pasted screenshot from clipboard data', () => {
    const screenshot = new File(['pixels'], 'screenshot.png', { type: 'image/png' })
    const data = {
      items: [{ kind: 'file', type: 'image/png', getAsFile: () => screenshot }],
      files: [],
    } as unknown as DataTransfer
    expect(clipboardImageFile(data)).toBe(screenshot)
  })

  it('calculates a bounded fit zoom', () => {
    expect(fitZoom(1000, 500, 500, 500)).toBe(45)
    expect(fitZoom(100, 100, 2000, 2000)).toBe(100)
  })

  it('zooms smoothly from wheel input within editor limits', () => {
    expect(wheelZoom(100, -100)).toBeGreaterThan(100)
    expect(wheelZoom(100, 100)).toBeLessThan(100)
    expect(wheelZoom(3200, -1000)).toBe(3200)
    expect(wheelZoom(5, 1000)).toBe(5)
  })

  it('fits and fills a selected layer from its center', () => {
    expect(fitLayerSize(800, 400, 400, 400, 'contain')).toEqual({ width: 400, height: 200, x: 0, y: 100 })
    expect(fitLayerSize(800, 400, 400, 400, 'cover')).toEqual({ width: 800, height: 400, x: -200, y: 0 })
  })

  it('resizes a layer proportionally from a corner', () => {
    const bounds = { x: 10, y: 20, width: 100, height: 50 }
    expect(resizeLayerBounds(bounds, 'se', 50, 25)).toEqual({ x: 10, y: 20, width: 150, height: 75 })
    expect(resizeLayerBounds(bounds, 'nw', -50, -25)).toEqual({ x: -40, y: -5, width: 150, height: 75 })
  })

  it('removes only matching background connected to an edge', () => {
    const pixels = new Uint8ClampedArray([
      255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
      255, 255, 255, 255, 20, 20, 20, 255, 255, 255, 255, 255,
      255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
    ])
    expect(removeEdgeBackgroundPixels(pixels, 3, 3, 10)).toBe(8)
    expect(pixels[3]).toBe(0)
    expect(pixels[19]).toBe(255)
  })

  it('rejects unknown and empty project manifests', () => {
    expect(() => assertProject({ format: 'other', formatVersion: 1 })).toThrow('Format atau versi')
    expect(() =>
      assertProject({
        format: 'qa-portal-photo-editor',
        formatVersion: 1,
        width: 100,
        height: 100,
        layers: [],
      }),
    ).toThrow('Project harus memiliki')
  })

  it('serializes selection as a detached project value', () => {
    const selection = { x: 2, y: 3, width: 40, height: 20 }
    const project = serializeProject({
      name: 'test',
      width: 100,
      height: 100,
      activeLayerId: 'layer-1',
      selection,
      layers: [
        {
          id: 'layer-1',
          name: 'Layer 1',
          canvas: { toDataURL: () => 'data:image/png;base64,image' } as HTMLCanvasElement,
          target: 'content',
          visible: true,
          locked: false,
          maskEnabled: true,
          opacity: 100,
          blendMode: 'source-over',
          x: 0,
          y: 0,
          brightness: 100,
          contrast: 100,
          saturation: 100,
          blur: 0,
          preview: '',
        },
      ],
    })
    expect(project.selection).toEqual(selection)
    expect(project.selection).not.toBe(selection)
  })
})
