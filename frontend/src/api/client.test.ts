import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiFetch } from './client'

afterEach(() => vi.unstubAllGlobals())

describe('apiFetch', () => {
  it('returns the parsed JSON body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"status":"ok"}')))
    await expect(apiFetch('/health')).resolves.toEqual({ status: 'ok' })
  })

  it('turns domain errors into ApiError', async () => {
    const body = JSON.stringify({ error: 'SlotUnavailableError', detail: 'already booked' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 409 })))
    const error = await apiFetch('/bookings').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 409, error: 'SlotUnavailableError', message: 'already booked' })
  })
})
