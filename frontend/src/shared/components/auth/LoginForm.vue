<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { errorMessage } from '../../api'
import UiInput from '../ui/UiInput.vue'
import UiButton from '../ui/UiButton.vue'
import UiErrorState from '../ui/UiErrorState.vue'
const auth = useAuthStore()
const name = ref(auth.username)
const password = ref('')
const confirmation = ref('')
const busy = ref(false)
const error = ref('')
const mismatch = ref('')
const form = ref<HTMLFormElement>()
async function submit(): Promise<void> {
  mismatch.value = ''
  error.value = ''
  if (auth.setupRequired && password.value !== confirmation.value) {
    mismatch.value = 'Kedua password belum sama.'
    await nextTick()
    form.value?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()
    return
  }
  busy.value = true
  try {
    await auth.login(name.value, password.value)
    password.value = ''
    confirmation.value = ''
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <form
    ref="form"
    class="stack"
    @submit.prevent="submit"
  >
    <UiInput
      v-model="name"
      label="Username"
      required
      autocomplete="username"
      pattern="[a-zA-Z0-9_.\-]+"
      maxlength="80"
      hint="Huruf, angka, titik, tanda hubung, atau underscore."
      autofocus
    />
    <UiInput
      v-model="password"
      label="Password"
      type="password"
      required
      minlength="12"
      maxlength="128"
      :autocomplete="auth.setupRequired ? 'new-password' : 'current-password'"
      hint="12–128 karakter. Gunakan password khusus untuk workspace ini."
    />
    <UiInput
      v-if="auth.setupRequired"
      v-model="confirmation"
      label="Ulangi password"
      type="password"
      autocomplete="new-password"
      required
      :error="mismatch"
    />
    <UiErrorState
      v-if="error"
      :message="error"
    />
    <UiButton
      type="submit"
      :loading="busy"
    >
      {{ auth.setupRequired ? 'Buat akun lokal' : 'Masuk ke workspace' }}
    </UiButton>
  </form>
</template>
