<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { TreeNode } from '../json'
const props = defineProps<{ nodes: TreeNode[]; search: string }>()
const expanded = ref(new Set([0]))
const scroll = ref(0)
const viewport = ref<HTMLElement>()
const rowHeight = 32
const visible = computed(() => {
  const query = props.search.toLowerCase().trim()
  if (query) {
    const matches = new Set<number>()
    for (const node of props.nodes)
      if (`${node.label} ${node.value}`.toLowerCase().includes(query)) {
        let id = node.id
        while (id >= 0 && !matches.has(id)) {
          matches.add(id)
          id = props.nodes[id]!.parent
        }
      }
    return props.nodes.filter((node) => matches.has(node.id))
  }
  const included = new Set<number>()
  return props.nodes.filter((node) => {
    if (node.parent < 0 || (included.has(node.parent) && expanded.value.has(node.parent))) {
      included.add(node.id)
      return true
    }
    return false
  })
})
const start = computed(() => Math.max(0, Math.floor(scroll.value / rowHeight) - 4))
const windowed = computed(() => visible.value.slice(start.value, start.value + 22))
watch(
  () => props.nodes,
  () => {
    expanded.value = new Set([0])
  },
)
watch(
  [() => props.nodes, () => props.search, expanded],
  () => {
    scroll.value = 0
    if (viewport.value) viewport.value.scrollTop = 0
  },
  { deep: true },
)
function toggle(id: number): void {
  const next = new Set(expanded.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expanded.value = next
}
function parts(text: string): { text: string; match: boolean }[] {
  const query = props.search.trim().toLowerCase()
  if (text.length > 600) {
    const offset = query ? Math.max(0, text.toLowerCase().indexOf(query) - 80) : 0
    text = `${offset ? '…' : ''}${text.slice(offset, offset + 600)}…`
  }
  if (!query) return [{ text, match: false }]
  const result: { text: string; match: boolean }[] = []
  let offset = 0,
    index = text.toLowerCase().indexOf(query)
  while (index >= 0) {
    result.push(
      { text: text.slice(offset, index), match: false },
      { text: text.slice(index, index + query.length), match: true },
    )
    offset = index + query.length
    index = text.toLowerCase().indexOf(query, offset)
  }
  result.push({ text: text.slice(offset), match: false })
  return result
}
</script>
<template>
  <p class="text-muted">
    {{ visible.length.toLocaleString() }} node · klik panah untuk buka/tutup. Pencarian mencakup key
    dan nilai.
  </p>
  <div
    ref="viewport"
    class="json-tree"
    aria-label="Struktur JSON"
    tabindex="0"
    @scroll="scroll = ($event.target as HTMLElement).scrollTop"
  >
    <div :style="{ height: `${visible.length * rowHeight}px`, position: 'relative' }">
      <div
        v-for="(node, index) in windowed"
        :key="node.id"
        class="tree-row"
        :style="{
          top: `${(start + index) * rowHeight}px`,
          paddingLeft: `${Math.min(node.depth, 16) * 16 + 8}px`,
        }"
        :title="`${node.label}: ${node.value}`"
      >
        <button
          v-if="node.container"
          type="button"
          :aria-label="`${expanded.has(node.id) ? 'Tutup' : 'Buka'} ${node.label}`"
          :aria-expanded="!!search.trim() || expanded.has(node.id)"
          :disabled="!!search.trim()"
          @click="toggle(node.id)"
        >
          {{ search.trim() || expanded.has(node.id) ? '▾' : '▸' }}
        </button>
        <span
          v-else
          class="tree-spacer"
        />
        <span class="tree-label">
          <template
            v-for="(part, n) in parts(`${node.label}: ${node.value}`)"
            :key="n"
          >
            <mark v-if="part.match">{{ part.text }}</mark>
            <template v-else>{{ part.text }}</template>
          </template>
        </span>
      </div>
    </div>
    <p v-if="!visible.length">Tidak ada hasil pencarian.</p>
  </div>
</template>
<style scoped>
.json-tree {
  height: 400px;
  overflow: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  font-family: var(--font-mono);
  font-size: 13px;
}
.tree-row {
  position: absolute;
  left: 0;
  right: 0;
  height: 32px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.tree-row:hover {
  background: var(--color-surface-subtle);
}
.tree-row button,
.tree-spacer {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
}
.tree-row button {
  cursor: pointer;
  border: 1px solid var(--color-border);
  border-radius: 4px;
}
.tree-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
mark {
  background: var(--color-primary);
  color: var(--color-on-primary);
}
</style>
