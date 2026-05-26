import { useState } from 'react'
import EventList from './components/EventList'
import EventDetailView from './components/EventDetail'
import MatchDetailView from './components/MatchDetail'

type View =
  | { page: 'events' }
  | { page: 'event'; eventId: number }
  | { page: 'match'; matchId: number }

export default function App() {
  const [view, setView] = useState<View>({ page: 'events' })

  return (
    <div className="min-h-[100dvh] bg-zinc-950 text-zinc-200">
      {/* Top nav */}
      <header className="sticky top-0 z-50 border-b border-zinc-800/50 bg-zinc-950/80 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto flex items-center justify-between px-4 h-14">
          <button
            onClick={() => setView({ page: 'events' })}
            className="flex items-center gap-2 group"
          >
            <svg className="w-6 h-6 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12,2 22,8.5 22,15.5 12,22 2,15.5 2,8.5" strokeLinejoin="round" />
            </svg>
            <span className="text-sm font-bold tracking-tight text-zinc-200 group-hover:text-accent transition-colors">
              CS2 Radar
            </span>
          </button>
          <span className="text-[10px] text-zinc-600 font-mono uppercase tracking-widest">
            Pro Player Stats
          </span>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-5xl mx-auto">
        {view.page === 'events' && (
          <EventList onSelectEvent={(eventId) => setView({ page: 'event', eventId })} />
        )}
        {view.page === 'event' && (
          <EventDetailView
            eventId={view.eventId}
            onSelectMatch={(matchId) => setView({ page: 'match', matchId })}
            onBack={() => setView({ page: 'events' })}
          />
        )}
        {view.page === 'match' && (
          <MatchDetailView
            matchId={view.matchId}
            onBack={() => setView({ page: 'events' })}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800/50 mt-12 py-6 text-center">
        <p className="text-[11px] text-zinc-600 font-mono">
          Data from HLTV.org &middot; Built for CS2 community
        </p>
      </footer>
    </div>
  )
}
