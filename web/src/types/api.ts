/**
 * TypeScript interfaces matching the JSON API contracts
 * Defined in design plan: data/index.json, data/scores/YYYY-MM-DD.json,
 * data/games/{gameId}/boxscore.json, data/games/{gameId}/gameflow.json
 */

// ============================================================================
// Index Data (data/index.json)
// ============================================================================

export interface GameSummary {
  gameId: string;
  home: string;
  away: string;
  homeScore: number;
  awayScore: number;
}

export interface DateEntry {
  date: string;
  games: GameSummary[];
}

export interface IndexData {
  dates: DateEntry[];
}

// ============================================================================
// Score Data (data/scores/YYYY-MM-DD.json)
// ============================================================================

export interface TeamInfo {
  tricode: string;
  name: string;
  score: number;
}

export interface ScoreEntry {
  gameId: string;
  date: string;
  homeTeam: TeamInfo;
  awayTeam: TeamInfo;
  status: string;
}

// ============================================================================
// Box Score Data (data/games/{gameId}/boxscore.json)
// ============================================================================

export interface PlayerTotals {
  min: number;
  fgm: number;
  fga: number;
  fg3m: number;
  fg3a: number;
  ftm: number;
  fta: number;
  oreb: number;
  reb: number;
  ast: number;
  blk: number;
  stl: number;
  tov: number;
  pf: number;
  pts: number;
  plusMinus: number;
  hv: number;
  prod: number;
  eff: number;
}

export interface StintData {
  period: number;
  inTime: string;
  outTime: string;
  minutes: number;
  plusMinus: number;
  fgm: number;
  fga: number;
  fg3m: number;
  fg3a: number;
  ftm: number;
  fta: number;
  oreb: number;
  reb: number;
  ast: number;
  blk: number;
  stl: number;
  tov: number;
  pf: number;
  pts: number;
}

export interface PlayerData {
  playerId: string;
  name: string;
  team: string;
  position?: string;   // "G", "F", "C" for starters; empty for bench
  starter?: boolean;    // true if player started the game
  totals: PlayerTotals;
  stints: StintData[];
}

export interface TeamTotals {
  fgm: number;
  fga: number;
  fg3m: number;
  fg3a: number;
  ftm: number;
  fta: number;
  oreb: number;
  reb: number;
  ast: number;
  blk: number;
  stl: number;
  tov: number;
  pf: number;
  pts: number;
}

export interface PeriodTotals {
  period: number;
  fgm: number;
  fga: number;
  fg3m: number;
  fg3a: number;
  ftm: number;
  fta: number;
  pts: number;
}

export interface BoxScoreData {
  gameId: string;
  date: string;
  homeTeam: TeamInfo;
  awayTeam: TeamInfo;
  players: PlayerData[];
  teamTotals: {
    home: TeamTotals;
    away: TeamTotals;
  };
  periodTotals: {
    home: PeriodTotals[];
    away: PeriodTotals[];
  };
}

// ============================================================================
// Gameflow Data (data/games/{gameId}/gameflow.json)
// ============================================================================

export interface StintStats {
  fgm: number;
  fga: number;
  fg3m: number;
  fg3a: number;
  ftm: number;
  fta: number;
  pts: number;
  ast: number;
  reb: number;
  stl: number;
  blk: number;
  tov: number;
  pf: number;
}

export interface PlayByPlayEvent {
  clock: string;
  type: string;
  description: string;
}

export interface GameflowStint {
  period: number;
  inTime: string;
  outTime: string;
  minutes: number;
  plusMinus: number;
  stats: StintStats;
  events: PlayByPlayEvent[];
}

export interface GameflowPlayer {
  playerId: string;
  name: string;
  team: string;
  position?: string;   // "G", "F", "C" for starters; empty for bench
  starter?: boolean;    // true if player started the game
  stints: GameflowStint[];
}

export interface ScoreChange {
  ts: number;        // Elapsed game minutes (0 = start, 12 = end of Q1, etc.)
  homeScore: number;
  awayScore: number;
}

export interface GameflowData {
  gameId: string;
  homeTeam: {
    tricode: string;
    name: string;
  };
  awayTeam: {
    tricode: string;
    name: string;
  };
  players: GameflowPlayer[];
  scoreChanges?: ScoreChange[];
}
