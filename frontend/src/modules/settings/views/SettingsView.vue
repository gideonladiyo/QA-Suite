<script setup lang="ts">
import { PhSun, PhMoon, PhMonitor, PhArrowRight, PhCheck } from '@phosphor-icons/vue'
import { useUiStore } from '../../../shared/stores/ui'
import type { ThemePreference } from '../../../shared/stores/ui'
import UiCard from '../../../shared/components/ui/UiCard.vue'
import UiErrorState from '../../../shared/components/ui/UiErrorState.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import WorkspacePalette from '../components/WorkspacePalette.vue'
import { ref } from 'vue'
import { useAuthStore } from '../../../shared/stores/auth'
import { errorMessage } from '../../../shared/api'
const auth = useAuthStore()
const logoutBusy = ref(false)
const logoutError = ref('')
async function logout(): Promise<void> {
  logoutBusy.value = true
  logoutError.value = ''
  try {
    await auth.logout()
  } catch (cause) {
    logoutError.value = errorMessage(cause)
  } finally {
    logoutBusy.value = false
  }
}
const ui = useUiStore()
const themes: { value: ThemePreference; label: string; description: string; icon: typeof PhSun }[] =
  [
    {
      value: 'light',
      label: 'Terang',
      description: 'Permukaan bersih, aksen lembut.',
      icon: PhSun,
    },
    { value: 'dark', label: 'Gelap', description: 'Kontras tenang di ruang redup.', icon: PhMoon },
    {
      value: 'system',
      label: 'Ikuti perangkat',
      description: 'Menyesuaikan pengaturan sistem.',
      icon: PhMonitor,
    },
  ]
</script>
<template>
  <div class="page-header">
    <div>
      <h1>Settings</h1>
      <p>Sesuaikan workspace dengan cara kamu bekerja.</p>
    </div>
  </div>
  <div class="settings-content">
    <section class="mb-8 stack">
      <div>
        <h2>Akun lokal</h2>
        <p class="muted small mt-2">
          Masuk sebagai {{ auth.username }}. Sesi berlaku selama 12 jam.
        </p>
      </div>
      <div>
        <UiButton
          variant="secondary"
          :loading="logoutBusy"
          @click="logout"
        >
          Keluar dari workspace
        </UiButton>
      </div>
      <UiErrorState
        v-if="logoutError"
        :message="logoutError"
      />
    </section>
    <section>
      <div class="section-heading">
        <div>
          <h2>Tampilan</h2>
          <p>Pilihan tema tersimpan di browser ini.</p>
        </div>
      </div>
      <div
        class="theme-options"
        role="group"
        aria-label="Pilihan tema"
      >
        <UiCard
          v-for="option in themes"
          :key="option.value"
          interactive
          padding="sm"
          :aria-pressed="ui.theme === option.value"
          :class="{ 'theme-selected': ui.theme === option.value }"
          @click="ui.setTheme(option.value)"
        >
          <div class="theme-heading">
            <component
              :is="option.icon"
              :size="25"
              weight="duotone"
            />
            <PhCheck
              v-if="ui.theme === option.value"
              :size="18"
            />
          </div>
          <strong>{{ option.label }}</strong>
          <span class="theme-description">{{ option.description }}</span>
        </UiCard>
      </div>
      <UiErrorState
        v-if="ui.preferenceError"
        :message="ui.preferenceError"
        class="mt-4"
      />
      <p
        v-else
        class="setting-feedback"
        role="status"
      >
        Tema aktif: {{ themes.find((option) => option.value === ui.theme)?.label }}.
      </p>
    </section>
    <WorkspacePalette class="settings-section" />
    <section class="settings-section">
      <h2>Komponen yang konsisten</h2>
      <p class="muted small mt-2">
        Lihat dan coba button, form, dialog, serta feedback yang dipakai bersama.
      </p>
      <RouterLink
        to="/components"
        class="text-link mt-5"
      >
        Buka komponen UI
        <PhArrowRight :size="16" />
      </RouterLink>
    </section>
  </div>
</template>
<style scoped>
.settings-content {
  max-width: 820px;
}
.theme-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.theme-heading {
  display: flex;
  justify-content: space-between;
  color: var(--color-primary);
  margin-bottom: 22px;
}
.theme-options strong {
  font-size: 14px;
  font-weight: 500;
}
.theme-description {
  display: block;
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 6px;
}
.theme-selected {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
.setting-feedback {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 20px;
}
.settings-section {
  padding-top: 30px;
  margin-top: 32px;
  border-top: 1px solid var(--color-border);
}
@media (max-width: 600px) {
  .theme-options {
    grid-template-columns: 1fr;
  }
  .theme-heading {
    margin-bottom: 14px;
  }
}
</style>
