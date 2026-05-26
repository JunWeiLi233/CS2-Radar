export interface Event {
  id: number
  name: string
  date_start: string
  date_end: string
  prize: string
  location: string
  status: string
  logo_url: string
}

export interface Team {
  id: number
  name: string
  logo_url: string
}

export interface Match {
  id: number
  event_id: number
  event_name: string
  team1: Team
  team2: Team
  score1: number | null
  score2: number | null
  format: string
  status: string
  date: string
}

export interface PlayerStats {
  player_id: number
  player_name: string
  team_name: string
  rating: number
  kpr: number
  adr: number
  kast: number
  impact: number
  dpr: number
  kills: number
  deaths: number
  plus_minus: number
  hs_percent: number
}

export interface MatchDetail {
  match: Match
  team1_players: PlayerStats[]
  team2_players: PlayerStats[]
}

export interface EventDetail {
  event: Event
  matches: Match[]
}
