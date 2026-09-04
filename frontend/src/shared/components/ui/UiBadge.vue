<script setup lang="ts">
withDefaults(defineProps<{ tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' }>(), {
  tone: 'neutral',
})
</script>
<template>
  <span :class="['ui-badge', `badge-${tone}`]"><slot /></span>
</template>
<style scoped>
.ui-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
  white-space: nowrap;
}
.badge-success {
  color: var(--color-success);
  background: color-mix(in srgb, var(--color-success) 9%, var(--color-surface));
}
.badge-warning {
  color: var(--color-warning);
  background: color-mix(in srgb, var(--color-warning) 9%, var(--color-surface));
}
.badge-danger {
  color: var(--color-danger);
  background: color-mix(in srgb, var(--color-danger) 8%, var(--color-surface));
}
.badge-info {
  color: var(--color-info);
  background: color-mix(in srgb, var(--color-info) 8%, var(--color-surface));
}
</style>
