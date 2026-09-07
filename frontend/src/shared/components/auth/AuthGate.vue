<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useUiStore } from '../../stores/ui'
import UiButton from '../ui/UiButton.vue'
import { errorMessage } from '../../api'
import UiCard from '../ui/UiCard.vue'
import UiModal from '../ui/UiModal.vue'
import UiSkeleton from '../ui/UiSkeleton.vue'
import UiErrorState from '../ui/UiErrorState.vue'
import LoginForm from './LoginForm.vue'
const auth = useAuthStore()
const ui = useUiStore()
function toggleTheme(): void {
  ui.setTheme(ui.theme === 'dark' ? 'light' : 'dark')
}
const loading = ref(true)
const error = ref('')
const expired = computed(() => !auth.authDisabled && auth.everAuthenticated && !auth.authenticated)
async function check(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    await auth.check()
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}
function expire(): void {
  auth.authenticated = false
}
onMounted(() => {
  void check()
  window.addEventListener('qa:session-expired', expire)
})
onUnmounted(() => window.removeEventListener('qa:session-expired', expire))
</script>
<template>
  <template v-if="auth.authDisabled || auth.everAuthenticated">
    <slot />
    <UiModal
      :model-value="expired"
      title="Masuk kembali"
      description="Sesi berakhir. Isian yang belum disimpan tetap ada di halaman ini."
      :dismissible="false"
      size="sm"
    >
      <LoginForm />
    </UiModal>
  </template>
  <main
    v-else
    class="auth-page"
  >
    <div class="auth-intro">
      <div class="auth-heading">
        <span class="auth-mark">QA / LOCAL</span>
        <UiButton
          variant="ghost"
          size="sm"
          @click="toggleTheme"
        >
          {{ ui.theme === 'dark' ? 'Tema terang' : 'Tema gelap' }}
        </UiButton>
      </div>
      <h1>{{ auth.setupRequired ? 'Siapkan workspace-mu.' : 'Kembali ke pekerjaanmu.' }}</h1>
      <p>Laporan pengujian dan alat developer, tersimpan di perangkatmu.</p>
    </div>
    <UiCard
      class="auth-card"
      padding="lg"
    >
      <UiSkeleton
        v-if="loading"
        :lines="4"
        label="Memeriksa sesi"
      />
      <UiErrorState
        v-else-if="error"
        :message="error"
        retryable
        @retry="check"
      />
      <template v-else>
        <h2>{{ auth.setupRequired ? 'Akun lokal pertama' : 'Masuk' }}</h2>
        <p class="muted small auth-description">
          {{
            auth.setupRequired
              ? 'Satu akun untuk portal ini. Pilih password yang dapat kamu simpan dengan aman; belum ada pemulihan password otomatis.'
              : 'Gunakan akun yang dibuat saat setup pertama.'
          }}
        </p>
        <LoginForm />
      </template>
    </UiCard>
    <p class="muted small">Tidak terhubung ke penyedia login eksternal.</p>
  </main>
</template>
<style scoped>
.auth-page {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 24px;
  padding: 40px 20px;
}
.auth-intro,
.auth-card {
  width: 100%;
  max-width: 460px;
}
.auth-intro h1 {
  font-size: 30px;
  line-height: 1.2;
  margin: 22px 0 12px;
}
.auth-intro p {
  color: var(--color-text-muted);
  line-height: 1.7;
}
.auth-mark {
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  border-left: 4px solid var(--color-blush);
  padding-left: 12px;
}
.auth-description {
  margin: 12px 0 24px;
  line-height: 1.6;
}
.auth-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
</style>
