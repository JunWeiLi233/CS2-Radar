import { useState, useEffect } from 'react'
import type { Event } from '../types'
import { getEvents } from '../api'

interface EventListProps {
  onSelectEvent: (eventId: number) => void
}

function statusBadge(status: string) {
  const map: Record<string, { label: string; cls: string }> = {
    ongoing: { label: 'LIVE', cls: 'bg-red-600/20 text-red-400 border-red-600/40' },
    upcoming: { label: 'UPCOMING', cls: 'bg-blue-600/20 text-blue-400 border-blue-600/40' },
    completed: { label: 'DONE', cls: 'bg-zinc-700/50 text-zinc-400 border-zinc-600/30' },
  }
  const s = map[status] ?? map.completed
  return (
    <span className={`text-[10px] font-semibold tracking-widest px-2 py-0.5 border rounded ${s.cls}`}>
      {s.label}
    </span>
  )
}

export default function EventList({ onSelectEvent }: EventListProps) {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getEvents()
      .then(setEvents)
      .catch(() => setError('Failed to load events. Is the backend running?'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="h-20 bg-surface rounded animate-pulse" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <div className="w-12 h-12 rounded-full bg-red-600/10 flex items-center justify-center">
          <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <p className="text-zinc-500 text-sm">{error}</p>
      </div>
    )
  }

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <p className="text-zinc-500 text-sm">No events found. Start the backend and refresh.</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-zinc-800/50">
      {events.map((event, i) => (
        <button
          key={event.id}
          onClick={() => onSelectEvent(event.id)}
          className="w-full text-left group flex items-center gap-4 px-4 py-4 hover:bg-zinc-800/30 transition-all duration-300"
          style={{ animationDelay: `${i * 60}ms` }}
        >
          {/* Logo */}
          <div className="w-12 h-12 rounded-lg bg-zinc-800/50 border border-zinc-700/30 flex items-center justify-center overflow-hidden shrink-0 group-hover:border-accent/30 transition-colors">
            {event.logo_url ? (
              <img src={event.logo_url} alt="" className="w-8 h-8 object-contain" />
            ) : (
              <span className="text-zinc-600 font-bold text-xs">{event.name[0]}</span>
            )}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-zinc-200 truncate group-hover:text-accent transition-colors">
                {event.name}
              </h3>
              {statusBadge(event.status)}
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-zinc-500 font-mono">
              <span>{event.date_start} — {event.date_end}</span>
              {event.prize && <span className="text-accent">{event.prize}</span>}
              {event.location && <span>{event.location}</span>}
            </div>
          </div>

          {/* Arrow */}
          <svg className="w-4 h-4 text-zinc-600 group-hover:text-accent group-hover:translate-x-0.5 transition-all shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      ))}
    </div>
  )
}
