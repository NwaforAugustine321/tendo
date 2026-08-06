import { request } from './http'

export interface DataSource {
  id?: string
  business_id: string
  source_type: string
  status: string
  details: Record<string, unknown>
}

export interface WhatsAppConnectConfig {
  app_id: string
  config_id: string
}

export async function onboardWhatsApp(businessId: string, code: string, wabaId?: string, phoneNumberId?: string): Promise<DataSource> {
  return request<DataSource>('/integrations/whatsapp/onboard', {
    method: 'POST',
    body: {
      business_id: businessId,
      code,
      waba_id: wabaId,
      phone_number_id: phoneNumberId,
    },
  })
}

export async function listDataSources(businessId: string): Promise<DataSource[]> {
  return request<DataSource[]>(`/integrations/data-sources?business_id=${businessId}`)
}

export async function connectDataSource(businessId: string, sourceType: string, details: Record<string, unknown> = {}): Promise<DataSource> {
  return request<DataSource>('/integrations/data-sources/connect', {
    method: 'POST',
    body: { business_id: businessId, source_type: sourceType, details },
  })
}

export async function disconnectDataSource(businessId: string, sourceType: string): Promise<void> {
  await request(`/integrations/data-sources/disconnect?business_id=${businessId}&source_type=${sourceType}`, {
    method: 'POST',
  })
}
