/**
 * Health service — check backend status.
 */

import { request } from './http'

export async function healthCheck(): Promise<{ status: string; service: string }> {
  return request('/health')
}
