import { request } from './http'
import { useBusinessStore } from '../../store/business'

function getBusinessId(): string {
  return useBusinessStore.getState().currentProfile?.id || ''
}

export type Folder = {
  id: string
  business_id: string
  name: string
  icon: string
  color: string
  record_count: number
  records: { id: string; title: string; created_at: string; updated_at: string }[]
  created_at: string
  updated_at: string
}

export type Record = {
  id: string
  business_id: string
  folder_id: string
  title: string
  ai_insight: { version: number; timestamp: string; insight: string; suggested_questions: string[] }[]
  created_at: string
  updated_at: string
}

export type RecordContent = {
  id: string
  business_id: string
  record_id: string
  content_type: string
  content: string
  created_at: string
  updated_at: string
}

export async function getFolders(): Promise<Folder[]> {
  return await request<Folder[]>(`/folders?business_id=${getBusinessId()}`, { silent: true })
}

export async function createFolder(name: string, icon = '', color = ''): Promise<Folder> {
  return await request<Folder>('/folders', { method: 'POST', body: { business_id: getBusinessId(), name, icon, color } })
}

export async function updateFolder(folderId: string, name: string, icon = '', color = ''): Promise<Folder> {
  return await request<Folder>(`/folders/${folderId}`, { method: 'PUT', body: { business_id: getBusinessId(), name, icon, color } })
}

export async function deleteFolder(folderId: string): Promise<void> {
  await request(`/folders/${folderId}?business_id=${getBusinessId()}`, { method: 'DELETE' })
}

export async function getRecords(folderId: string): Promise<Record[]> {
  return await request<Record[]>(`/folders/${folderId}/records?business_id=${getBusinessId()}`, { silent: true })
}

export async function getAllRecords(): Promise<Record[]> {
  return await request<Record[]>(`/records?business_id=${getBusinessId()}`, { silent: true })
}

export async function createRecord(folderId: string, title: string): Promise<Record> {
  return await request<Record>('/records', { method: 'POST', body: { business_id: getBusinessId(), folder_id: folderId || undefined, title } })
}

export async function getRecord(recordId: string): Promise<Record> {
  return await request<Record>(`/records/${recordId}?business_id=${getBusinessId()}`, { silent: true })
}

export async function updateRecord(recordId: string, title: string): Promise<Record> {
  return await request<Record>(`/records/${recordId}`, { method: 'PUT', body: { business_id: getBusinessId(), title } })
}

export async function moveRecord(recordId: string, targetFolderId: string): Promise<Record> {
  return await request<Record>(`/records/${recordId}`, { method: 'PUT', body: { business_id: getBusinessId(), folder_id: targetFolderId } })
}

export async function deleteRecord(recordId: string): Promise<void> {
  await request(`/records/${recordId}?business_id=${getBusinessId()}`, { method: 'DELETE' })
}

export async function getRecordContents(recordId: string): Promise<RecordContent[]> {
  return await request<RecordContent[]>(`/records/${recordId}/content?business_id=${getBusinessId()}`, { silent: true })
}

export async function addRecordContent(recordId: string, contentType: string, content: string, metadata: object = {}): Promise<{ content: RecordContent; processing: boolean }> {
  return await request<{ content: RecordContent; processing: boolean }>(`/records/${recordId}/content`, {
    method: 'POST',
    body: { business_id: getBusinessId(), content_type: contentType, content, metadata },
  })
}

export async function deleteRecordContent(recordId: string, contentId: string): Promise<void> {
  await request(`/records/${recordId}/content/${contentId}?business_id=${getBusinessId()}`, { method: 'DELETE' })
}

export async function getRecordUnderstanding(recordId: string): Promise<{ insight: string; suggested_questions: string[] }> {
  return await request<{ insight: string; suggested_questions: string[] }>(`/records/${recordId}/understanding?business_id=${getBusinessId()}`, { silent: true })
}
