import { api, apiFile } from '../../shared/api'
export interface CoverageLink {
  url: string
  label: string | null
}
export interface ItemInput {
  id?: string
  activity_code: string
  environment: string
  result: string
  current_status: string | null
  current_issue: string | null
  links: CoverageLink[]
  template_values?: Record<string, string>
}
export interface ReportMetadata {
  report_date: string
  title: string
  author_name: string | null
  template_id?: string | null
}
export interface ReportSummary extends ReportMetadata {
  id: string
  status: string
  item_count: number
}
export interface Report extends ReportMetadata {
  template_name?: string | null
  template_body?: string | null
  template_values?: Record<string, string>
  id: string
  status: 'draft' | 'finalized' | 'sent'
  version: number
  items: ItemInput[]
  updated_at: string
  slack_sent_at: string | null
  email_sent_at: string | null
}
export interface ReportSave extends ReportMetadata {
  template_values?: Record<string, string>
  version: number
  items: ItemInput[]
}
export interface ReportPage {
  reports: ReportSummary[]
  total: number
  page: number
  page_size: number
}
export interface ReportPreview {
  title: string
  slack: string
  html: string
  markdown: string
  slack_mrkdwn: string
}
export interface ReportTemplate {
  id: string
  name: string
  description: string | null
  body: string
  usage_count: number
  created_at: string
  updated_at: string
}
export interface Metrics {
  month: string
  total: number
  pass_rate: number
  issue_count: number
  repeated_entries: number
  environments: { label: string; count: number }[]
  results: { label: string; count: number }[]
  trend: { date: string; count: number }[]
}
const base = '/qa-reports'
export const qaApi = {
  remove: (id: string, version: number): Promise<void> =>
    api(`${base}/${encodeURIComponent(id)}?version=${version}`, { method: 'DELETE' }),
  backup: (): Promise<Blob> => apiFile(`${base}/backup`),
  restore: (json: string): Promise<{ restored: number; skipped: number }> =>
    api(`${base}/restore`, { method: 'POST', body: json }),
  list: (filters: Record<string, string> = {}): Promise<ReportPage> =>
    api(`${base}?${new URLSearchParams(filters)}`),
  listTemplates: (): Promise<ReportTemplate[]> => api(`${base}/templates`),
  createTemplate: (
    body: Omit<ReportTemplate, 'id' | 'usage_count' | 'created_at' | 'updated_at'>,
  ): Promise<ReportTemplate> =>
    api(`${base}/templates`, { method: 'POST', body: JSON.stringify(body) }),
  updateTemplate: (
    id: string,
    body: Omit<ReportTemplate, 'id' | 'usage_count' | 'created_at' | 'updated_at'> & {
      expected_updated_at: string
    },
  ): Promise<ReportTemplate> =>
    api(`${base}/templates/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  removeTemplate: (id: string): Promise<void> =>
    api(`${base}/templates/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  get: (id: string): Promise<Report> => api(`${base}/${encodeURIComponent(id)}`),
  create: (body: ReportMetadata & { items?: ItemInput[] }): Promise<Report> =>
    api(base, { method: 'POST', body: JSON.stringify(body) }),
  save: (id: string, body: ReportSave): Promise<Report> =>
    api(`${base}/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  finalize: (id: string, version: number): Promise<Report> =>
    api(`${base}/${id}/finalize`, { method: 'POST', body: JSON.stringify({ version }) }),
  preview: (id: string): Promise<ReportPreview> => api(`${base}/${id}/preview`),
  metrics: (month: string): Promise<Metrics> =>
    api(`${base}/monthly?${new URLSearchParams({ month })}`),
  csv: (month: string): Promise<Blob> =>
    apiFile(`${base}/monthly.csv?${new URLSearchParams({ month })}`),
  deliveryOptions: (): Promise<{ slack: boolean; email: boolean }> =>
    api(`${base}/delivery-options`),
  send: (
    id: string,
    version: number,
    channel: 'slack' | 'email',
    recipient?: string,
  ): Promise<Report> =>
    api(`${base}/${id}/send`, {
      method: 'POST',
      body: JSON.stringify({ version, channel, recipient }),
    }),
}

export function localDate(date = new Date()): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
export function yesterday(date: string): string {
  const value = new Date(`${date}T12:00:00`)
  value.setDate(value.getDate() - 1)
  return localDate(value)
}
export function safeCoverageUrl(value: string): boolean {
  try {
    const url = new URL(value)
    return (
      ['http:', 'https:'].includes(url.protocol) && !!url.hostname && !url.username && !url.password
    )
  } catch {
    return false
  }
}
export function statusLabel(status: string): string {
  return (
    ({ draft: 'Tersimpan', finalized: 'Final', sent: 'Terkirim' } as Record<string, string>)[
      status
    ] ?? status
  )
}
