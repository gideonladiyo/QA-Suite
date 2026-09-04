<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useUiStore } from '../../stores/ui'
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'
import CommandPalette from './CommandPalette.vue'
import UiModal from '../ui/UiModal.vue'
import UiToast from '../ui/UiToast.vue'
const ui = useUiStore()
const route = useRoute()
const menuOpen = ref(false)
const main = ref<HTMLElement>()
watch(
  () => route.fullPath,
  async () => {
    menuOpen.value = false
    ui.paletteOpen = false
    await nextTick()
    main.value?.focus({ preventScroll: true })
  },
)
function shortcut(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    if (document.querySelector('dialog[open]') && !ui.paletteOpen) return
    event.preventDefault()
    ui.paletteOpen = !ui.paletteOpen
  }
}
onMounted(() => document.addEventListener('keydown', shortcut))
onUnmounted(() => document.removeEventListener('keydown', shortcut))
</script>
<template>
  <a
    href="#main-content"
    class="skip-link"
  >
    Lewati ke konten
  </a>
  <div :class="['app-shell', { collapsed: ui.sidebarCollapsed }]">
    <div class="desktop-sidebar"><AppSidebar /></div>
    <div class="app-workspace">
      <AppTopbar @menu="menuOpen = true" />
      <main
        id="main-content"
        ref="main"
        tabindex="-1"
      >
        <div class="page-content"><RouterView /></div>
      </main>
    </div>
  </div>
  <UiModal
    v-model="menuOpen"
    title="Navigasi"
    size="sm"
  >
    <AppSidebar mobile />
  </UiModal>
  <CommandPalette />
  <UiToast />
</template>
<style scoped>
.app-shell {
  --sidebar-width: 244px;
  display: grid;
  grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
  min-height: 100dvh;
}
.app-shell.collapsed {
  --sidebar-width: 80px;
}
.desktop-sidebar {
  /* Anchor navigation to the viewport, independent of report/page length. */
  position: fixed;
  inset: 0 auto 0 0;
  width: var(--sidebar-width);
  height: 100dvh;
  z-index: var(--layer-header);
}
.app-workspace {
  grid-column: 2;
  min-width: 0;
}
main {
  outline: none;
}
.page-content {
  padding: 36px;
  max-width: 1480px;
  margin: 0 auto;
}
.skip-link {
  position: fixed;
  top: 8px;
  left: 8px;
  transform: translateY(-150%);
  padding: 12px 16px;
  background: var(--color-primary);
  color: var(--color-on-primary);
  z-index: var(--layer-notification);
  border-radius: 8px;
}
.skip-link:focus {
  transform: translateY(0);
}
@media (max-width: 1050px) {
  .page-content {
    padding: 28px 24px;
  }
}
@media (max-width: 767px) {
  .app-shell,
  .app-shell.collapsed {
    grid-template-columns: minmax(0, 1fr);
  }
  .desktop-sidebar {
    display: none;
  }
  .app-workspace {
    grid-column: 1;
  }
  .page-content {
    padding: 24px 16px;
  }
}
</style>
