import { useState, useEffect } from 'react'
import type { EventDetail } from '../types'
import { getEventDetail } from '../api'

interface EventDetailProps {
  eventId: number
  onSelectMatch: (matchId: number) => void
  onBack: () => void
}

export default function EventDetailView({ eventId, onSelectMatch, onBack }: EventDetailProps) {
  const [detail, setDetail] = useState<EventDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    getEventDetail(eventId)
      .then(setDetail)
      .catch(() => setError('Failed to load event details.'))
      .finally(() => setLoading(false))
  }, [eventId])

  if (loading) {
    return (
      <div className="space-y-3 px-4">
        {Array.from({ length: 8 }, (_, i) => (
          <div key={i} className="h-16 bg-surface rounded animate-pulse" />
        ))}
      </div>
    )
  }

  if (error || !detail) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <p className="text-zinc-500 text-sm">{error ?? 'Event not found.'}</p>
        <button onClick={onBack} className="text-accent text-sm hover:underline">Go back</button>
      </div>
    )
  }

  const { event, matches } = detail

  return (
    <div>
      {/* Header */}
      <div className="px-4 py-5 border-b border-zinc-800/50">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors mb-3"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Events
        </button>
        <div className="flex items-center gap-3">
          {event.logo_url && (
            <img src={event.logo_url} alt="" className="w-10 h-10 object-contain rounded bg-zinc-800/50" />
          )}
          <div>
            <h2 className="text-lg font-bold text-zinc-100 tracking-tight">{event.name}</h2>
            <p className="text-xs text-zinc-500 font-mono mt-0.5">
              {event.date_start} — {event.date_end}
              {event.prize && <span className="ml-3 text-accent">{event.prize}</span>}
              {event.location && <span className="ml-3">{event.location}</span>}
            </p>
          </div>
        </div>
      </div>

      {/* Matches */}
      <div className="divide-y divide-zinc-800/50">
        {matches.length === 0 ? (
          <div className="py-16 text-center text-zinc-500 text-sm">No matches available.</div>
        ) : (
          matches.map((match) => (
            <button
              key={match.id}
              onClick={() => onSelectMatch(match.id)}
              className="w-full text-left group flex items-center gap-4 px-4 py-4 hover:bg-zinc-800/30 transition-all duration-300"
            >
              {/* Team 1 */}
              <div className="flex items-center gap-2 flex-1 justify-end min-w-0">
                <span className="text-sm font-medium text-zinc-300 truncate group-hover:text-zinc-200 transition-colors">
                  {match.team1.name}
                </span>
                {match.team1.logo_url && (
                  <img src={match.team1.logo_url} alt="" className="w-6 h-6 object-contain shrink-0" />
                )}
              </div>

              {/* Score */}
              <div className="flex items-center gap-1.5 shrink-0">
                <span className={`font-mono text-base font-bold tabular-nums ${(match.score1 ?? 0) > (match.score2 ?? 0) ? 'text-zinc-100' : 'text-zinc-500'}`}>
                  {match.score1 ?? '-'}
                </span>
                <span className="text-zinc-600 text-xs">:</span>
                <span className={`font-mono text-base font-bold tabular-nums ${(match.score2 ?? 0) > (match.score1 ?? 0) ? 'text-zinc-100' : 'text-zinc-500'}`}>
                  {match.score2 ?? '-'}
                </span>
              </div>

              {/* Team 2 */}
              <div className="flex items-center gap-2 flex-1 min-w-0">
                {match.team2.logo_url && (
                  <img src={match.team2.logo_url} alt="" className="w-6 h-6 object-contain shrink-0" />
                )}
                <span className="text-sm font-medium text-zinc-300 truncate group-hover:text-zinc-200 transition-colors">
                  {match.team2.name}
                </span>
              </div>

              {/* Meta */}
              <div className="hidden sm:flex items-center gap-2 text-[10px] text-zinc-600 font-mono shrink-0">
                <span className="uppercase tracking-wider">{match.format}</span>
                <span>{match.date}</span>
              </div>

              <svg className="w-4 h-4 text-zinc-600 group-hover:text-accent group-hover:translate-x-0.5 transition-all shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
