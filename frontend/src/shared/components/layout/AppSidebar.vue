<script setup lang="ts">
import { useRoute } from 'vue-router'
import { PhArrowLeft, PhArrowRight, PhDesktop } from '@phosphor-icons/vue'
import { primaryNavigation, secondaryNavigation } from '../../navigation'
import { useUiStore } from '../../stores/ui'
import UiButton from '../ui/UiButton.vue'
defineProps<{ mobile?: boolean }>()
const route = useRoute()
const ui = useUiStore()
function selected(path: string): boolean {
  return path === '/' ? route.path === '/' : route.path.startsWith(path)
}
</script>
<template>
  <aside
    :class="[
      'app-sidebar',
      { 'is-collapsed': ui.sidebarCollapsed && !mobile, 'is-mobile': mobile },
    ]"
    aria-label="Sidebar"
  >
    <RouterLink
      to="/"
      class="product-brand"
      aria-label="QA Portal, dashboard"
    >
      <span class="product-mark">
        q
        <span>.</span>
      </span>
      <span class="brand-copy">
        QA Portal
        <small>Personal workspace</small>
      </span>
    </RouterLink>
    <div class="sidebar-content">
      <p class="nav-label">WORKSPACE</p>
      <nav aria-label="Navigasi utama">
        <RouterLink
          v-for="item in primaryNavigation"
          :key="item.path"
          :to="item.path"
          :class="['nav-item', { selected: selected(item.path) }]"
          :aria-current="selected(item.path) ? 'page' : undefined"
          :aria-label="item.label"
          :title="ui.sidebarCollapsed && !mobile ? item.label : undefined"
        >
          <component
            :is="item.icon"
            :size="20"
            :weight="selected(item.path) ? 'duotone' : 'regular'"
            aria-hidden="true"
          />
          <span class="nav-copy">{{ item.label }}</span>
        </RouterLink>
      </nav>
      <nav
        aria-label="Preferensi dan komponen"
        class="secondary-nav"
      >
        <RouterLink
          v-for="item in secondaryNavigation"
          :key="item.path"
          :to="item.path"
          :class="['nav-item', { selected: selected(item.path) }]"
          :aria-current="selected(item.path) ? 'page' : undefined"
          :aria-label="item.label"
          :title="ui.sidebarCollapsed && !mobile ? item.label : undefined"
        >
          <component
            :is="item.icon"
            :size="20"
            aria-hidden="true"
          />
          <span class="nav-copy">{{ item.label }}</span>
        </RouterLink>
      </nav>
    </div>
    <div class="sidebar-footer">
      <PhDesktop
        :size="20"
        aria-hidden="true"
      />
      <div class="footer-copy">
        <strong>Workspace lokal</strong>
        <small>Di perangkatmu sendiri</small>
      </div>
      <UiButton
        v-if="!mobile"
        icon-only
        variant="ghost"
        :label="ui.sidebarCollapsed ? 'Perluas sidebar' : 'Ringkas sidebar'"
        @click="ui.sidebarCollapsed = !ui.sidebarCollapsed"
      >
        <component
          :is="ui.sidebarCollapsed ? PhArrowRight : PhArrowLeft"
          :size="16"
        />
      </UiButton>
    </div>
  </aside>
</template>
<style scoped>
.app-sidebar {
  height: 100%;
  overflow: hidden;
  background: var(--color-surface);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-border);
}
.product-brand {
  display: flex;
  align-items: center;
  gap: 11px;
  height: 100px;
  padding: 24px;
  flex-shrink: 0;
}
.product-mark {
  display: grid;
  place-items: center;
  position: relative;
  width: 37px;
  height: 39px;
  background: var(--color-ink);
  color: var(--color-text-on-ink);
  border-radius: 9px;
  font-weight: 600;
  font-size: 27px;
  line-height: 1;
  padding-bottom: 4px;
}
.product-mark span {
  color: var(--color-blush);
  position: absolute;
  right: 6px;
  bottom: 7px;
  font-size: 23px;
}
.brand-copy {
  font-size: 19px;
  font-weight: 600;
  letter-spacing: -0.5px;
  white-space: nowrap;
}
.brand-copy small {
  display: block;
  font-size: 11px;
  font-weight: 400;
  letter-spacing: 0.1px;
  color: var(--color-text-muted);
  margin-top: 1px;
}
.sidebar-content {
  padding: 22px 16px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior-y: contain;
}
.nav-label {
  color: var(--color-text-muted);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.14em;
  margin: 0 12px 14px;
}
nav {
  display: grid;
  gap: 5px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  min-height: 46px;
  border-radius: 8px;
  color: var(--color-text-muted);
  font-size: 14px;
  transition: background var(--duration-fast);
}
.nav-item:hover {
  background: var(--color-surface-subtle);
  color: var(--color-text);
}
.nav-item.selected {
  background: color-mix(in srgb, var(--color-primary) 9%, var(--color-surface));
  color: var(--color-primary);
  font-weight: 500;
}
.secondary-nav {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid var(--color-border);
}
.sidebar-footer {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 16px;
  border-top: 1px solid var(--color-border);
  color: var(--color-text-muted);
}
.footer-copy {
  flex: 1;
}
.footer-copy strong {
  display: block;
  font-size: 12px;
  color: var(--color-text);
  font-weight: 500;
  white-space: nowrap;
}
.footer-copy small {
  display: block;
  font-size: 11px;
  margin-top: 3px;
  white-space: nowrap;
}
.is-collapsed .nav-copy,
.is-collapsed .brand-copy,
.is-collapsed .nav-label,
.is-collapsed .footer-copy,
.is-collapsed .sidebar-footer > svg {
  display: none;
}
.is-collapsed .product-brand {
  padding: 20px;
}
.is-collapsed .sidebar-content {
  padding: 24px 12px;
}
.is-collapsed .nav-item {
  justify-content: center;
}
.is-collapsed .sidebar-footer {
  justify-content: center;
}
.is-mobile {
  height: auto;
  overflow: visible;
  border: 0;
}
.is-mobile .product-brand {
  display: none;
}
.is-mobile .sidebar-content {
  overflow: visible;
  padding: 0 0 20px;
}
.is-mobile .sidebar-footer {
  padding-bottom: 0;
}
</style>
