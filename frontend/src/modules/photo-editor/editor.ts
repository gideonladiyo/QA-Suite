export const MIN_DOCUMENT_SIZE = 1
export const MAX_DOCUMENT_SIDE = 8192
export const MAX_DOCUMENT_PIXELS = 64_000_000
export const MAX_LAYERS = 100
export const PROJECT_VERSION = 1
export const PROJECT_EXTENSION = '.qpe'

export type EditorTool = 'move' | 'select' | 'brush' | 'eraser' | 'hand' | 'zoom' | 'eyedropper'
export type LayerTarget = 'content' | 'mask'
export type BlendMode =
  | 'source-over'
  | 'multiply'
  | 'screen'
  | 'overlay'
  | 'darken'
  | 'lighten'
  | 'color-dodge'
  | 'color-burn'
  | 'hard-light'
  | 'soft-light'
  | 'difference'
  | 'hue'
  | 'saturation'
  | 'color'
  | 'luminosity'

export interface SelectionRect {
  x: number
  y: number
  width: number
  height: number
}

export type ResizeHandle = 'nw' | 'ne' | 'se' | 'sw'

export interface LayerBounds {
  x: number
  y: number
  width: number
  height: number
}

export interface EditorLayer {
  id: string
  name: string
  canvas: HTMLCanvasElement
  mask?: HTMLCanvasElement
  target: LayerTarget
  visible: boolean
  locked: boolean
  maskEnabled: boolean
  opacity: number
  blendMode: BlendMode
  x: number
  y: number
  brightness: number
  contrast: number
  saturation: number
  blur: number
  preview: string
}

export interface EditorDocument {
  name: string
  width: number
  height: number
  layers: EditorLayer[]
  activeLayerId: string
  selection: SelectionRect | null
}

export interface SerializedLayer {
  id: string
  name: string
  image: string
  mask?: string
  target: LayerTarget
  visible: boolean
  locked: boolean
  maskEnabled: boolean
  opacity: number
  blendMode: BlendMode
  x: number
  y: number
  brightness: number
  contrast: number
  saturation: number
  blur: number
}

export interface SerializedProject {
  format: 'qa-portal-photo-editor'
  formatVersion: number
  name: string
  width: number
  height: number
  activeLayerId: string
  selection: SelectionRect | null
  layers: SerializedLayer[]
  savedAt: string
}

export interface HistoryEntry {
  label: string
  project: SerializedProject
}

export const blendOptions: readonly { value: BlendMode; label: string }[] = [
  { value: 'source-over', label: 'Normal' },
  { value: 'multiply', label: 'Multiply' },
  { value: 'screen', label: 'Screen' },
  { value: 'overlay', label: 'Overlay' },
  { value: 'darken', label: 'Darken' },
  { value: 'lighten', label: 'Lighten' },
  { value: 'color-dodge', label: 'Color Dodge' },
  { value: 'color-burn', label: 'Color Burn' },
  { value: 'hard-light', label: 'Hard Light' },
  { value: 'soft-light', label: 'Soft Light' },
  { value: 'difference', label: 'Difference' },
  { value: 'hue', label: 'Hue' },
  { value: 'saturation', label: 'Saturation' },
  { value: 'color', label: 'Color' },
  { value: 'luminosity', label: 'Luminosity' },
]

export function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value))
}

export function validateDocumentSize(width: number, height: number): string {
  if (!Number.isInteger(width) || !Number.isInteger(height)) return 'Ukuran harus berupa angka bulat.'
  if (width < MIN_DOCUMENT_SIZE || height < MIN_DOCUMENT_SIZE) return 'Ukuran minimum adalah 1 × 1 px.'
  if (width > MAX_DOCUMENT_SIDE || height > MAX_DOCUMENT_SIDE)
    return `Sisi dokumen maksimum ${MAX_DOCUMENT_SIDE.toLocaleString('id-ID')} px.`
  if (width * height > MAX_DOCUMENT_PIXELS)
    return 'Dokumen melebihi batas 64 megapixel untuk menjaga browser tetap stabil.'
  return ''
}

export function sanitizeProjectName(name: string): string {
  const clean = name
    .trim()
    .replace(/\.[^.]+$/, '')
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, '-')
    .replace(/\s+/g, ' ')
    .slice(0, 80)
  return clean || 'untitled'
}

export function exportFilename(name: string, extension: 'png' | 'jpeg' | 'webp'): string {
  const suffix = extension === 'jpeg' ? 'jpg' : extension
  return `${sanitizeProjectName(name)}-edited.${suffix}`
}

export function clipboardImageFile(data: DataTransfer | null): File | null {
  if (!data) return null
  const allowed = new Set(['image/png', 'image/jpeg', 'image/webp'])
  for (const item of Array.from(data.items)) {
    if (item.kind !== 'file' || !allowed.has(item.type)) continue
    const file = item.getAsFile()
    if (file) return file
  }
  return Array.from(data.files).find((file) => allowed.has(file.type)) ?? null
}

export function fitZoom(
  documentWidth: number,
  documentHeight: number,
  viewportWidth: number,
  viewportHeight: number,
): number {
  if (documentWidth <= 0 || documentHeight <= 0 || viewportWidth <= 0 || viewportHeight <= 0)
    return 100
  return clamp(Math.floor(Math.min(viewportWidth / documentWidth, viewportHeight / documentHeight) * 90), 5, 100)
}

export function wheelZoom(currentZoom: number, deltaY: number): number {
  return Math.round(clamp(currentZoom * Math.exp(-deltaY * 0.002), 5, 3200))
}

export function normalizedSelection(startX: number, startY: number, endX: number, endY: number): SelectionRect {
  return {
    x: Math.round(Math.min(startX, endX)),
    y: Math.round(Math.min(startY, endY)),
    width: Math.round(Math.abs(endX - startX)),
    height: Math.round(Math.abs(endY - startY)),
  }
}

export function fitLayerSize(
  layerWidth: number,
  layerHeight: number,
  documentWidth: number,
  documentHeight: number,
  mode: 'contain' | 'cover',
): { width: number; height: number; x: number; y: number } {
  const scale =
    mode === 'contain'
      ? Math.min(documentWidth / layerWidth, documentHeight / layerHeight)
      : Math.max(documentWidth / layerWidth, documentHeight / layerHeight)
  const width = Math.max(1, Math.round(layerWidth * scale))
  const height = Math.max(1, Math.round(layerHeight * scale))
  return {
    width,
    height,
    x: Math.round((documentWidth - width) / 2),
    y: Math.round((documentHeight - height) / 2),
  }
}

export function resizeLayerBounds(
  bounds: LayerBounds,
  handle: ResizeHandle,
  deltaX: number,
  deltaY: number,
  minimumSize = 8,
): LayerBounds {
  const horizontalDirection = handle.includes('e') ? 1 : -1
  const verticalDirection = handle.includes('s') ? 1 : -1
  const scale = Math.max(
    minimumSize / bounds.width,
    minimumSize / bounds.height,
    1 + ((deltaX * horizontalDirection) / bounds.width + (deltaY * verticalDirection) / bounds.height) / 2,
  )
  const width = Math.max(minimumSize, Math.round(bounds.width * scale))
  const height = Math.max(minimumSize, Math.round(bounds.height * scale))
  return {
    x: handle.includes('w') ? bounds.x + bounds.width - width : bounds.x,
    y: handle.includes('n') ? bounds.y + bounds.height - height : bounds.y,
    width,
    height,
  }
}

export function removeEdgeBackgroundPixels(
  pixels: Uint8ClampedArray,
  width: number,
  height: number,
  tolerance: number,
): number {
  if (width < 1 || height < 1 || pixels.length !== width * height * 4) return 0
  const corners = [0, width - 1, (height - 1) * width, width * height - 1]
  let first = corners[0]!
  let second = corners[1]!
  let closest = Number.POSITIVE_INFINITY
  for (let left = 0; left < corners.length; left += 1) {
    for (let right = left + 1; right < corners.length; right += 1) {
      const a = corners[left]! * 4
      const b = corners[right]! * 4
      const distance =
        (pixels[a]! - pixels[b]!) ** 2 +
        (pixels[a + 1]! - pixels[b + 1]!) ** 2 +
        (pixels[a + 2]! - pixels[b + 2]!) ** 2
      if (distance < closest) {
        closest = distance
        first = corners[left]!
        second = corners[right]!
      }
    }
  }
  const firstOffset = first * 4
  const secondOffset = second * 4
  const reference = [0, 1, 2].map((channel) =>
    Math.round((pixels[firstOffset + channel]! + pixels[secondOffset + channel]!) / 2),
  )
  const threshold = (clamp(tolerance, 0, 100) * 4.42) ** 2
  const visited = new Uint8Array(width * height)
  const queue = new Int32Array(width * height)
  let head = 0
  let tail = 0
  let removed = 0

  function enqueue(index: number): void {
    if (visited[index]) return
    visited[index] = 1
    const offset = index * 4
    const transparent = pixels[offset + 3] === 0
    const distance =
      (pixels[offset]! - reference[0]!) ** 2 +
      (pixels[offset + 1]! - reference[1]!) ** 2 +
      (pixels[offset + 2]! - reference[2]!) ** 2
    if (!transparent && distance > threshold) return
    queue[tail] = index
    tail += 1
    if (!transparent) {
      pixels[offset + 3] = 0
      removed += 1
    }
  }

  for (let x = 0; x < width; x += 1) {
    enqueue(x)
    enqueue((height - 1) * width + x)
  }
  for (let y = 1; y < height - 1; y += 1) {
    enqueue(y * width)
    enqueue(y * width + width - 1)
  }
  while (head < tail) {
    const index = queue[head]!
    head += 1
    const x = index % width
    const y = Math.floor(index / width)
    if (x > 0) enqueue(index - 1)
    if (x + 1 < width) enqueue(index + 1)
    if (y > 0) enqueue(index - width)
    if (y + 1 < height) enqueue(index + width)
  }
  return removed
}

export function createCanvas(width: number, height: number): HTMLCanvasElement {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  return canvas
}

export function cloneCanvas(source: HTMLCanvasElement): HTMLCanvasElement {
  const clone = createCanvas(source.width, source.height)
  clone.getContext('2d')?.drawImage(source, 0, 0)
  return clone
}

export function makeLayer(name: string, width: number, height: number, canvas?: HTMLCanvasElement): EditorLayer {
  const pixels = canvas ?? createCanvas(width, height)
  return {
    id: crypto.randomUUID(),
    name,
    canvas: pixels,
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
    preview: makePreview(pixels),
  }
}

export function makePreview(source: HTMLCanvasElement): string {
  const preview = createCanvas(56, 42)
  const context = preview.getContext('2d')
  if (!context || !source.width || !source.height) return ''
  const scale = Math.min(preview.width / source.width, preview.height / source.height)
  const width = source.width * scale
  const height = source.height * scale
  context.drawImage(source, (preview.width - width) / 2, (preview.height - height) / 2, width, height)
  return preview.toDataURL('image/png')
}

export function layerFilter(layer: EditorLayer): string {
  return `brightness(${layer.brightness}%) contrast(${layer.contrast}%) saturate(${layer.saturation}%) blur(${layer.blur}px)`
}

export function renderDocument(editor: EditorDocument, target: HTMLCanvasElement, showSelection = false): void {
  if (target.width !== editor.width) target.width = editor.width
  if (target.height !== editor.height) target.height = editor.height
  const context = target.getContext('2d')
  if (!context) return
  context.clearRect(0, 0, target.width, target.height)

  for (const layer of editor.layers) {
    if (!layer.visible) continue
    const surface = createCanvas(editor.width, editor.height)
    const surfaceContext = surface.getContext('2d')
    if (!surfaceContext) continue
    surfaceContext.drawImage(layer.canvas, layer.x, layer.y)
    if (layer.mask && layer.maskEnabled) {
      surfaceContext.globalCompositeOperation = 'destination-in'
      surfaceContext.drawImage(layer.mask, layer.x, layer.y)
    }
    context.save()
    context.globalAlpha = layer.opacity / 100
    context.globalCompositeOperation = layer.blendMode
    context.filter = layerFilter(layer)
    context.drawImage(surface, 0, 0)
    context.restore()
  }

  if (showSelection && editor.selection) {
    const { x, y, width, height } = editor.selection
    context.save()
    context.setLineDash([7, 5])
    context.lineWidth = 1
    context.strokeStyle = '#ffffff'
    context.strokeRect(x + 0.5, y + 0.5, width, height)
    context.lineDashOffset = 6
    context.strokeStyle = '#211f32'
    context.strokeRect(x + 0.5, y + 0.5, width, height)
    context.restore()
  }
}

export function serializeProject(editor: EditorDocument): SerializedProject {
  return {
    format: 'qa-portal-photo-editor',
    formatVersion: PROJECT_VERSION,
    name: editor.name,
    width: editor.width,
    height: editor.height,
    activeLayerId: editor.activeLayerId,
    selection: editor.selection ? { ...editor.selection } : null,
    savedAt: new Date().toISOString(),
    layers: editor.layers.map((layer) => ({
      id: layer.id,
      name: layer.name,
      image: layer.canvas.toDataURL('image/png'),
      mask: layer.mask?.toDataURL('image/png'),
      target: layer.target,
      visible: layer.visible,
      locked: layer.locked,
      maskEnabled: layer.maskEnabled,
      opacity: layer.opacity,
      blendMode: layer.blendMode,
      x: layer.x,
      y: layer.y,
      brightness: layer.brightness,
      contrast: layer.contrast,
      saturation: layer.saturation,
      blur: layer.blur,
    })),
  }
}

export function assertProject(value: unknown): asserts value is SerializedProject {
  if (!value || typeof value !== 'object') throw new Error('Project tidak berisi data yang valid.')
  const project = value as Partial<SerializedProject>
  if (project.format !== 'qa-portal-photo-editor' || project.formatVersion !== PROJECT_VERSION)
    throw new Error('Format atau versi project belum didukung.')
  if (typeof project.width !== 'number' || typeof project.height !== 'number')
    throw new Error('Ukuran project tidak valid.')
  const sizeError = validateDocumentSize(project.width, project.height)
  if (sizeError) throw new Error(sizeError)
  if (!Array.isArray(project.layers) || project.layers.length < 1 || project.layers.length > MAX_LAYERS)
    throw new Error(`Project harus memiliki 1-${MAX_LAYERS} layer.`)
  if (project.layers.some((layer) => !layer || typeof layer.image !== 'string' || !layer.image.startsWith('data:image/png;base64,')))
    throw new Error('Isi layer project rusak atau tidak didukung.')
}

function loadImage(source: string | Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    const objectUrl = typeof source === 'string' ? source : URL.createObjectURL(source)
    image.onload = () => {
      if (typeof source !== 'string') URL.revokeObjectURL(objectUrl)
      resolve(image)
    }
    image.onerror = () => {
      if (typeof source !== 'string') URL.revokeObjectURL(objectUrl)
      reject(new Error('Gambar tidak dapat dibaca.'))
    }
    image.src = objectUrl
  })
}

export async function canvasFromImage(source: string | Blob): Promise<HTMLCanvasElement> {
  const image = await loadImage(source)
  const sizeError = validateDocumentSize(image.naturalWidth, image.naturalHeight)
  if (sizeError) throw new Error(sizeError)
  const canvas = createCanvas(image.naturalWidth, image.naturalHeight)
  canvas.getContext('2d')?.drawImage(image, 0, 0)
  return canvas
}

export async function hydrateProject(value: unknown): Promise<EditorDocument> {
  assertProject(value)
  const layers = await Promise.all(
    value.layers.map(async (saved): Promise<EditorLayer> => {
      const canvas = await canvasFromImage(saved.image)
      const mask = saved.mask ? await canvasFromImage(saved.mask) : undefined
      return {
        ...saved,
        canvas,
        mask,
        target: saved.target === 'mask' && mask ? 'mask' : 'content',
        preview: makePreview(canvas),
      }
    }),
  )
  const activeLayerId = layers.some((layer) => layer.id === value.activeLayerId)
    ? value.activeLayerId
    : layers.at(-1)!.id
  return {
    name: sanitizeProjectName(value.name),
    width: value.width,
    height: value.height,
    layers,
    activeLayerId,
    selection: value.selection,
  }
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

export function canvasToBlob(canvas: HTMLCanvasElement, type: string, quality?: number): Promise<Blob> {
  return new Promise((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('Browser gagal membuat file gambar.'))), type, quality),
  )
}

const DB_NAME = 'qa-portal-photo-editor'
const STORE_NAME = 'recovery'
const RECOVERY_KEY = 'latest'

function recoveryStore(mode: IDBTransactionMode): Promise<IDBObjectStore> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => request.result.createObjectStore(STORE_NAME)
    request.onerror = () => reject(new Error('Penyimpanan recovery tidak tersedia.'))
    request.onsuccess = () => resolve(request.result.transaction(STORE_NAME, mode).objectStore(STORE_NAME))
  })
}

export async function saveRecovery(project: SerializedProject): Promise<void> {
  const store = await recoveryStore('readwrite')
  await new Promise<void>((resolve, reject) => {
    const request = store.put(project, RECOVERY_KEY)
    request.onsuccess = () => resolve()
    request.onerror = () => reject(new Error('Autosave gagal. Unduh project untuk mengamankan perubahan.'))
  })
}

export async function loadRecovery(): Promise<SerializedProject | null> {
  const store = await recoveryStore('readonly')
  return new Promise((resolve, reject) => {
    const request = store.get(RECOVERY_KEY)
    request.onsuccess = () => resolve((request.result as SerializedProject | undefined) ?? null)
    request.onerror = () => reject(new Error('Recovery tidak dapat dibaca.'))
  })
}

export async function clearRecovery(): Promise<void> {
  const store = await recoveryStore('readwrite')
  await new Promise<void>((resolve, reject) => {
    const request = store.delete(RECOVERY_KEY)
    request.onsuccess = () => resolve()
    request.onerror = () => reject(new Error('Recovery tidak dapat dibersihkan.'))
  })
}
