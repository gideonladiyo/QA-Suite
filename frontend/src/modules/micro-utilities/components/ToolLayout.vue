<script setup lang="ts">
import { toolNavigation } from '../../../shared/navigation'
import UiBreadcrumbs from '../../../shared/components/ui/UiBreadcrumbs.vue'
defineProps<{ title: string; description: string }>()
</script>
<template>
  <UiBreadcrumbs :items="[{ label: 'Micro Tools', to: '/micro-utilities' }, { label: title }]" />
  <header class="page-header">
    <div>
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
    </div>
  </header>
  <nav
    class="tool-nav"
    aria-label="Micro Tools"
  >
    <RouterLink
      v-for="tool in toolNavigation"
      :key="tool.path"
      :to="tool.path"
    >
      <component
        :is="tool.icon"
        :size="18"
        aria-hidden="true"
      />
      {{ tool.label }}
    </RouterLink>
  </nav>
  <div class="micro-workspace"><slot /></div>
</template>
<style>
.tool-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 28px;
}
.tool-nav a {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 48px;
  padding: 10px 0;
  color: var(--color-text-muted);
  border-bottom: 2px solid transparent;
}
.tool-nav .router-link-exact-active {
  border-color: var(--color-primary);
  color: var(--color-primary);
  font-weight: 500;
}
.tool-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
  align-items: start;
}
.tool-grid > *,
.micro-workspace {
  min-width: 0;
}
.tool-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.tool-notice {
  background: var(--color-surface-subtle);
  border-left: 3px solid var(--color-primary);
  padding: 12px 16px;
  font-size: 14px;
}
.tool-details {
  border-top: 1px solid var(--color-border);
  padding-top: 12px;
}
.tool-details summary {
  cursor: pointer;
  padding: 12px 0;
  font-weight: 500;
}
.tool-code textarea {
  font-family: var(--font-mono);
  font-size: 14px;
}
.tool-section {
  display: grid;
  gap: 16px;
}
.micro-workspace pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.micro-workspace .field-control {
  min-width: 0;
}
@media (max-width: 1000px) {
  .tool-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
