<script setup lang="ts">
import type { Pair } from '../api'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
const rows = defineModel<Pair[]>({ required: true })
defineProps<{ label: string; secret?: boolean; disabled?: boolean }>()
</script>
<template>
  <div class="tool-section">
    <div class="tool-actions">
      <h3>{{ label }}</h3>
      <UiButton
        variant="secondary"
        :disabled="disabled || rows.length >= 50"
        @click="rows.push({ key: '', value: '' })"
      >
        Tambah {{ label.toLowerCase() }}
      </UiButton>
    </div>
    <p
      v-if="!rows.length"
      class="small muted"
    >
      Belum ada {{ label.toLowerCase() }} tambahan.
    </p>
    <div
      v-for="(row, index) in rows"
      :key="index"
      class="pair-row"
    >
      <UiInput
        v-model="row.key"
        :label="`${label} ${index + 1}: nama`"
        maxlength="200"
        :disabled="disabled"
      />
      <UiInput
        v-model="row.value"
        :label="`${label} ${index + 1}: nilai`"
        :type="secret ? 'password' : 'text'"
        autocomplete="off"
        maxlength="10000"
        :disabled="disabled"
      />
      <UiButton
        variant="secondary"
        :label="`Hapus ${label} ${index + 1}`"
        :disabled="disabled"
        @click="rows.splice(index, 1)"
      >
        Hapus
      </UiButton>
    </div>
  </div>
</template>
<style scoped>
.pair-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.5fr) auto;
  gap: 12px;
  align-items: end;
}
@media (max-width: 600px) {
  .pair-row {
    grid-template-columns: minmax(0, 1fr);
    padding-bottom: 16px;
    border-bottom: 1px solid var(--color-border);
  }
}
</style>
