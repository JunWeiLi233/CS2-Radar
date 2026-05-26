import { useState, useEffect } from 'react'
import type { MatchDetail as MatchDetailType, PlayerStats } from '../types'
import { getMatchDetail } from '../api'
import RadarChart from './RadarChart'

interface MatchDetailProps {
  matchId: number
  onBack: () => void
}

function buildRadarData(player: PlayerStats) {
  return [
    { label: 'Rating', value: player.rating, maxValue: 1.5 },
    { label: 'KPR', value: player.kpr, maxValue: 1.0 },
    { label: 'ADR', value: player.adr, maxValue: 100 },
    { label: 'KAST', value: player.kast, maxValue: 100 },
    { label: 'Impact', value: player.impact, maxValue: 1.5 },
    { label: 'Survival', value: Math.max(0, 1 - player.dpr), maxValue: 1 },
  ]
}

function PlayerCard({ player, color, index }: { player: PlayerStats; color: string; index: number }) {
  const radarData = buildRadarData(player)

  return (
    <div
      className="radar-animate flex flex-col items-center gap-3 p-4 rounded-xl bg-surface/60 border border-zinc-800/40 hover:border-zinc-700/60 transition-colors"
      style={{ animationDelay: `${index * 0.08}s` }}
    >
      <RadarChart data={radarData} playerName={player.player_name} color={color} />
      <div className="grid grid-cols-3 gap-x-4 gap-y-1 text-center w-full">
        <div>
          <div className="text-[10px] text-zinc-500 uppercase tracking-wider">K-D</div>
          <div className="font-mono text-xs text-zinc-300 tabular-nums">
            {player.kills}-{player.deaths}
            <span className={player.plus_minus >= 0 ? 'text-emerald-400 ml-0.5' : 'text-red-400 ml-0.5'}>
              {player.plus_minus > 0 ? '+' : ''}{player.plus_minus}
            </span>
          </div>
        </div>
        <div>
          <div className="text-[10px] text-zinc-500 uppercase tracking-wider">ADR</div>
          <div className="font-mono text-xs text-zinc-300 tabular-nums">{player.adr.toFixed(1)}</div>
        </div>
        <div>
          <div className="text-[10px] text-zinc-500 uppercase tracking-wider">HS%</div>
          <div className="font-mono text-xs text-zinc-300 tabular-nums">{player.hs_percent}%</div>
        </div>
      </div>
    </div>
  )
}

export default function MatchDetailView({ matchId, onBack }: MatchDetailProps) {
  const [detail, setDetail] = useState<MatchDetailType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    getMatchDetail(matchId)
      .then(setDetail)
      .catch(() => setError('Failed to load match details.'))
      .finally(() => setLoading(false))
  }, [matchId])

  if (loading) {
    return (
      <div className="p-4 space-y-6">
        <div className="h-8 w-48 bg-surface rounded animate-pulse" />
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {Array.from({ length: 10 }, (_, i) => (
            <div key={i} className="aspect-square bg-surface rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (error || !detail) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <p className="text-zinc-500 text-sm">{error ?? 'Match not found.'}</p>
        <button onClick={onBack} className="text-accent text-sm hover:underline">Go back</button>
      </div>
    )
  }

  const { match, team1_players, team2_players } = detail

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
          {match.event_name}
        </button>

        {/* Score bar */}
        <div className="flex items-center justify-center gap-6">
          {/* Team 1 */}
          <div className="flex items-center gap-3 flex-1 justify-end">
            <span className="text-base font-bold text-zinc-100 tracking-tight">{match.team1.name}</span>
            {match.team1.logo_url && (
              <img src={match.team1.logo_url} alt="" className="w-10 h-10 object-contain" />
            )}
          </div>

          {/* Score */}
          <div className="flex items-center gap-2 shrink-0">
            <span className={`font-mono text-2xl font-bold tabular-nums ${(match.score1 ?? 0) > (match.score2 ?? 0) ? 'text-zinc-100' : 'text-zinc-500'}`}>
              {match.score1 ?? '-'}
            </span>
            <span className="text-zinc-700 text-lg">:</span>
            <span className={`font-mono text-2xl font-bold tabular-nums ${(match.score2 ?? 0) > (match.score1 ?? 0) ? 'text-zinc-100' : 'text-zinc-500'}`}>
              {match.score2 ?? '-'}
            </span>
          </div>

          {/* Team 2 */}
          <div className="flex items-center gap-3 flex-1">
            {match.team2.logo_url && (
              <img src={match.team2.logo_url} alt="" className="w-10 h-10 object-contain" />
            )}
            <span className="text-base font-bold text-zinc-100 tracking-tight">{match.team2.name}</span>
          </div>
        </div>

        <div className="flex justify-center gap-3 mt-2 text-[10px] text-zinc-600 font-mono uppercase tracking-wider">
          <span>{match.format}</span>
          <span>{match.date}</span>
        </div>
      </div>

      {/* Player radars */}
      <div className="p-4 space-y-8">
        {/* Team 1 */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-0.5 h-4 bg-accent rounded-full" />
            <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">{match.team1.name}</h3>
          </div>
          {team1_players.length === 0 ? (
            <p className="text-zinc-600 text-xs py-4">No player stats available.</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {team1_players.map((p, i) => (
                <PlayerCard key={p.player_id} player={p} color="#f59e0b" index={i} />
              ))}
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="border-t border-zinc-800/50" />

        {/* Team 2 */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-0.5 h-4 bg-cyan-400 rounded-full" />
            <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">{match.team2.name}</h3>
          </div>
          {team2_players.length === 0 ? (
            <p className="text-zinc-600 text-xs py-4">No player stats available.</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {team2_players.map((p, i) => (
                <PlayerCard key={p.player_id} player={p} color="#22d3ee" index={i} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
