import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { vaultApi, type VaultEntry } from './api'
import VaultView from './views/VaultView.vue'

const command: VaultEntry = {
  id: '11111111-1111-4111-8111-111111111111',
  title: 'Restart worker',
  username: null,
  category: 'command',
  url: null,
  last_accessed_at: null,
  created_at: '2026-09-07T00:00:00Z',
  updated_at: '2026-09-07T00:00:00Z',
}

describe('Vault UI', () => {
  it('unlocks into a masked list and can save an important command', async () => {
    vi.spyOn(vaultApi, 'status').mockResolvedValue({ configured: true, unlocked: false })
    vi.spyOn(vaultApi, 'unlock').mockResolvedValue({
      configured: true,
      unlocked: true,
      token: 'vault-session',
      auto_lock_minutes: 5,
    })
    vi.spyOn(vaultApi, 'list').mockResolvedValue([command])
    vi.spyOn(vaultApi, 'lock').mockResolvedValue()
    vi.spyOn(vaultApi, 'touch').mockResolvedValue()
    const create = vi.spyOn(vaultApi, 'create').mockResolvedValue(command)

    const wrapper = mount(VaultView, {
      attachTo: document.body,
      global: { stubs: { Teleport: true } },
    })
    await flushPromises()

    await wrapper.get('input[type="password"]').setValue('test_master_passphrase')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(vaultApi.unlock).toHaveBeenCalledWith('test_master_passphrase', 5)
    expect(wrapper.text()).toContain('Restart worker')
    expect(wrapper.text()).toContain('••••••••')
    expect(wrapper.text()).not.toContain('docker compose restart worker')

    await wrapper
      .findAll('button')
      .find((item) => item.text() === 'Tambah item')!
      .trigger('click')
    await nextTick()
    await wrapper.get('#vault-entry-form select').setValue('command')
    await wrapper.get('#vault-entry-form input[required]').setValue('Restart API')
    await wrapper
      .get('#vault-entry-form textarea[required]')
      .setValue('docker compose restart backend')
    await wrapper.get('#vault-entry-form').trigger('submit')
    await flushPromises()

    expect(create).toHaveBeenCalledWith(
      'vault-session',
      expect.objectContaining({
        title: 'Restart API',
        category: 'command',
        value: 'docker compose restart backend',
      }),
    )
    wrapper.unmount()
    await flushPromises()
  })
})
