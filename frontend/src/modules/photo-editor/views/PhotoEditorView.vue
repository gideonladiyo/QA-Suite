<script setup lang="ts">
import {
  computed,
  markRaw,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  type Component,
} from 'vue'
import {
  PhArrowClockwise,
  PhArrowCounterClockwise,
  PhArrowDown,
  PhArrowUp,
  PhCheck,
  PhCircleHalf,
  PhClockCounterClockwise,
  PhCopy,
  PhCrop,
  PhCursor,
  PhDownloadSimple,
  PhEraser,
  PhEye,
  PhEyeSlash,
  PhEyedropper,
  PhFloppyDisk,
  PhFolderOpen,
  PhHand,
  PhImageSquare,
  PhLock,
  PhLockOpen,
  PhMagnifyingGlassPlus,
  PhPaintBrush,
  PhPlus,
  PhSelection,
  PhSliders,
  PhStack,
  PhTrash,
} from '@phosphor-icons/vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiConfirmDialog from '../../../shared/components/ui/UiConfirmDialog.vue'
import UiModal from '../../../shared/components/ui/UiModal.vue'
import { useToast } from '../../../shared/composables/useToast'
import {
  MAX_LAYERS,
  PROJECT_EXTENSION,
  blendOptions,
  canvasFromImage,
  canvasToBlob,
  clipboardImageFile,
  clamp,
  clearRecovery,
  cloneCanvas,
  createCanvas,
  downloadBlob,
  exportFilename,
  fitLayerSize,
  fitZoom,
  hydrateProject,
  loadRecovery,
  makeLayer,
  makePreview,
  normalizedSelection,
  removeEdgeBackgroundPixels,
  resizeLayerBounds,
  renderDocument,
  sanitizeProjectName,
  saveRecovery,
  serializeProject,
  validateDocumentSize,
  wheelZoom,
  type EditorDocument,
  type EditorLayer,
  type EditorTool,
  type HistoryEntry,
  type LayerBounds,
  type ResizeHandle,
  type SerializedProject,
} from '../editor'

interface ToolItem {
  id: EditorTool
  label: string
  shortcut: string
  icon: Component
}

const tools: readonly ToolItem[] = [
  { id: 'move', label: 'Pindahkan layer', shortcut: 'V', icon: PhCursor },
  { id: 'select', label: 'Seleksi kotak', shortcut: 'M', icon: PhSelection },
  { id: 'brush', label: 'Brush', shortcut: 'B', icon: PhPaintBrush },
  { id: 'eraser', label: 'Eraser', shortcut: 'E', icon: PhEraser },
  { id: 'eyedropper', label: 'Ambil warna', shortcut: 'I', icon: PhEyedropper },
  { id: 'hand', label: 'Geser canvas', shortcut: 'H', icon: PhHand },
  { id: 'zoom', label: 'Zoom', shortcut: 'Z', icon: PhMagnifyingGlassPlus },
]

const { notify } = useToast()
const fileInput = ref<HTMLInputElement>()
const viewport = ref<HTMLElement>()
const displayCanvas = ref<HTMLCanvasElement>()
const editor = ref<EditorDocument | null>(null)
const activeTool = ref<EditorTool>('move')
const zoom = ref(100)
const brushSize = ref(28)
const brushOpacity = ref(100)
const foreground = ref('#e14d67')
const maskPaint = ref<'hide' | 'reveal'>('hide')
const inspectorTab = ref<'layers' | 'properties' | 'history'>('layers')
const busy = ref(false)
const error = ref('')
const dirty = ref(false)
const autosaveState = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const recovery = ref<SerializedProject | null>(null)
const history = ref<HistoryEntry[]>([])
const historyIndex = ref(-1)
const newOpen = ref(false)
const newWidth = ref('1600')
const newHeight = ref('1000')
const newBackground = ref('#ffffff')
const transparentBackground = ref(false)
const exportOpen = ref(false)
const exportFormat = ref<'png' | 'jpeg' | 'webp'>('png')
const exportQuality = ref(90)
const exportBackground = ref('#ffffff')
const removeBackgroundTolerance = ref(18)
const hoverHandle = ref<ResizeHandle | null>(null)
const hoveredLayerId = ref<string | null>(null)
const transformMode = ref<'move' | 'resize' | null>(null)
const confirmOpen = ref(false)
const confirmKind = ref<'replace' | 'layer' | 'mask'>('replace')
const pendingFile = ref<File | null>(null)
const fileIntent = ref<'open' | 'layer'>('open')
const spacePressed = ref(false)
const panning = ref(false)

let frame = 0
let autosaveTimer: ReturnType<typeof setTimeout> | undefined
let drawing = false
let pointerStart = { x: 0, y: 0 }
let previousPoint = { x: 0, y: 0 }
let layerStart = { x: 0, y: 0 }
let scrollStart = { left: 0, top: 0 }
let panPointerStart = { x: 0, y: 0 }
let activeResizeHandle: ResizeHandle | null = null
let resizeStart: LayerBounds | null = null
let resizeSource: HTMLCanvasElement | null = null
let resizeMaskSource: HTMLCanvasElement | null = null

const activeLayer = computed(() =>
  editor.value?.layers.find((layer) => layer.id === editor.value?.activeLayerId),
)
const displayLayers = computed(() => [...(editor.value?.layers ?? [])].reverse())
const canUndo = computed(() => historyIndex.value > 0 && !busy.value)
const canRedo = computed(() => historyIndex.value >= 0 && historyIndex.value < history.value.length - 1 && !busy.value)
const canvasStyle = computed(() => {
  if (!editor.value) return {}
  let cursor: string | undefined
  if (activeTool.value === 'move') {
    const handle = activeResizeHandle ?? hoverHandle.value
    if (handle === 'nw' || handle === 'se') cursor = 'nwse-resize'
    else if (handle === 'ne' || handle === 'sw') cursor = 'nesw-resize'
    else if (transformMode.value === 'move') cursor = 'grabbing'
    else cursor = hoveredLayerId.value ? 'move' : 'default'
  }
  return {
    width: `${editor.value.width * (zoom.value / 100)}px`,
    height: `${editor.value.height * (zoom.value / 100)}px`,
    cursor,
  }
})
const canvasStageStyle = computed(() => {
  if (!editor.value) return {}
  const scale = zoom.value / 100
  return {
    width: `max(200%, ${editor.value.width * scale + 128}px)`,
    height: `max(200%, ${editor.value.height * scale + 128}px)`,
  }
})
const statusText = computed(() => {
  if (!editor.value) return 'Belum ada dokumen'
  if (autosaveState.value === 'saving') return 'Menyimpan recovery...'
  if (autosaveState.value === 'error') return 'Recovery gagal. Unduh project untuk backup.'
  if (dirty.value) return autosaveState.value === 'saved' ? 'Recovery tersimpan' : 'Perubahan belum diunduh'
  return 'Project sudah diunduh'
})
const newSizeError = computed(() => validateDocumentSize(Number(newWidth.value), Number(newHeight.value)))

function makeCanvasesRaw(documentValue: EditorDocument): EditorDocument {
  documentValue.layers.forEach((layer) => {
    layer.canvas = markRaw(layer.canvas)
    if (layer.mask) layer.mask = markRaw(layer.mask)
  })
  return documentValue
}

function render(): void {
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(() => {
    if (editor.value && displayCanvas.value) {
      renderDocument(editor.value, displayCanvas.value, true)
      if (activeTool.value === 'move') drawTransformControls()
    }
  })
}

function layerBounds(layer: EditorLayer): LayerBounds {
  return { x: layer.x, y: layer.y, width: layer.canvas.width, height: layer.canvas.height }
}

function transformHandles(layer: EditorLayer): Record<ResizeHandle, { x: number; y: number }> {
  return {
    nw: { x: layer.x, y: layer.y },
    ne: { x: layer.x + layer.canvas.width, y: layer.y },
    se: { x: layer.x + layer.canvas.width, y: layer.y + layer.canvas.height },
    sw: { x: layer.x, y: layer.y + layer.canvas.height },
  }
}

function drawTransformControls(): void {
  const layer = activeLayer.value
  const canvas = displayCanvas.value
  if (!layer?.visible || !canvas) return
  const context = canvas.getContext('2d')
  if (!context) return
  const scale = zoom.value / 100
  const handleSize = 10 / scale
  context.save()
  context.lineWidth = 3 / scale
  context.strokeStyle = '#ffffff'
  context.strokeRect(layer.x, layer.y, layer.canvas.width, layer.canvas.height)
  context.lineWidth = 1.5 / scale
  context.strokeStyle = '#e56f51'
  context.strokeRect(layer.x, layer.y, layer.canvas.width, layer.canvas.height)
  if (!layer.locked) {
    for (const point of Object.values(transformHandles(layer))) {
      context.fillStyle = '#ffffff'
      context.fillRect(point.x - handleSize / 2, point.y - handleSize / 2, handleSize, handleSize)
      context.lineWidth = 1.5 / scale
      context.strokeStyle = '#e56f51'
      context.strokeRect(point.x - handleSize / 2, point.y - handleSize / 2, handleSize, handleSize)
    }
  }
  context.restore()
}

function updateActivePreview(): void {
  if (activeLayer.value) activeLayer.value.preview = makePreview(activeLayer.value.canvas)
}

function resetHistory(label: string): void {
  if (!editor.value) return
  history.value = [{ label, project: serializeProject(editor.value) }]
  historyIndex.value = 0
}

function scheduleAutosave(): void {
  if (!editor.value) return
  clearTimeout(autosaveTimer)
  autosaveState.value = 'saving'
  const snapshot = serializeProject(editor.value)
  autosaveTimer = setTimeout(async () => {
    try {
      await saveRecovery(snapshot)
      autosaveState.value = 'saved'
      recovery.value = snapshot
    } catch (cause) {
      autosaveState.value = 'error'
      error.value = cause instanceof Error ? cause.message : 'Autosave gagal.'
    }
  }, 700)
}

function commit(label: string, updatePreview = true): void {
  if (!editor.value) return
  if (updatePreview) updateActivePreview()
  history.value.splice(historyIndex.value + 1)
  history.value.push({ label, project: serializeProject(editor.value) })
  // ponytail: full snapshots keep v1 reliable; replace with delta checkpoints when profiling shows memory pressure.
  if (history.value.length > 12) history.value.shift()
  historyIndex.value = history.value.length - 1
  dirty.value = true
  scheduleAutosave()
  render()
}

async function restoreHistory(index: number): Promise<void> {
  const entry = history.value[index]
  if (!entry || busy.value) return
  busy.value = true
  error.value = ''
  try {
    editor.value = makeCanvasesRaw(await hydrateProject(entry.project))
    historyIndex.value = index
    dirty.value = true
    await nextTick()
    render()
    scheduleAutosave()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'History tidak dapat dipulihkan.'
  } finally {
    busy.value = false
  }
}

function undo(): void {
  if (canUndo.value) void restoreHistory(historyIndex.value - 1)
}

function redo(): void {
  if (canRedo.value) void restoreHistory(historyIndex.value + 1)
}

function fitCanvas(): void {
  if (!editor.value || !viewport.value) return
  zoom.value = fitZoom(
    editor.value.width,
    editor.value.height,
    viewport.value.clientWidth - 64,
    viewport.value.clientHeight - 64,
  )
  render()
  void nextTick().then(centerCanvas)
}

function setZoom(value: number): void {
  zoom.value = clamp(Math.round(value), 5, 3200)
  render()
}

function centerCanvas(): void {
  if (!viewport.value) return
  viewport.value.scrollLeft = (viewport.value.scrollWidth - viewport.value.clientWidth) / 2
  viewport.value.scrollTop = (viewport.value.scrollHeight - viewport.value.clientHeight) / 2
}

function zoomAt(value: number, clientX: number, clientY: number): void {
  const view = viewport.value
  const canvas = displayCanvas.value
  if (!view || !canvas) return
  const before = canvas.getBoundingClientRect()
  const ratioX = before.width ? (clientX - before.left) / before.width : 0.5
  const ratioY = before.height ? (clientY - before.top) / before.height : 0.5
  setZoom(value)
  void nextTick().then(() => {
    const after = canvas.getBoundingClientRect()
    view.scrollLeft += after.left + ratioX * after.width - clientX
    view.scrollTop += after.top + ratioY * after.height - clientY
  })
}

function onWheel(event: WheelEvent): void {
  if (!editor.value || (!event.ctrlKey && !event.metaKey)) return
  event.preventDefault()
  zoomAt(wheelZoom(zoom.value, event.deltaY), event.clientX, event.clientY)
}

function onViewportPointerDown(event: PointerEvent): void {
  if ((!spacePressed.value && activeTool.value !== 'hand') || !viewport.value) return
  if (event.button !== 0 && event.button !== 1) return
  event.preventDefault()
  event.stopPropagation()
  panning.value = true
  panPointerStart = { x: event.clientX, y: event.clientY }
  scrollStart = { left: viewport.value.scrollLeft, top: viewport.value.scrollTop }
  viewport.value.setPointerCapture(event.pointerId)
}

function onViewportPointerMove(event: PointerEvent): void {
  if (!panning.value || !viewport.value) return
  viewport.value.scrollLeft = scrollStart.left - (event.clientX - panPointerStart.x)
  viewport.value.scrollTop = scrollStart.top - (event.clientY - panPointerStart.y)
}

function onViewportPointerUp(event: PointerEvent): void {
  if (!panning.value || !viewport.value) return
  panning.value = false
  if (viewport.value.hasPointerCapture(event.pointerId)) {
    viewport.value.releasePointerCapture(event.pointerId)
  }
}

function setActiveTool(tool: EditorTool): void {
  activeTool.value = tool
  hoverHandle.value = null
  hoveredLayerId.value = null
  render()
}

function selectFile(intent: 'open' | 'layer'): void {
  fileIntent.value = intent
  fileInput.value?.click()
}

async function loadImageFile(file: File, asLayer: boolean): Promise<void> {
  const canvas = markRaw(await canvasFromImage(file))
  const name = sanitizeProjectName(file.name)
  if (asLayer && editor.value) {
    if (editor.value.layers.length >= MAX_LAYERS) throw new Error(`Maksimum ${MAX_LAYERS} layer.`)
    const layer = makeLayer(name, canvas.width, canvas.height, canvas)
    layer.canvas = markRaw(layer.canvas)
    fitLayerToDocument(layer, 'contain')
    editor.value.layers.push(layer)
    editor.value.activeLayerId = layer.id
    inspectorTab.value = 'layers'
    commit('Tambah gambar')
    return
  }
  const layer = makeLayer(name, canvas.width, canvas.height, canvas)
  layer.canvas = markRaw(layer.canvas)
  editor.value = {
    name,
    width: canvas.width,
    height: canvas.height,
    layers: [layer],
    activeLayerId: layer.id,
    selection: null,
  }
  dirty.value = false
  autosaveState.value = 'idle'
  resetHistory('Buka gambar')
  await nextTick()
  fitCanvas()
  render()
}

function fitLayerToDocument(layer: EditorLayer, mode: 'contain' | 'cover'): void {
  if (!editor.value) return
  const placement = fitLayerSize(
    layer.canvas.width,
    layer.canvas.height,
    editor.value.width,
    editor.value.height,
    mode,
  )
  if (placement.width !== layer.canvas.width || placement.height !== layer.canvas.height) {
    const resized = createCanvas(placement.width, placement.height)
    resized.getContext('2d')?.drawImage(layer.canvas, 0, 0, placement.width, placement.height)
    layer.canvas = markRaw(resized)
    if (layer.mask) {
      const resizedMask = createCanvas(placement.width, placement.height)
      resizedMask.getContext('2d')?.drawImage(layer.mask, 0, 0, placement.width, placement.height)
      layer.mask = markRaw(resizedMask)
    }
    layer.preview = makePreview(layer.canvas)
  }
  layer.x = placement.x
  layer.y = placement.y
}

function fitActiveLayer(mode: 'contain' | 'cover'): void {
  if (!activeLayer.value || activeLayer.value.locked) return
  fitLayerToDocument(activeLayer.value, mode)
  commit(mode === 'contain' ? 'Fit layer ke canvas' : 'Isi canvas dengan layer', false)
}

function alignActiveLayer(horizontal?: 'left' | 'center' | 'right', vertical?: 'top' | 'middle' | 'bottom'): void {
  if (!editor.value || !activeLayer.value || activeLayer.value.locked) return
  if (horizontal === 'left') activeLayer.value.x = 0
  if (horizontal === 'center') activeLayer.value.x = Math.round((editor.value.width - activeLayer.value.canvas.width) / 2)
  if (horizontal === 'right') activeLayer.value.x = editor.value.width - activeLayer.value.canvas.width
  if (vertical === 'top') activeLayer.value.y = 0
  if (vertical === 'middle') activeLayer.value.y = Math.round((editor.value.height - activeLayer.value.canvas.height) / 2)
  if (vertical === 'bottom') activeLayer.value.y = editor.value.height - activeLayer.value.canvas.height
  commit('Align layer', false)
}

function addPlainBackground(): void {
  if (!editor.value) return
  if (editor.value.layers.length >= MAX_LAYERS) {
    error.value = `Maksimum ${MAX_LAYERS} layer.`
    return
  }
  const canvas = markRaw(createCanvas(editor.value.width, editor.value.height))
  const context = canvas.getContext('2d')
  if (!context) return
  context.fillStyle = '#ffffff'
  context.fillRect(0, 0, canvas.width, canvas.height)
  const layer = makeLayer('Background putih', canvas.width, canvas.height, canvas)
  layer.canvas = markRaw(layer.canvas)
  editor.value.layers.unshift(layer)
  commit('Tambah background putih', false)
}

async function autoRemoveBackground(): Promise<void> {
  const layer = activeLayer.value
  if (!layer || layer.locked || busy.value) return
  if (layer.canvas.width * layer.canvas.height > 16_000_000) {
    error.value = 'Auto Remove BG dibatasi sampai 16 megapixel agar browser tetap stabil.'
    return
  }
  busy.value = true
  error.value = ''
  await nextTick()
  await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
  try {
    const context = layer.canvas.getContext('2d', { willReadFrequently: true })
    const image = context?.getImageData(0, 0, layer.canvas.width, layer.canvas.height)
    if (!context || !image) throw new Error('Piksel gambar tidak dapat dibaca.')
    const removed = removeEdgeBackgroundPixels(
      image.data,
      layer.canvas.width,
      layer.canvas.height,
      removeBackgroundTolerance.value,
    )
    if (!removed) throw new Error('Background polos yang terhubung ke tepi tidak ditemukan. Coba naikkan tolerance.')
    context.putImageData(image, 0, 0)
    layer.target = 'content'
    commit('Auto Remove BG')
    notify(`Background dihapus dari ${removed.toLocaleString('id-ID')} piksel.`)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Background gagal dihapus.'
  } finally {
    busy.value = false
  }
}

async function loadProjectFile(file: File): Promise<void> {
  const text = await file.text()
  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch {
    throw new Error('Project bukan file JSON yang valid.')
  }
  editor.value = makeCanvasesRaw(await hydrateProject(parsed))
  dirty.value = false
  autosaveState.value = 'idle'
  resetHistory('Buka project')
  await nextTick()
  fitCanvas()
  render()
}

async function loadFile(file: File, asLayer = false): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    if (file.size > 200 * 1024 * 1024) throw new Error('File melebihi batas 200 MB.')
    if (file.name.toLowerCase().endsWith(PROJECT_EXTENSION)) {
      if (asLayer) throw new Error('Project hanya dapat dibuka sebagai dokumen, bukan sebagai layer.')
      await loadProjectFile(file)
    } else if (['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      await loadImageFile(file, asLayer)
    } else {
      throw new Error('Gunakan PNG, JPEG, WebP, atau project .qpe.')
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'File tidak dapat dibuka.'
  } finally {
    busy.value = false
  }
}

function requestLoad(file: File, asLayer: boolean): void {
  if (editor.value && dirty.value && !asLayer) {
    pendingFile.value = file
    confirmKind.value = 'replace'
    confirmOpen.value = true
    return
  }
  void loadFile(file, asLayer)
}

function onFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) requestLoad(file, fileIntent.value === 'layer')
  input.value = ''
}

function onDrop(event: DragEvent): void {
  const file = event.dataTransfer?.files[0]
  if (!file) return
  const asLayer = Boolean(editor.value && !file.name.toLowerCase().endsWith(PROJECT_EXTENSION))
  requestLoad(file, asLayer)
}

function onPaste(event: ClipboardEvent): void {
  const file = clipboardImageFile(event.clipboardData)
  if (!file) return
  event.preventDefault()
  requestLoad(file, Boolean(editor.value))
}

async function confirmDestructive(): Promise<void> {
  confirmOpen.value = false
  if (confirmKind.value === 'replace' && pendingFile.value) {
    const file = pendingFile.value
    pendingFile.value = null
    await loadFile(file)
  } else if (confirmKind.value === 'layer') {
    deleteActiveLayer()
  } else if (confirmKind.value === 'mask') {
    removeActiveMask()
  }
}

function createNewDocument(): void {
  const width = Number(newWidth.value)
  const height = Number(newHeight.value)
  if (validateDocumentSize(width, height)) return
  const canvas = markRaw(createCanvas(width, height))
  if (!transparentBackground.value) {
    const context = canvas.getContext('2d')
    if (context) {
      context.fillStyle = newBackground.value
      context.fillRect(0, 0, width, height)
    }
  }
  const layer = makeLayer('Background', width, height, canvas)
  layer.canvas = markRaw(layer.canvas)
  editor.value = {
    name: 'untitled',
    width,
    height,
    layers: [layer],
    activeLayerId: layer.id,
    selection: null,
  }
  newOpen.value = false
  dirty.value = true
  resetHistory('Dokumen baru')
  scheduleAutosave()
  void nextTick().then(() => {
    fitCanvas()
    render()
  })
}

async function restoreRecovery(): Promise<void> {
  if (!recovery.value) return
  busy.value = true
  error.value = ''
  try {
    editor.value = makeCanvasesRaw(await hydrateProject(recovery.value))
    dirty.value = true
    autosaveState.value = 'saved'
    resetHistory('Pulihkan recovery')
    await nextTick()
    fitCanvas()
    render()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Recovery gagal dipulihkan.'
  } finally {
    busy.value = false
  }
}

function addLayer(): void {
  if (!editor.value || editor.value.layers.length >= MAX_LAYERS) return
  const layer = makeLayer(`Layer ${editor.value.layers.length + 1}`, editor.value.width, editor.value.height)
  layer.canvas = markRaw(layer.canvas)
  editor.value.layers.push(layer)
  editor.value.activeLayerId = layer.id
  commit('Tambah layer')
}

function duplicateLayer(): void {
  if (!editor.value || !activeLayer.value || editor.value.layers.length >= MAX_LAYERS) return
  const source = activeLayer.value
  const copy: EditorLayer = {
    ...source,
    id: crypto.randomUUID(),
    name: `${source.name} copy`,
    canvas: markRaw(cloneCanvas(source.canvas)),
    mask: source.mask ? markRaw(cloneCanvas(source.mask)) : undefined,
    preview: source.preview,
  }
  const index = editor.value.layers.indexOf(source)
  editor.value.layers.splice(index + 1, 0, copy)
  editor.value.activeLayerId = copy.id
  commit('Duplikat layer', false)
}

function requestDeleteLayer(): void {
  if (!editor.value || !activeLayer.value || editor.value.layers.length === 1) return
  confirmKind.value = 'layer'
  confirmOpen.value = true
}

function deleteActiveLayer(): void {
  if (!editor.value || !activeLayer.value || editor.value.layers.length === 1) return
  const index = editor.value.layers.indexOf(activeLayer.value)
  editor.value.layers.splice(index, 1)
  editor.value.activeLayerId = editor.value.layers[Math.max(0, index - 1)]!.id
  commit('Hapus layer', false)
}

function moveLayer(direction: 1 | -1): void {
  if (!editor.value || !activeLayer.value) return
  const index = editor.value.layers.indexOf(activeLayer.value)
  const next = index + direction
  if (next < 0 || next >= editor.value.layers.length) return
  const [layer] = editor.value.layers.splice(index, 1)
  editor.value.layers.splice(next, 0, layer!)
  commit(direction > 0 ? 'Naikkan layer' : 'Turunkan layer', false)
}

function toggleLayerVisibility(layer: EditorLayer): void {
  layer.visible = !layer.visible
  commit(layer.visible ? 'Tampilkan layer' : 'Sembunyikan layer', false)
}

function toggleLayerLock(layer: EditorLayer): void {
  layer.locked = !layer.locked
  commit(layer.locked ? 'Kunci layer' : 'Buka kunci layer', false)
}

function selectLayer(layer: EditorLayer, target: 'content' | 'mask' = 'content'): void {
  if (!editor.value) return
  editor.value.activeLayerId = layer.id
  layer.target = target === 'mask' && layer.mask ? 'mask' : 'content'
  render()
}

function addMask(fromSelection: boolean): void {
  if (!editor.value || !activeLayer.value) return
  const layer = activeLayer.value
  const mask = markRaw(createCanvas(layer.canvas.width, layer.canvas.height))
  const context = mask.getContext('2d')
  if (!context) return
  context.fillStyle = fromSelection ? '#000000' : '#ffffff'
  context.fillRect(0, 0, mask.width, mask.height)
  if (fromSelection && editor.value.selection) {
    const selection = editor.value.selection
    context.fillStyle = '#ffffff'
    context.fillRect(selection.x - layer.x, selection.y - layer.y, selection.width, selection.height)
  }
  layer.mask = mask
  layer.maskEnabled = true
  layer.target = 'mask'
  activeTool.value = 'brush'
  maskPaint.value = 'hide'
  commit(fromSelection && editor.value.selection ? 'Mask dari seleksi' : 'Tambah mask', false)
}

function requestRemoveMask(): void {
  if (!activeLayer.value?.mask) return
  confirmKind.value = 'mask'
  confirmOpen.value = true
}

function removeActiveMask(): void {
  if (!activeLayer.value?.mask) return
  activeLayer.value.mask = undefined
  activeLayer.value.target = 'content'
  commit('Hapus mask', false)
}

function invertMask(): void {
  const mask = activeLayer.value?.mask
  if (!mask) return
  const context = mask.getContext('2d')
  const image = context?.getImageData(0, 0, mask.width, mask.height)
  if (!context || !image) return
  for (let index = 0; index < image.data.length; index += 4) {
    image.data[index] = 255 - image.data[index]!
    image.data[index + 1] = 255 - image.data[index + 1]!
    image.data[index + 2] = 255 - image.data[index + 2]!
  }
  context.putImageData(image, 0, 0)
  commit('Balik mask', false)
}

function cropToSelection(): void {
  if (!editor.value?.selection || editor.value.selection.width < 1 || editor.value.selection.height < 1) return
  const selection = editor.value.selection
  for (const layer of editor.value.layers) {
    const aligned = createCanvas(editor.value.width, editor.value.height)
    aligned.getContext('2d')?.drawImage(layer.canvas, layer.x, layer.y)
    const cropped = createCanvas(selection.width, selection.height)
    cropped
      .getContext('2d')
      ?.drawImage(aligned, selection.x, selection.y, selection.width, selection.height, 0, 0, selection.width, selection.height)
    layer.canvas = markRaw(cropped)
    if (layer.mask) {
      const alignedMask = createCanvas(editor.value.width, editor.value.height)
      alignedMask.getContext('2d')?.drawImage(layer.mask, layer.x, layer.y)
      const croppedMask = createCanvas(selection.width, selection.height)
      croppedMask
        .getContext('2d')
        ?.drawImage(
          alignedMask,
          selection.x,
          selection.y,
          selection.width,
          selection.height,
          0,
          0,
          selection.width,
          selection.height,
        )
      layer.mask = markRaw(croppedMask)
    }
    layer.x = 0
    layer.y = 0
    layer.preview = makePreview(layer.canvas)
  }
  editor.value.width = selection.width
  editor.value.height = selection.height
  editor.value.selection = null
  commit('Crop ke seleksi', false)
  void nextTick().then(fitCanvas)
}

function rotateDocument(): void {
  if (!editor.value) return
  const oldWidth = editor.value.width
  const oldHeight = editor.value.height
  for (const layer of editor.value.layers) {
    const aligned = createCanvas(oldWidth, oldHeight)
    aligned.getContext('2d')?.drawImage(layer.canvas, layer.x, layer.y)
    const rotated = createCanvas(oldHeight, oldWidth)
    const context = rotated.getContext('2d')
    context?.translate(oldHeight, 0)
    context?.rotate(Math.PI / 2)
    context?.drawImage(aligned, 0, 0)
    layer.canvas = markRaw(rotated)
    if (layer.mask) {
      const alignedMask = createCanvas(oldWidth, oldHeight)
      alignedMask.getContext('2d')?.drawImage(layer.mask, layer.x, layer.y)
      const rotatedMask = createCanvas(oldHeight, oldWidth)
      const maskContext = rotatedMask.getContext('2d')
      maskContext?.translate(oldHeight, 0)
      maskContext?.rotate(Math.PI / 2)
      maskContext?.drawImage(alignedMask, 0, 0)
      layer.mask = markRaw(rotatedMask)
    }
    layer.x = 0
    layer.y = 0
    layer.preview = makePreview(layer.canvas)
  }
  editor.value.width = oldHeight
  editor.value.height = oldWidth
  editor.value.selection = null
  commit('Putar dokumen 90°', false)
  void nextTick().then(fitCanvas)
}

function getPoint(event: PointerEvent): { x: number; y: number } {
  const rect = displayCanvas.value!.getBoundingClientRect()
  return {
    x: clamp(((event.clientX - rect.left) / rect.width) * editor.value!.width, 0, editor.value!.width),
    y: clamp(((event.clientY - rect.top) / rect.height) * editor.value!.height, 0, editor.value!.height),
  }
}

function pointInLayerBounds(point: { x: number; y: number }, layer: EditorLayer): boolean {
  return point.x >= layer.x && point.x <= layer.x + layer.canvas.width
    && point.y >= layer.y && point.y <= layer.y + layer.canvas.height
}

function resizeHandleAt(point: { x: number; y: number }): ResizeHandle | null {
  const layer = activeLayer.value
  if (!layer?.visible || layer.locked) return null
  const radius = 9 / (zoom.value / 100)
  for (const [handle, position] of Object.entries(transformHandles(layer)) as [ResizeHandle, { x: number; y: number }][]) {
    if (Math.abs(point.x - position.x) <= radius && Math.abs(point.y - position.y) <= radius) return handle
  }
  return null
}

function layerAt(point: { x: number; y: number }): EditorLayer | undefined {
  if (!editor.value) return undefined
  for (let index = editor.value.layers.length - 1; index >= 0; index -= 1) {
    const layer = editor.value.layers[index]!
    if (!layer.visible || layer.opacity === 0 || !pointInLayerBounds(point, layer)) continue
    const x = Math.min(layer.canvas.width - 1, Math.max(0, Math.floor(point.x - layer.x)))
    const y = Math.min(layer.canvas.height - 1, Math.max(0, Math.floor(point.y - layer.y)))
    const alpha = layer.canvas.getContext('2d', { willReadFrequently: true })?.getImageData(x, y, 1, 1).data[3] ?? 0
    if (alpha > 8) return layer
  }
  return undefined
}

function updateMoveHover(event: PointerEvent): void {
  if (activeTool.value !== 'move' || drawing || !editor.value) return
  const point = getPoint(event)
  hoverHandle.value = resizeHandleAt(point)
  hoveredLayerId.value = hoverHandle.value ? activeLayer.value?.id ?? null : layerAt(point)?.id ?? null
}

function clearMoveHover(): void {
  if (drawing) return
  hoverHandle.value = null
  hoveredLayerId.value = null
}

function resizeActiveLayer(point: { x: number; y: number }): void {
  const layer = activeLayer.value
  if (!layer || !resizeStart || !resizeSource || !activeResizeHandle) return
  const bounds = resizeLayerBounds(
    resizeStart,
    activeResizeHandle,
    point.x - pointerStart.x,
    point.y - pointerStart.y,
  )
  const resized = createCanvas(bounds.width, bounds.height)
  resized.getContext('2d')?.drawImage(resizeSource, 0, 0, bounds.width, bounds.height)
  layer.canvas = markRaw(resized)
  if (resizeMaskSource) {
    const mask = createCanvas(bounds.width, bounds.height)
    mask.getContext('2d')?.drawImage(resizeMaskSource, 0, 0, bounds.width, bounds.height)
    layer.mask = markRaw(mask)
  }
  layer.x = bounds.x
  layer.y = bounds.y
}

function paintSegment(from: { x: number; y: number }, to: { x: number; y: number }): void {
  const layer = activeLayer.value
  const documentValue = editor.value
  if (!layer || !documentValue || layer.locked) return
  const target = layer.target === 'mask' && layer.mask ? layer.mask : layer.canvas
  const context = target.getContext('2d')
  if (!context) return
  context.save()
  if (documentValue.selection) {
    const selection = documentValue.selection
    context.beginPath()
    context.rect(selection.x - layer.x, selection.y - layer.y, selection.width, selection.height)
    context.clip()
  }
  context.lineCap = 'round'
  context.lineJoin = 'round'
  context.lineWidth = brushSize.value
  context.globalAlpha = brushOpacity.value / 100
  if (layer.target === 'mask' && layer.mask) {
    context.globalCompositeOperation = 'source-over'
    context.strokeStyle = maskPaint.value === 'reveal' ? '#ffffff' : '#000000'
  } else if (activeTool.value === 'eraser') {
    context.globalCompositeOperation = 'destination-out'
    context.strokeStyle = '#000000'
  } else {
    context.globalCompositeOperation = 'source-over'
    context.strokeStyle = foreground.value
  }
  context.beginPath()
  context.moveTo(from.x - layer.x, from.y - layer.y)
  context.lineTo(to.x - layer.x, to.y - layer.y)
  context.stroke()
  context.restore()
}

function onPointerDown(event: PointerEvent): void {
  if (!editor.value || busy.value) return
  pointerStart = getPoint(event)

  if (activeTool.value === 'move') {
    activeResizeHandle = resizeHandleAt(pointerStart)
    if (activeResizeHandle && activeLayer.value) {
      transformMode.value = 'resize'
      resizeStart = layerBounds(activeLayer.value)
      resizeSource = markRaw(cloneCanvas(activeLayer.value.canvas))
      resizeMaskSource = activeLayer.value.mask ? markRaw(cloneCanvas(activeLayer.value.mask)) : null
    } else {
      const hit = layerAt(pointerStart)
      if (!hit) return
      selectLayer(hit)
      if (hit.locked) return
      transformMode.value = 'move'
    }
  }

  if (!activeLayer.value) return
  displayCanvas.value?.setPointerCapture(event.pointerId)
  drawing = true
  previousPoint = pointerStart
  layerStart = { x: activeLayer.value.x, y: activeLayer.value.y }
  scrollStart = { left: viewport.value?.scrollLeft ?? 0, top: viewport.value?.scrollTop ?? 0 }

  if (activeTool.value === 'select') {
    editor.value.selection = { x: pointerStart.x, y: pointerStart.y, width: 0, height: 0 }
    render()
  } else if (activeTool.value === 'brush' || activeTool.value === 'eraser') {
    paintSegment(pointerStart, { x: pointerStart.x + 0.01, y: pointerStart.y + 0.01 })
    render()
  } else if (activeTool.value === 'eyedropper') {
    const sample = createCanvas(editor.value.width, editor.value.height)
    renderDocument(editor.value, sample)
    const pixel = sample.getContext('2d')?.getImageData(Math.floor(pointerStart.x), Math.floor(pointerStart.y), 1, 1).data
    if (pixel) foreground.value = `#${[pixel[0], pixel[1], pixel[2]].map((value) => value!.toString(16).padStart(2, '0')).join('')}`
    drawing = false
  } else if (activeTool.value === 'zoom') {
    zoomAt(zoom.value * (event.altKey ? 0.8 : 1.25), event.clientX, event.clientY)
    drawing = false
  }
}

function onPointerMove(event: PointerEvent): void {
  if (!drawing) {
    updateMoveHover(event)
    return
  }
  if (!editor.value || !activeLayer.value) return
  const point = getPoint(event)
  if (activeTool.value === 'select') {
    editor.value.selection = normalizedSelection(pointerStart.x, pointerStart.y, point.x, point.y)
  } else if (activeTool.value === 'brush' || activeTool.value === 'eraser') {
    paintSegment(previousPoint, point)
    previousPoint = point
  } else if (activeTool.value === 'move' && transformMode.value === 'resize') {
    resizeActiveLayer(point)
  } else if (activeTool.value === 'move' && !activeLayer.value.locked) {
    activeLayer.value.x = Math.round(layerStart.x + point.x - pointerStart.x)
    activeLayer.value.y = Math.round(layerStart.y + point.y - pointerStart.y)
  }
  render()
}

function onPointerUp(event: PointerEvent): void {
  if (!drawing) return
  drawing = false
  displayCanvas.value?.releasePointerCapture(event.pointerId)
  if (activeTool.value === 'select') {
    if (editor.value?.selection && (editor.value.selection.width < 2 || editor.value.selection.height < 2))
      editor.value.selection = null
    commit('Ubah seleksi', false)
  } else if (activeTool.value === 'brush' || activeTool.value === 'eraser') {
    commit(activeLayer.value?.target === 'mask' ? 'Edit mask' : activeTool.value === 'eraser' ? 'Hapus piksel' : 'Brush stroke')
  } else if (activeTool.value === 'move') {
    if (transformMode.value === 'resize' && activeLayer.value && resizeStart
      && (activeLayer.value.canvas.width !== resizeStart.width || activeLayer.value.canvas.height !== resizeStart.height))
      commit('Resize layer')
    else if (activeLayer.value && (activeLayer.value.x !== layerStart.x || activeLayer.value.y !== layerStart.y))
      commit('Pindahkan layer', false)
  }
  transformMode.value = null
  activeResizeHandle = null
  resizeStart = null
  resizeSource = null
  resizeMaskSource = null
  updateMoveHover(event)
}

function clearSelection(): void {
  if (!editor.value?.selection) return
  editor.value.selection = null
  commit('Hapus seleksi', false)
}

function applyLayerChange(label: string): void {
  render()
  commit(label, false)
}

async function saveProject(): Promise<void> {
  if (!editor.value) return
  const project = serializeProject(editor.value)
  downloadBlob(new Blob([JSON.stringify(project)], { type: 'application/json' }), `${sanitizeProjectName(editor.value.name)}${PROJECT_EXTENSION}`)
  dirty.value = false
  autosaveState.value = 'idle'
  try {
    await clearRecovery()
    recovery.value = null
  } catch {
    // Download remains valid even if browser storage cannot be cleared.
  }
  notify('Project berhasil diunduh.')
}

async function exportImage(): Promise<void> {
  if (!editor.value) return
  busy.value = true
  error.value = ''
  try {
    const composite = createCanvas(editor.value.width, editor.value.height)
    renderDocument(editor.value, composite)
    let result = composite
    if (exportFormat.value === 'jpeg') {
      result = createCanvas(editor.value.width, editor.value.height)
      const context = result.getContext('2d')
      if (context) {
        context.fillStyle = exportBackground.value
        context.fillRect(0, 0, result.width, result.height)
        context.drawImage(composite, 0, 0)
      }
    }
    const mime = `image/${exportFormat.value}`
    const blob = await canvasToBlob(result, mime, exportQuality.value / 100)
    downloadBlob(blob, exportFilename(editor.value.name, exportFormat.value))
    exportOpen.value = false
    notify('Gambar berhasil diekspor.')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Gambar gagal diekspor.'
  } finally {
    busy.value = false
  }
}

function onKeydown(event: KeyboardEvent): void {
  const target = event.target as HTMLElement | null
  const typing = target?.matches('input, textarea, select, [contenteditable="true"]')
  const modifier = event.ctrlKey || event.metaKey
  const key = event.key.toLowerCase()
  if (!typing && !modifier && event.code === 'Space') {
    event.preventDefault()
    spacePressed.value = true
    return
  }
  if (modifier && key === 's') {
    event.preventDefault()
    void saveProject()
  } else if (modifier && event.shiftKey && key === 'e') {
    event.preventDefault()
    if (editor.value) exportOpen.value = true
  } else if (modifier && key === 'z') {
    event.preventDefault()
    if (event.shiftKey) redo()
    else undo()
  } else if (modifier && key === 'd' && editor.value?.selection) {
    event.preventDefault()
    clearSelection()
  } else if (!typing && !modifier) {
    const tool = tools.find((item) => item.shortcut.toLowerCase() === key)
    if (tool) setActiveTool(tool.id)
    if (key === '[') brushSize.value = clamp(brushSize.value - 2, 1, 300)
    if (key === ']') brushSize.value = clamp(brushSize.value + 2, 1, 300)
  }
}

function onKeyup(event: KeyboardEvent): void {
  if (event.code === 'Space') spacePressed.value = false
}

function onBeforeUnload(event: BeforeUnloadEvent): void {
  if (!dirty.value) return
  event.preventDefault()
}

onMounted(async () => {
  document.addEventListener('keydown', onKeydown)
  document.addEventListener('keyup', onKeyup)
  document.addEventListener('paste', onPaste)
  window.addEventListener('beforeunload', onBeforeUnload)
  try {
    recovery.value = await loadRecovery()
  } catch {
    recovery.value = null
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  document.removeEventListener('keyup', onKeyup)
  document.removeEventListener('paste', onPaste)
  window.removeEventListener('beforeunload', onBeforeUnload)
  clearTimeout(autosaveTimer)
  cancelAnimationFrame(frame)
})
</script>

<template>
  <section
    class="photo-editor"
    @dragover.prevent
    @drop.prevent="onDrop"
  >
    <input
      ref="fileInput"
      class="sr-only"
      type="file"
      accept="image/png,image/jpeg,image/webp,.qpe,application/json"
      @change="onFileChange"
    />

    <header class="editor-header">
      <div class="document-identity">
        <PhImageSquare
          :size="22"
          weight="duotone"
          aria-hidden="true"
        />
        <div>
          <h1>Photo Editor</h1>
          <input
            v-if="editor"
            v-model="editor.name"
            class="project-name"
            aria-label="Nama project"
            maxlength="80"
            @change="commit('Ubah nama project', false)"
          />
          <p v-else>Editor gambar lokal dengan layer dan mask.</p>
        </div>
      </div>
      <div class="header-actions">
        <UiButton
          variant="ghost"
          size="sm"
          :disabled="!editor || busy"
          label="Undo"
          @click="undo"
        >
          <PhArrowCounterClockwise :size="18" />
        </UiButton>
        <UiButton
          variant="ghost"
          size="sm"
          :disabled="!editor || busy"
          label="Redo"
          @click="redo"
        >
          <PhArrowClockwise :size="18" />
        </UiButton>
        <span class="header-divider" />
        <UiButton
          variant="secondary"
          size="sm"
          :disabled="busy"
          @click="selectFile('open')"
        >
          <PhFolderOpen :size="17" />
          Buka
        </UiButton>
        <UiButton
          variant="secondary"
          size="sm"
          :disabled="!editor || busy"
          @click="saveProject"
        >
          <PhFloppyDisk :size="17" />
          Save project
        </UiButton>
        <UiButton
          size="sm"
          :disabled="!editor || busy"
          @click="exportOpen = true"
        >
          <PhDownloadSimple :size="17" />
          Export
        </UiButton>
      </div>
    </header>

    <p
      v-if="error"
      class="editor-error"
      role="alert"
    >
      {{ error }}
      <button @click="error = ''">Tutup</button>
    </p>

    <div
      v-if="!editor"
      class="start-surface"
      :aria-busy="busy || undefined"
    >
      <div class="start-copy">
        <span class="start-icon"><PhImageSquare :size="42" weight="duotone" /></span>
        <h2>Edit gambar tanpa mengunggahnya.</h2>
        <p>PNG, JPEG, dan WebP diproses di browser. Tarik file ke sini, atau paste screenshot dengan Ctrl+V.</p>
        <div class="start-actions">
          <UiButton
            :loading="busy"
            @click="selectFile('open')"
          >
            <PhFolderOpen :size="18" />
            Buka gambar
          </UiButton>
          <UiButton
            variant="secondary"
            :disabled="busy"
            @click="newOpen = true"
          >
            <PhPlus :size="18" />
            Buat dokumen
          </UiButton>
        </div>
        <button
          v-if="recovery"
          class="recovery-action"
          @click="restoreRecovery"
        >
          <PhClockCounterClockwise :size="18" />
          <span>
            <strong>Pulihkan {{ recovery.name }}</strong>
            <small>{{ recovery.width }} × {{ recovery.height }} px, {{ new Date(recovery.savedAt).toLocaleString('id-ID') }}</small>
          </span>
        </button>
      </div>
      <div class="privacy-note">
        <PhLock :size="18" />
        <span><strong>Tetap di perangkatmu.</strong> Editor tidak mengirim gambar ke server.</span>
      </div>
    </div>

    <div
      v-else
      class="editor-workspace"
    >
      <aside
        class="tool-rail"
        aria-label="Tools editor"
      >
        <button
          v-for="tool in tools"
          :key="tool.id"
          :class="['tool-button', { active: activeTool === tool.id }]"
          :aria-pressed="activeTool === tool.id"
          :aria-label="`${tool.label}, shortcut ${tool.shortcut}`"
          :title="`${tool.label} (${tool.shortcut})`"
          @click="setActiveTool(tool.id)"
        >
          <component
            :is="tool.icon"
            :size="20"
            :weight="activeTool === tool.id ? 'fill' : 'regular'"
          />
          <kbd>{{ tool.shortcut }}</kbd>
        </button>
      </aside>

      <div class="canvas-column">
        <div class="context-bar">
          <template v-if="activeTool === 'brush' || activeTool === 'eraser'">
            <label>
              Size
              <input
                v-model.number="brushSize"
                type="range"
                min="1"
                max="300"
              />
              <output>{{ brushSize }} px</output>
            </label>
            <label>
              Opacity
              <input
                v-model.number="brushOpacity"
                type="range"
                min="1"
                max="100"
              />
              <output>{{ brushOpacity }}%</output>
            </label>
            <template v-if="activeLayer?.target === 'mask'">
              <button
                :class="{ active: maskPaint === 'hide' }"
                @click="maskPaint = 'hide'"
              >
                Sembunyikan
              </button>
              <button
                :class="{ active: maskPaint === 'reveal' }"
                @click="maskPaint = 'reveal'"
              >
                Tampilkan
              </button>
              <span class="context-hint">Putih menampilkan, hitam menyembunyikan.</span>
            </template>
            <label
              v-else-if="activeTool === 'brush'"
              class="color-control"
            >
              Warna
              <input
                v-model="foreground"
                type="color"
              />
              <code>{{ foreground }}</code>
            </label>
          </template>
          <template v-else-if="activeTool === 'select'">
            <span class="context-hint">Tarik pada canvas untuk membuat seleksi kotak.</span>
            <button
              :disabled="!editor.selection"
              @click="addMask(true)"
            >
              Mask dari seleksi
            </button>
            <button
              :disabled="!editor.selection"
              @click="cropToSelection"
            >
              <PhCrop :size="16" />
              Crop
            </button>
            <button
              :disabled="!editor.selection"
              @click="clearSelection"
            >
              Hapus seleksi
            </button>
          </template>
          <template v-else-if="activeTool === 'move'">
            <span class="context-hint">Klik gambar untuk memilih. Tarik sudut untuk resize.</span>
            <label>
              X
              <input
                v-if="activeLayer"
                v-model.number="activeLayer.x"
                class="compact-input"
                type="number"
                @input="render"
                @change="commit('Posisi layer', false)"
              />
            </label>
            <label>
              Y
              <input
                v-if="activeLayer"
                v-model.number="activeLayer.y"
                class="compact-input"
                type="number"
                @input="render"
                @change="commit('Posisi layer', false)"
              />
            </label>
          </template>
          <template v-else-if="activeTool === 'hand'">
            <span class="context-hint">Tarik area kerja untuk pan. Tahan Space untuk pan dari tool apa pun.</span>
          </template>
          <template v-else>
            <span class="context-hint">{{ tools.find((tool) => tool.id === activeTool)?.label }}</span>
          </template>
          <span class="context-spacer" />
          <div
            class="context-zoom"
            aria-label="Kontrol zoom canvas"
          >
            <button @click="fitCanvas">Fit</button>
            <button @click="setZoom(100)">100%</button>
            <label title="Zoom canvas · Ctrl + scroll">
              <PhMagnifyingGlassPlus :size="16" />
              <span class="sr-only">Zoom canvas</span>
              <input
                :value="zoom"
                type="range"
                min="5"
                max="3200"
                @input="setZoom(Number(($event.target as HTMLInputElement).value))"
              />
            </label>
            <output>{{ zoom }}%</output>
          </div>
          <button @click="rotateDocument">
            <PhArrowClockwise :size="16" />
            Putar 90°
          </button>
        </div>

        <div
          ref="viewport"
          :class="[
            'canvas-viewport',
            `cursor-${activeTool}`,
            { 'is-space-pan': spacePressed, 'is-panning': panning },
          ]"
          @wheel="onWheel"
          @pointerdown.capture="onViewportPointerDown"
          @pointermove="onViewportPointerMove"
          @pointerup="onViewportPointerUp"
          @pointercancel="onViewportPointerUp"
        >
          <div
            class="canvas-stage"
            :style="canvasStageStyle"
          >
            <canvas
              ref="displayCanvas"
              :style="canvasStyle"
              tabindex="0"
              role="img"
              :aria-label="`Canvas ${editor.width} kali ${editor.height} pixel. Tool aktif ${activeTool}.`"
              @pointerdown="onPointerDown"
              @pointermove="onPointerMove"
              @pointerup="onPointerUp"
              @pointercancel="onPointerUp"
              @pointerleave="clearMoveHover"
            />
          </div>
        </div>
      </div>

      <aside class="inspector">
        <div
          class="inspector-tabs"
          role="tablist"
          aria-label="Panel editor"
        >
          <button
            :aria-selected="inspectorTab === 'layers'"
            role="tab"
            @click="inspectorTab = 'layers'"
          >
            <PhStack :size="16" /> Layers
          </button>
          <button
            :aria-selected="inspectorTab === 'properties'"
            role="tab"
            @click="inspectorTab = 'properties'"
          >
            <PhSliders :size="16" /> Properti
          </button>
          <button
            :aria-selected="inspectorTab === 'history'"
            role="tab"
            @click="inspectorTab = 'history'"
          >
            <PhClockCounterClockwise :size="16" /> History
          </button>
        </div>

        <div
          v-if="inspectorTab === 'layers'"
          class="inspector-body layers-panel"
          role="tabpanel"
        >
          <div class="panel-actions">
            <button
              title="Tambah layer"
              aria-label="Tambah layer"
              @click="addLayer"
            ><PhPlus :size="17" /></button>
            <button
              title="Tambah gambar sebagai layer"
              aria-label="Tambah gambar sebagai layer"
              @click="selectFile('layer')"
            ><PhImageSquare :size="17" /></button>
            <button
              title="Duplikat layer"
              aria-label="Duplikat layer"
              @click="duplicateLayer"
            ><PhCopy :size="17" /></button>
            <button
              title="Naikkan layer"
              aria-label="Naikkan layer"
              @click="moveLayer(1)"
            ><PhArrowUp :size="17" /></button>
            <button
              title="Turunkan layer"
              aria-label="Turunkan layer"
              @click="moveLayer(-1)"
            ><PhArrowDown :size="17" /></button>
            <span />
            <button
              class="danger-action"
              title="Hapus layer"
              aria-label="Hapus layer"
              :disabled="editor.layers.length === 1"
              @click="requestDeleteLayer"
            ><PhTrash :size="17" /></button>
          </div>

          <div class="layer-list">
            <article
              v-for="layer in displayLayers"
              :key="layer.id"
              :class="['layer-row', { active: layer.id === editor.activeLayerId }]"
              @click="selectLayer(layer)"
            >
              <button
                class="layer-toggle"
                :aria-label="layer.visible ? `Sembunyikan ${layer.name}` : `Tampilkan ${layer.name}`"
                @click.stop="toggleLayerVisibility(layer)"
              >
                <PhEye v-if="layer.visible" :size="17" />
                <PhEyeSlash v-else :size="17" />
              </button>
              <button
                :class="['layer-thumb', { target: layer.id === editor.activeLayerId && layer.target === 'content' }]"
                :aria-label="`Edit isi ${layer.name}`"
                @click.stop="selectLayer(layer, 'content')"
              >
                <img
                  v-if="layer.preview"
                  :src="layer.preview"
                  alt=""
                />
              </button>
              <button
                v-if="layer.mask"
                :class="['mask-thumb', { target: layer.id === editor.activeLayerId && layer.target === 'mask' }]"
                :aria-label="`Edit mask ${layer.name}`"
                title="Mask"
                @click.stop="selectLayer(layer, 'mask')"
              ><PhCircleHalf :size="20" weight="fill" /></button>
              <button
                class="layer-name"
                @click.stop="selectLayer(layer)"
              >
                <strong>{{ layer.name }}</strong>
                <small>{{ layer.target === 'mask' && layer.id === editor.activeLayerId ? 'Mask aktif' : `${layer.opacity}%` }}</small>
              </button>
              <button
                class="layer-toggle"
                :aria-label="layer.locked ? `Buka kunci ${layer.name}` : `Kunci ${layer.name}`"
                @click.stop="toggleLayerLock(layer)"
              >
                <PhLock v-if="layer.locked" :size="16" />
                <PhLockOpen v-else :size="16" />
              </button>
            </article>
          </div>

          <div class="mask-actions">
            <strong>Mask layer</strong>
            <template v-if="activeLayer?.mask">
              <label class="switch-row">
                <input
                  v-model="activeLayer.maskEnabled"
                  type="checkbox"
                  @change="applyLayerChange('Toggle mask')"
                />
                Aktifkan mask
              </label>
              <div class="button-row">
                <button @click="invertMask">Invert</button>
                <button
                  class="danger-action"
                  @click="requestRemoveMask"
                >Hapus mask</button>
              </div>
            </template>
            <div
              v-else
              class="button-row"
            >
              <button @click="addMask(false)">Reveal all</button>
              <button
                :disabled="!editor.selection"
                @click="addMask(true)"
              >Dari seleksi</button>
            </div>
          </div>
        </div>

        <div
          v-else-if="inspectorTab === 'properties' && activeLayer"
          class="inspector-body properties-panel"
          role="tabpanel"
        >
          <label class="property-field">
            <span>Nama layer</span>
            <input
              v-model="activeLayer.name"
              type="text"
              maxlength="80"
              @change="commit('Ubah nama layer', false)"
            />
          </label>
          <label class="property-field">
            <span>Blend mode</span>
            <select
              v-model="activeLayer.blendMode"
              @change="applyLayerChange('Blend mode')"
            >
              <option
                v-for="option in blendOptions"
                :key="option.value"
                :value="option.value"
              >{{ option.label }}</option>
            </select>
          </label>
          <label class="property-slider">
            <span>Opacity <output>{{ activeLayer.opacity }}%</output></span>
            <input
              v-model.number="activeLayer.opacity"
              type="range"
              min="0"
              max="100"
              @input="render"
              @change="commit('Opacity layer', false)"
            />
          </label>
          <div class="property-section">
            <h3>Posisi dan ukuran</h3>
            <p>Atur layer aktif terhadap canvas.</p>
          </div>
          <div class="alignment-grid" aria-label="Alignment layer aktif">
            <button
              :disabled="activeLayer.locked"
              @click="alignActiveLayer('left')"
            >Kiri</button>
            <button
              :disabled="activeLayer.locked"
              @click="alignActiveLayer('center')"
            >Tengah X</button>
            <button
              :disabled="activeLayer.locked"
              @click="alignActiveLayer('right')"
            >Kanan</button>
            <button
              :disabled="activeLayer.locked"
              @click="alignActiveLayer(undefined, 'top')"
            >Atas</button>
            <button
              :disabled="activeLayer.locked"
              @click="alignActiveLayer(undefined, 'middle')"
            >Tengah Y</button>
            <button
              :disabled="activeLayer.locked"
              @click="alignActiveLayer(undefined, 'bottom')"
            >Bawah</button>
          </div>
          <div class="button-row property-actions">
            <button
              :disabled="activeLayer.locked"
              title="Seluruh gambar terlihat dan dipusatkan"
              @click="fitActiveLayer('contain')"
            >Fit layer</button>
            <button
              :disabled="activeLayer.locked"
              title="Penuhi canvas, bagian berlebih akan berada di luar canvas"
              @click="fitActiveLayer('cover')"
            >Fill canvas</button>
            <button @click="addPlainBackground">Background putih</button>
          </div>
          <div class="property-section">
            <h3>Auto Remove BG</h3>
            <p>Menghapus warna polos yang tersambung ke tepi gambar. Tidak mengunggah foto.</p>
          </div>
          <label class="property-slider">
            <span>Tolerance <output>{{ removeBackgroundTolerance }}</output></span>
            <input
              v-model.number="removeBackgroundTolerance"
              type="range"
              min="0"
              max="100"
            />
          </label>
          <button
            class="auto-remove-button"
            :disabled="activeLayer.locked || busy"
            @click="autoRemoveBackground"
          >
            {{ busy ? 'Memproses...' : 'Hapus background otomatis' }}
          </button>
          <div class="property-section">
            <h3>Adjustment</h3>
            <p>Non-destruktif dan dapat diubah kembali.</p>
          </div>
          <label class="property-slider">
            <span>Brightness <output>{{ activeLayer.brightness }}%</output></span>
            <input
              v-model.number="activeLayer.brightness"
              type="range"
              min="0"
              max="200"
              @input="render"
              @change="commit('Brightness', false)"
            />
          </label>
          <label class="property-slider">
            <span>Contrast <output>{{ activeLayer.contrast }}%</output></span>
            <input
              v-model.number="activeLayer.contrast"
              type="range"
              min="0"
              max="200"
              @input="render"
              @change="commit('Contrast', false)"
            />
          </label>
          <label class="property-slider">
            <span>Saturation <output>{{ activeLayer.saturation }}%</output></span>
            <input
              v-model.number="activeLayer.saturation"
              type="range"
              min="0"
              max="200"
              @input="render"
              @change="commit('Saturation', false)"
            />
          </label>
          <label class="property-slider">
            <span>Blur <output>{{ activeLayer.blur }} px</output></span>
            <input
              v-model.number="activeLayer.blur"
              type="range"
              min="0"
              max="30"
              step="0.5"
              @input="render"
              @change="commit('Blur', false)"
            />
          </label>
          <button
            class="reset-adjustments"
            @click="activeLayer.brightness = 100; activeLayer.contrast = 100; activeLayer.saturation = 100; activeLayer.blur = 0; applyLayerChange('Reset adjustment')"
          >Reset adjustment</button>
        </div>

        <div
          v-else
          class="inspector-body history-panel"
          role="tabpanel"
        >
          <button
            v-for="(entry, index) in history"
            :key="`${index}-${entry.label}`"
            :class="{ active: index === historyIndex }"
            :disabled="busy"
            @click="restoreHistory(index)"
          >
            <PhCheck
              v-if="index === historyIndex"
              :size="15"
            />
            <span v-else class="history-index">{{ index + 1 }}</span>
            {{ entry.label }}
          </button>
        </div>
      </aside>

      <footer class="editor-status">
        <span>{{ editor.width }} × {{ editor.height }} px</span>
        <span>{{ editor.layers.length }} layer</span>
        <span :class="{ warning: autosaveState === 'error' }">{{ statusText }}</span>
      </footer>
    </div>

    <UiModal
      v-model="newOpen"
      title="Buat dokumen baru"
      description="Pilih ukuran canvas. Kamu dapat crop atau memutar dokumen setelah dibuat."
      size="sm"
    >
      <div class="new-grid">
        <label class="property-field">
          <span>Lebar (px)</span>
          <input
            v-model="newWidth"
            type="number"
            min="1"
            max="8192"
          />
        </label>
        <label class="property-field">
          <span>Tinggi (px)</span>
          <input
            v-model="newHeight"
            type="number"
            min="1"
            max="8192"
          />
        </label>
        <label class="switch-row new-background">
          <input
            v-model="transparentBackground"
            type="checkbox"
          />
          Background transparan
        </label>
        <label
          v-if="!transparentBackground"
          class="property-field"
        >
          <span>Warna background</span>
          <input
            v-model="newBackground"
            type="color"
          />
        </label>
        <p
          v-if="newSizeError"
          class="field-error new-error"
          role="alert"
        >{{ newSizeError }}</p>
      </div>
      <template #footer>
        <UiButton
          variant="secondary"
          @click="newOpen = false"
        >Batal</UiButton>
        <UiButton
          :disabled="Boolean(newSizeError)"
          @click="createNewDocument"
        >Buat dokumen</UiButton>
      </template>
    </UiModal>

    <UiModal
      v-model="exportOpen"
      title="Export gambar"
      description="Export membuat gambar flattened dan tidak mengubah project aktif."
      size="sm"
    >
      <div class="export-fields">
        <label class="property-field">
          <span>Format</span>
          <select v-model="exportFormat">
            <option value="png">PNG</option>
            <option value="jpeg">JPEG</option>
            <option value="webp">WebP</option>
          </select>
        </label>
        <label
          v-if="exportFormat !== 'png'"
          class="property-slider"
        >
          <span>Quality <output>{{ exportQuality }}%</output></span>
          <input
            v-model.number="exportQuality"
            type="range"
            min="1"
            max="100"
          />
        </label>
        <label
          v-if="exportFormat === 'jpeg'"
          class="property-field"
        >
          <span>Warna area transparan</span>
          <input
            v-model="exportBackground"
            type="color"
          />
        </label>
        <p class="export-summary">
          {{ editor?.width }} × {{ editor?.height }} px. Metadata lokasi tidak disertakan.
        </p>
      </div>
      <template #footer>
        <UiButton
          variant="secondary"
          :disabled="busy"
          @click="exportOpen = false"
        >Batal</UiButton>
        <UiButton
          :loading="busy"
          @click="exportImage"
        >Export {{ exportFormat.toUpperCase() }}</UiButton>
      </template>
    </UiModal>

    <UiConfirmDialog
      v-model="confirmOpen"
      :title="confirmKind === 'replace' ? 'Ganti dokumen aktif?' : confirmKind === 'layer' ? 'Hapus layer?' : 'Hapus mask?'"
      :description="confirmKind === 'replace' ? 'Perubahan yang belum diunduh akan diganti. Recovery terakhir tetap tersedia.' : confirmKind === 'layer' ? `Layer ${activeLayer?.name ?? ''} akan dihapus dari project.` : `Mask pada ${activeLayer?.name ?? ''} akan dihapus dan seluruh isi layer kembali terlihat.`"
      :confirm-label="confirmKind === 'replace' ? 'Ganti dokumen' : confirmKind === 'layer' ? 'Hapus layer' : 'Hapus mask'"
      @confirm="confirmDestructive"
    />
  </section>
</template>

<style scoped>
.photo-editor {
  min-height: calc(100dvh - 104px);
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  color: var(--color-text);
}
.editor-header {
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 0 4px 14px;
}
.document-identity,
.header-actions,
.context-bar,
.panel-actions,
.button-row,
.switch-row,
.editor-status {
  display: flex;
  align-items: center;
}
.document-identity {
  gap: 11px;
  min-width: 0;
}
.document-identity > svg {
  color: var(--color-primary);
}
.document-identity h1 {
  font-size: 18px;
  letter-spacing: -0.35px;
}
.document-identity p,
.project-name {
  color: var(--color-text-muted);
  font-size: 12px;
}
.project-name {
  display: block;
  width: min(280px, 32vw);
  border: 0;
  border-bottom: 1px solid transparent;
  padding: 1px 0;
  background: transparent;
}
.project-name:hover,
.project-name:focus {
  border-color: var(--color-border-strong);
  color: var(--color-text);
}
.header-actions {
  gap: 7px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.header-divider {
  width: 1px;
  height: 24px;
  background: var(--color-border);
  margin: 0 3px;
}
.editor-error {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
  padding: 10px 13px;
  border-left: 3px solid var(--color-danger);
  background: color-mix(in srgb, var(--color-danger) 8%, var(--color-surface));
  color: var(--color-danger);
  font-size: 13px;
}
.editor-error button {
  border: 0;
  background: transparent;
  color: inherit;
  text-decoration: underline;
}
.start-surface {
  min-height: 620px;
  display: grid;
  place-items: center;
  position: relative;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-panel);
  background:
    linear-gradient(var(--color-surface-subtle) 1px, transparent 1px),
    linear-gradient(90deg, var(--color-surface-subtle) 1px, transparent 1px),
    var(--color-surface);
  background-size: 32px 32px;
}
.start-copy {
  width: min(520px, calc(100% - 40px));
  text-align: center;
  padding: 36px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-panel);
  box-shadow: var(--shadow-floating);
}
.start-icon {
  width: 72px;
  height: 72px;
  display: grid;
  place-items: center;
  margin: 0 auto 20px;
  border-radius: 14px;
  background: var(--color-brand-panel);
  color: var(--color-primary);
}
.start-copy h2 {
  font-size: 24px;
}
.start-copy > p {
  max-width: 45ch;
  margin: 10px auto 22px;
  color: var(--color-text-muted);
  font-size: 14px;
}
.start-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
}
.recovery-action {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 24px;
  padding: 13px;
  text-align: left;
  color: var(--color-text);
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
}
.recovery-action svg {
  color: var(--color-primary);
}
.recovery-action strong,
.recovery-action small {
  display: block;
}
.recovery-action strong {
  font-size: 13px;
}
.recovery-action small {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 11px;
}
.privacy-note {
  position: absolute;
  bottom: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 12px;
}
.privacy-note strong {
  color: var(--color-text);
}
.editor-workspace {
  min-height: 600px;
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) 292px;
  grid-template-rows: minmax(0, 1fr) 35px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-panel);
  background: var(--color-surface);
}
.tool-rail {
  grid-row: 1;
  padding: 8px 6px;
  border-right: 1px solid var(--color-border);
  background: var(--color-surface);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.tool-button {
  min-height: 46px;
  display: grid;
  place-items: center;
  position: relative;
  border: 1px solid transparent;
  border-radius: 7px;
  color: var(--color-text-muted);
  background: transparent;
}
.tool-button:hover {
  color: var(--color-text);
  background: var(--color-surface-subtle);
}
.tool-button.active {
  color: var(--color-primary);
  border-color: color-mix(in srgb, var(--color-primary) 30%, var(--color-border));
  background: color-mix(in srgb, var(--color-primary) 10%, var(--color-surface));
}
.tool-button kbd {
  position: absolute;
  right: 3px;
  bottom: 1px;
  padding: 0;
  border: 0;
  color: var(--color-text-muted);
  font-size: 8px;
}
.canvas-column {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
}
.context-bar {
  min-height: 48px;
  gap: 14px;
  padding: 6px 12px;
  overflow-x: auto;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  white-space: nowrap;
  font-size: 12px;
}
.context-bar label {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--color-text-muted);
}
.context-bar input[type='range'] {
  width: 88px;
}
.context-bar output,
.context-bar code {
  color: var(--color-text);
  min-width: 40px;
}
.context-bar button,
.panel-actions button,
.button-row button,
.reset-adjustments {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 5px 9px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: 12px;
}
.context-bar button:hover:not(:disabled),
.context-bar button.active,
.panel-actions button:hover:not(:disabled),
.button-row button:hover:not(:disabled),
.reset-adjustments:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.context-bar button:disabled,
.panel-actions button:disabled,
.button-row button:disabled {
  opacity: 0.45;
}
.context-hint {
  color: var(--color-text-muted);
}
.context-zoom {
  display: flex;
  align-items: center;
  gap: 6px;
}
.context-zoom label {
  gap: 4px;
}
.context-spacer,
.panel-actions > span {
  flex: 1;
}
.color-control input {
  width: 27px;
  height: 27px;
  padding: 2px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background: var(--color-surface);
}
.compact-input {
  width: 68px;
  min-height: 30px;
  padding: 4px 7px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background: var(--color-surface);
  color: var(--color-text);
}
.canvas-viewport {
  min-width: 0;
  min-height: 0;
  height: calc(100dvh - 240px);
  overflow: auto;
  background-color: #c7c7cc;
  background-image: linear-gradient(45deg, #b8b8bd 25%, transparent 25%),
    linear-gradient(-45deg, #b8b8bd 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #b8b8bd 75%),
    linear-gradient(-45deg, transparent 75%, #b8b8bd 75%);
  background-size: 20px 20px;
  background-position: 0 0, 0 10px, 10px -10px, -10px 0;
  overscroll-behavior: contain;
}
.canvas-stage {
  display: grid;
  place-items: center;
  min-width: 100%;
  min-height: 100%;
}
[data-theme='dark'] .canvas-viewport {
  background-color: #353440;
  background-image: linear-gradient(45deg, #2c2b36 25%, transparent 25%),
    linear-gradient(-45deg, #2c2b36 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #2c2b36 75%),
    linear-gradient(-45deg, transparent 75%, #2c2b36 75%);
}
.canvas-viewport canvas {
  display: block;
  flex: none;
  max-width: none;
  touch-action: none;
  background-color: transparent;
  background-image: linear-gradient(45deg, #ececef 25%, transparent 25%),
    linear-gradient(-45deg, #ececef 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #ececef 75%),
    linear-gradient(-45deg, transparent 75%, #ececef 75%);
  background-size: 16px 16px;
  background-position: 0 0, 0 8px, 8px -8px, -8px 0;
  box-shadow: 0 8px 28px rgb(27 25 39 / 22%);
}
.cursor-move canvas {
  cursor: move;
}
.cursor-select canvas {
  cursor: crosshair;
}
.cursor-brush canvas,
.cursor-eraser canvas {
  cursor: crosshair;
}
.cursor-hand,
.cursor-hand canvas,
.is-space-pan,
.is-space-pan canvas {
  cursor: grab;
}
.is-panning,
.is-panning canvas {
  cursor: grabbing;
}
.cursor-zoom canvas {
  cursor: zoom-in;
}
.cursor-eyedropper canvas {
  cursor: crosshair;
}
.inspector {
  min-width: 0;
  grid-column: 3;
  grid-row: 1;
  border-left: 1px solid var(--color-border);
  background: var(--color-surface);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
}
.inspector-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-bottom: 1px solid var(--color-border);
}
.inspector-tabs button {
  min-width: 0;
  min-height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 7px 4px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--color-text-muted);
  font-size: 11px;
}
.inspector-tabs button[aria-selected='true'] {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 500;
}
.inspector-body {
  min-height: 0;
  overflow-y: auto;
}
.panel-actions {
  gap: 4px;
  padding: 8px;
  border-bottom: 1px solid var(--color-border);
}
.panel-actions button {
  width: 32px;
  padding: 0;
}
.danger-action {
  color: var(--color-danger) !important;
}
.layer-list {
  padding: 5px 0;
}
.layer-row {
  min-height: 58px;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 8px;
  border-left: 3px solid transparent;
}
.layer-row:hover {
  background: var(--color-surface-subtle);
}
.layer-row.active {
  border-left-color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 8%, var(--color-surface));
}
.layer-toggle,
.layer-name,
.layer-thumb,
.mask-thumb {
  border: 0;
  background: transparent;
  color: var(--color-text-muted);
}
.layer-toggle {
  width: 26px;
  height: 32px;
  display: grid;
  place-items: center;
  padding: 0;
}
.layer-thumb,
.mask-thumb {
  width: 43px;
  height: 36px;
  display: grid;
  place-items: center;
  overflow: hidden;
  padding: 2px;
  border: 1px solid var(--color-border-strong);
  border-radius: 5px;
  background: var(--color-surface-subtle);
}
.layer-thumb.target,
.mask-thumb.target {
  outline: 2px solid var(--color-primary);
  outline-offset: 1px;
}
.layer-thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.mask-thumb {
  width: 34px;
  color: var(--color-text);
}
.layer-name {
  min-width: 0;
  flex: 1;
  padding: 2px;
  text-align: left;
}
.layer-name strong,
.layer-name small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.layer-name strong {
  color: var(--color-text);
  font-size: 12px;
  font-weight: 500;
}
.layer-name small {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 10px;
}
.mask-actions {
  display: grid;
  gap: 10px;
  margin: 8px;
  padding: 12px;
  border-top: 1px solid var(--color-border);
}
.mask-actions > strong {
  font-size: 12px;
}
.switch-row {
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 12px;
}
.button-row {
  gap: 6px;
  flex-wrap: wrap;
}
.properties-panel {
  padding: 15px;
  display: grid;
  align-content: start;
  gap: 15px;
}
.property-field,
.property-slider {
  display: grid;
  gap: 6px;
  color: var(--color-text-muted);
  font-size: 12px;
}
.property-field input,
.property-field select {
  min-height: 38px;
  width: 100%;
  padding: 7px 9px;
  border: 1px solid var(--color-border-strong);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
}
.property-field input[type='color'] {
  padding: 3px;
}
.property-slider > span {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.property-slider output {
  font-family: var(--font-mono);
  color: var(--color-text);
}
.property-slider input {
  width: 100%;
}
.property-section {
  padding-top: 14px;
  border-top: 1px solid var(--color-border);
}
.property-section h3 {
  font-size: 13px;
}
.property-section p {
  margin-top: 3px;
  color: var(--color-text-muted);
  font-size: 11px;
}
.reset-adjustments {
  justify-self: start;
}
.alignment-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}
.alignment-grid button,
.auto-remove-button {
  min-height: 34px;
  padding: 6px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: 11px;
}
.alignment-grid button:hover:not(:disabled),
.auto-remove-button:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.alignment-grid button:disabled,
.auto-remove-button:disabled {
  opacity: 0.45;
}
.property-actions button {
  flex: 1 1 auto;
}
.auto-remove-button {
  min-height: 39px;
  color: var(--color-on-primary);
  background: var(--color-primary);
  border-color: var(--color-primary);
  font-size: 12px;
  font-weight: 500;
}
.auto-remove-button:hover:not(:disabled) {
  color: var(--color-on-primary);
  background: var(--color-primary-hover);
}
.history-panel {
  padding: 6px 0;
}
.history-panel button {
  width: 100%;
  min-height: 38px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 12px;
  border: 0;
  background: transparent;
  color: var(--color-text-muted);
  text-align: left;
  font-size: 12px;
}
.history-panel button:hover,
.history-panel button.active {
  background: var(--color-surface-subtle);
  color: var(--color-text);
}
.history-panel button.active {
  color: var(--color-primary);
}
.history-index {
  width: 15px;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 9px;
  text-align: center;
}
.editor-status {
  grid-column: 1 / -1;
  grid-row: 2;
  gap: 14px;
  min-width: 0;
  padding: 4px 10px;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 10px;
}
.editor-status .warning {
  color: var(--color-warning);
}
.new-grid,
.export-fields {
  display: grid;
  gap: 16px;
}
.new-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.new-background,
.new-error {
  grid-column: 1 / -1;
}
.export-summary {
  padding: 11px 13px;
  background: var(--color-surface-subtle);
  color: var(--color-text-muted);
  font-size: 12px;
}
button:active:not(:disabled) {
  transform: scale(0.98);
}
@media (max-width: 1180px) {
  .editor-workspace {
    grid-template-columns: 50px minmax(0, 1fr) 255px;
  }
  .header-actions :deep(.ui-button) {
    padding-inline: 10px;
  }
  .context-hint {
    display: none;
  }
}
@media (max-width: 900px) {
  .editor-header {
    align-items: flex-start;
    flex-direction: column;
  }
  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
  .editor-workspace {
    grid-template-columns: 50px minmax(0, 1fr);
    grid-template-rows: minmax(460px, 65dvh) auto 35px;
  }
  .inspector {
    grid-column: 1 / -1;
    grid-row: 2;
    min-height: 330px;
    border-top: 1px solid var(--color-border);
    border-left: 0;
  }
  .tool-rail,
  .canvas-column {
    grid-row: 1;
  }
  .canvas-viewport {
    height: calc(65dvh - 49px);
  }
  .editor-status {
    grid-row: 3;
  }
}
@media (max-width: 620px) {
  .photo-editor {
    min-height: calc(100dvh - 88px);
  }
  .header-actions {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .header-actions > :deep(button) {
    width: 100%;
  }
  .header-actions > :deep(button:nth-child(1)),
  .header-actions > :deep(button:nth-child(2)),
  .header-divider {
    display: none;
  }
  .start-surface {
    min-height: 540px;
  }
  .start-copy {
    padding: 28px 20px;
  }
  .start-actions {
    flex-direction: column;
  }
  .start-actions :deep(button) {
    width: 100%;
  }
  .privacy-note {
    width: calc(100% - 32px);
    align-items: flex-start;
  }
  .editor-workspace {
    border-radius: 8px;
  }
  .tool-rail {
    overflow-y: auto;
  }
  .context-bar {
    gap: 10px;
  }
  .context-bar label:nth-of-type(2) {
    display: none;
  }
  .editor-status > span:nth-child(2),
  .editor-status > span:nth-child(3) {
    display: none;
  }
  .new-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .new-background,
  .new-error {
    grid-column: 1;
  }
}
</style>
