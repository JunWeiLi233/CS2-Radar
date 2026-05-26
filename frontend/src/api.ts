import type { Event, EventDetail, MatchDetail } from './types'

const BASE = '/api'

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url}`)
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`)
  }
  return res.json()
}

export function getEvents(): Promise<Event[]> {
  return fetchJson('/events')
}

export function getEventDetail(eventId: number): Promise<EventDetail> {
  return fetchJson(`/events/${eventId}`)
}

export function getMatchDetail(matchId: number): Promise<MatchDetail> {
  return fetchJson(`/matches/${matchId}`)
}
