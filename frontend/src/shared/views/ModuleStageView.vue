<script setup lang="ts">
import { PhArrowLeft, PhArrowRight, PhCheckSquareOffset } from '@phosphor-icons/vue'
import { toolNavigation } from '../navigation'
import UiCard from '../components/ui/UiCard.vue'
import UiBadge from '../components/ui/UiBadge.vue'
defineProps<{
  title: string
  description: string
  stage: string
  features: string[]
  showTools?: boolean
  securityNotice?: string
}>()
</script>
<template>
  <div class="page-header">
    <div>
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
    </div>
    <UiBadge>{{ stage }}</UiBadge>
  </div>
  <nav
    v-if="showTools"
    class="tool-nav"
    aria-label="Pilih micro tool"
  >
    <RouterLink
      v-for="tool in toolNavigation"
      :key="tool.path"
      :to="tool.path"
    >
      <component
        :is="tool.icon"
        :size="18"
      />
      {{ tool.label }}
    </RouterLink>
  </nav>
  <UiCard
    class="stage-card"
    padding="lg"
  >
    <PhCheckSquareOffset
      :size="42"
      weight="duotone"
      class="stage-icon"
    />
    <h2>Modul ini masuk tahap berikutnya.</h2>
    <p>Fondasi antarmuka sudah siap. Berikut yang akan dibangun untuk {{ title }}:</p>
    <ul>
      <li
        v-for="feature in features"
        :key="feature"
      >
        {{ feature }}
      </li>
    </ul>
    <p
      v-if="securityNotice"
      class="security-notice"
    >
      {{ securityNotice }}
    </p>
    <div class="cluster">
      <RouterLink
        to="/components"
        class="text-link"
      >
        Coba komponen UI
        <PhArrowRight :size="16" />
      </RouterLink>
      <RouterLink
        to="/"
        class="text-link"
      >
        <PhArrowLeft :size="16" />
        Kembali ke dashboard
      </RouterLink>
    </div>
  </UiCard>
</template>
<style scoped>
.stage-card {
  max-width: 740px;
}
.stage-icon {
  color: var(--color-secondary);
  margin-bottom: 24px;
}
.stage-card > p {
  margin-top: 12px;
  font-size: 14px;
  color: var(--color-text-muted);
}
.stage-card ul {
  display: grid;
  gap: 10px;
  margin: 24px 0 32px;
  padding-left: 20px;
  font-size: 14px;
}
.stage-card .cluster {
  gap: 24px;
}
.stage-card .security-notice {
  color: var(--color-warning);
  background: color-mix(in srgb, var(--color-warning) 8%, var(--color-surface));
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 24px;
}
.tool-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 24px;
}
.tool-nav a {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
  color: var(--color-text-muted);
}
.tool-nav .router-link-active {
  background: var(--color-surface-subtle);
  color: var(--color-primary);
}
</style>
