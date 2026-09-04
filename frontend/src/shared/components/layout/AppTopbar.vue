<script setup lang="ts">
import { useRoute } from 'vue-router'
import { PhList, PhMagnifyingGlass, PhDatabase, PhCaretRight } from '@phosphor-icons/vue'
import { useUiStore } from '../../stores/ui'
import UiButton from '../ui/UiButton.vue'
const emit = defineEmits<{ menu: [] }>()
const ui = useUiStore()
const route = useRoute()
</script>
<template>
  <header class="app-topbar">
    <UiButton
      class="mobile-toggle"
      variant="ghost"
      icon-only
      label="Buka navigasi"
      @click="emit('menu')"
    >
      <PhList :size="22" />
    </UiButton>
    <div class="breadcrumb">
      <span>Workspace</span>
      <PhCaretRight
        :size="12"
        aria-hidden="true"
      />
      <strong>{{ route.meta.title ?? 'Halaman' }}</strong>
    </div>
    <div class="topbar-actions">
      <RouterLink
        to="/supabase-hub"
        class="connection-context"
      >
        <PhDatabase
          :size="16"
          aria-hidden="true"
        />
        <span>Belum terhubung</span>
      </RouterLink>
      <span class="topbar-divider" />
      <UiButton
        variant="ghost"
        label="Cari halaman atau alat"
        @click="ui.paletteOpen = true"
      >
        <PhMagnifyingGlass :size="18" />
        <span class="search-label">Cari</span>
        <kbd>Ctrl K</kbd>
      </UiButton>
    </div>
  </header>
</template>
<style scoped>
.app-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 72px;
  padding: 0 36px;
  background: var(--color-page);
  border-bottom: 1px solid var(--color-border);
}
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: var(--color-text-muted);
}
.breadcrumb strong {
  font-weight: 500;
  color: var(--color-text);
}
.topbar-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}
.connection-context {
  display: flex;
  gap: 7px;
  align-items: center;
  font-size: 12px;
  color: var(--color-text-muted);
}
.connection-context:hover {
  color: var(--color-primary);
}
.topbar-divider {
  height: 18px;
  width: 1px;
  background: var(--color-border);
}
.mobile-toggle {
  display: none;
}
@media (max-width: 1000px) {
  .app-topbar {
    padding: 0 24px;
  }
  .connection-context {
    display: none;
  }
  .topbar-divider {
    display: none;
  }
}
@media (max-width: 767px) {
  .app-topbar {
    padding: 0 12px;
    gap: 8px;
    min-height: 64px;
  }
  .mobile-toggle {
    display: inline-flex;
  }
  .breadcrumb {
    flex: 1;
  }
  .breadcrumb > span,
  .breadcrumb > svg,
  .search-label,
  kbd {
    display: none;
  }
  .topbar-actions {
    gap: 0;
  }
}
</style>
