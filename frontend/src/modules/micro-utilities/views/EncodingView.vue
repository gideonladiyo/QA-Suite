<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import ToolLayout from '../components/ToolLayout.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiSelect from '../../../shared/components/ui/UiSelect.vue'
import UiTextarea from '../../../shared/components/ui/UiTextarea.vue'
import UiCodeBlock from '../../../shared/components/ui/UiCodeBlock.vue'
import { errorMessage } from '../../../shared/api'
import { decodeBase64, decodeJwt, encodeBase64, jwtTimeStatus, verifyJwt } from '../encoding'
import { useMicroStore } from '../store'
const state = useMicroStore().encoding
const base64Error = ref(''),
  verifyError = ref(''),
  verdict = ref(''),
  verifying = ref(false),
  now = ref(Date.now()),
  expectedAlgorithm = ref('HS256')
let revision = 0
const interval = setInterval(() => {
  now.value = Date.now()
}, 1000)
onBeforeUnmount(() => {
  clearInterval(interval)
  revision++
})
watch(
  () => [state.text, state.alphabet],
  () => {
    base64Error.value = ''
    state.output = ''
  },
)
watch(
  () => [state.token, state.key, expectedAlgorithm.value],
  () => {
    revision++
    verifying.value = false
    verifyError.value = ''
    verdict.value = ''
  },
)
const decoded = computed(() => {
  if (!state.token.trim()) return { jwt: undefined, error: '' }
  try {
    return { jwt: decodeJwt(state.token), error: '' }
  } catch (cause) {
    return { jwt: undefined, error: errorMessage(cause) }
  }
})
function convert(action: 'encode' | 'decode'): void {
  base64Error.value = ''
  state.output = ''
  try {
    state.output =
      action === 'encode'
        ? encodeBase64(state.text, state.alphabet === 'url')
        : decodeBase64(state.text, state.alphabet === 'url')
  } catch (cause) {
    base64Error.value = errorMessage(cause)
  }
}
function timeLabel(value: unknown): string {
  return typeof value === 'number' && Number.isFinite(value) && Math.abs(value) <= 8640000000000
    ? new Date(value * 1000).toLocaleString('id-ID', { timeZoneName: 'short' })
    : 'Bukan NumericDate yang valid'
}
function clearJwt(): void {
  state.token = ''
  state.key = ''
}
async function verify(): Promise<void> {
  const current = ++revision
  verifying.value = true
  verdict.value = ''
  verifyError.value = ''
  try {
    const valid = await verifyJwt(state.token, state.key, expectedAlgorithm.value)
    if (current === revision)
      verdict.value = valid
        ? 'Signature cocok dengan key. Issuer, audience, dan kebijakan aplikasi belum diverifikasi.'
        : 'Signature tidak cocok. Jangan percaya token ini.'
  } catch (cause) {
    if (current === revision) verifyError.value = errorMessage(cause)
  } finally {
    if (current === revision) verifying.value = false
  }
}
</script>
<template>
  <ToolLayout
    title="Base64 / JWT"
    description="Encode teks dan periksa token tanpa mengirim input atau key ke server. Decode bukan verifikasi keamanan."
  >
    <section
      class="tool-section"
      aria-label="Base64"
    >
      <h2>Base64</h2>
      <div class="tool-grid">
        <div class="tool-section">
          <UiSelect
            v-model="state.alphabet"
            label="Alfabet Base64"
            :options="[
              { value: 'standard', label: 'Standar (+ / dengan padding)' },
              { value: 'url', label: 'URL-safe (- _ tanpa padding)' },
            ]"
          />
          <UiTextarea
            v-model="state.text"
            label="Teks / Base64"
            class="tool-code"
            rows="6"
            maxlength="1048576"
            spellcheck="false"
            hint="Teks UTF-8, maksimal 1 MB. Bukan untuk file biner."
          />
          <div class="tool-actions">
            <UiButton
              :disabled="!state.text"
              @click="convert('encode')"
            >
              Encode
            </UiButton>
            <UiButton
              variant="secondary"
              :disabled="!state.text"
              @click="convert('decode')"
            >
              Decode
            </UiButton>
            <UiButton
              variant="secondary"
              :disabled="!state.text"
              @click="state.text = ''"
            >
              Kosongkan
            </UiButton>
          </div>
          <p
            v-if="base64Error"
            role="alert"
            class="field-error"
          >
            {{ base64Error }}
          </p>
        </div>
        <div class="tool-section">
          <UiCodeBlock
            v-if="state.output"
            :code="state.output"
            label="Hasil Base64 / teks"
          />
          <p
            v-else
            class="tool-notice"
          >
            Hasil encode atau decode ditampilkan di sini. Base64 adalah encoding, bukan enkripsi.
          </p>
        </div>
      </div>
    </section>
    <section
      class="tool-section jwt-section"
      aria-label="JWT decoder"
    >
      <h2>JWT decoder</h2>
      <UiTextarea
        v-model="state.token"
        label="JWT"
        class="tool-code"
        rows="4"
        spellcheck="false"
        autocomplete="off"
        maxlength="1048576"
        hint="Tempel token header.payload.signature. Jangan bagikan token asli dalam screenshot."
      />
      <div class="tool-actions">
        <UiButton
          variant="secondary"
          :disabled="!state.token && !state.key"
          @click="clearJwt"
        >
          Kosongkan JWT & key
        </UiButton>
        <span class="small muted">Token dan key hanya disimpan selama sesi tab ini.</span>
      </div>
      <p
        v-if="decoded.error"
        role="alert"
        class="field-error"
      >
        {{ decoded.error }}
      </p>
      <template v-if="decoded.jwt">
        <p
          class="tool-notice"
          role="status"
        >
          {{ jwtTimeStatus(decoded.jwt.payload, now) }}. Status waktu tidak membuktikan signature
          atau izin akses.
        </p>
        <div class="tool-grid">
          <UiCodeBlock
            :code="JSON.stringify(decoded.jwt.header, null, 2)"
            label="Header JSON"
          />
          <UiCodeBlock
            :code="JSON.stringify(decoded.jwt.payload, null, 2)"
            label="Payload JSON"
          />
        </div>
        <dl class="jwt-times">
          <template
            v-for="key in ['exp', 'iat', 'nbf']"
            :key="key"
          >
            <dt>{{ key }}</dt>
            <dd>
              {{ key in decoded.jwt.payload ? timeLabel(decoded.jwt.payload[key]) : 'Tidak ada' }}
            </dd>
          </template>
        </dl>
        <details class="tool-details">
          <summary>Segmen mentah & signature</summary>
          <div class="tool-section">
            <UiCodeBlock
              v-for="(segment, index) in decoded.jwt.segments"
              :key="index"
              :code="segment"
              :label="
                ['Header (Base64URL)', 'Payload (Base64URL)', 'Signature (Base64URL)'][index]!
              "
            />
          </div>
        </details>
        <details class="tool-details">
          <summary>Verifikasi signature (opsional, lokal)</summary>
          <div class="tool-section">
            <UiSelect
              v-model="expectedAlgorithm"
              label="Algoritma yang kamu harapkan"
              :options="[
                { value: 'HS256', label: 'HS256 — shared secret' },
                { value: 'RS256', label: 'RS256 — public key PEM' },
              ]"
            />
            <UiInput
              v-if="expectedAlgorithm === 'HS256'"
              v-model="state.key"
              label="HS256 secret"
              type="password"
              autocomplete="new-password"
              maxlength="16384"
            />
            <UiTextarea
              v-else
              v-model="state.key"
              label="RS256 public key PEM (SPKI)"
              class="tool-code"
              maxlength="16384"
              spellcheck="false"
              hint="Hanya BEGIN PUBLIC KEY. Jangan tempel private key."
            />
            <p class="small muted">
              Algoritma header harus cocok dengan pilihanmu. Algoritma none, ekstensi kritis, dan
              key URL otomatis tidak didukung. Tidak ada pengambilan JWKS dari jaringan.
            </p>
            <UiButton
              :loading="verifying"
              :disabled="!state.key"
              @click="verify"
            >
              Verifikasi signature
            </UiButton>
            <p
              v-if="verdict"
              role="status"
              class="tool-notice"
            >
              {{ verdict }}
            </p>
            <p
              v-if="verifyError"
              role="alert"
              class="field-error"
            >
              {{ verifyError }}
            </p>
          </div>
        </details>
      </template>
    </section>
  </ToolLayout>
</template>
<style scoped>
.jwt-section {
  margin-top: 40px;
  padding-top: 24px;
  border-top: 1px solid var(--color-border);
}
.jwt-times {
  display: grid;
  grid-template-columns: 64px 1fr;
  gap: 8px 16px;
  margin: 0;
}
.jwt-times dt {
  font-family: var(--font-mono);
}
.jwt-times dd {
  margin: 0;
}
</style>
