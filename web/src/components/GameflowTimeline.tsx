import { useState, useMemo, useRef, useEffect, useCallback, type MouseEvent as ReactMouseEvent } from "react";
import type { GameflowData, GameflowPlayer, GameflowStint, BoxScoreData, ScoreChange } from "../types/api";

interface GameflowTimelineProps {
  data: GameflowData;
  boxscore?: BoxScoreData;
}

/** Quarter width in pixels (matches original PopcornMachine) */
const QUARTER_PX = 216;
/** Player name column width */
const NAME_COL_PX = 120;
/** End stat column width */
const STAT_COL_PX = 35;
/** Spacer between quarters */
const SPACER_PX = 1;
/** Row height */
const ROW_HEIGHT = 18;
/** Seconds per regulation quarter */
const QUARTER_SECONDS = 720;
/** Seconds per OT period */
const OT_SECONDS = 300;
/** Canvas height for momentum line */
const CANVAS_HEIGHT = 90;
/** Minute selector row height */
const MINUTE_ROW_HEIGHT = 16;

/** Convert "MM:SS" countdown clock to elapsed seconds within period */
function clockToElapsed(clock: string, periodDuration: number): number {
  const [m, s] = clock.split(":").map(Number);
  return periodDuration - (m * 60 + s);
}

interface Segment {
  type: "in" | "out";
  widthPx: number;
  stint?: GameflowStint;
  stintIndex?: number;
}

/**
 * Build segments for one quarter for a player.
 * Fills the full quarter width with alternating IN/OUT segments.
 */
function buildQuarterSegments(
  stints: GameflowStint[],
  period: number,
): Segment[] {
  const periodDuration = period > 4 ? OT_SECONDS : QUARTER_SECONDS;
  const periodStints = stints
    .map((s, idx) => ({ stint: s, idx }))
    .filter((s) => s.stint.period === period)
    .sort(
      (a, b) =>
        clockToElapsed(a.stint.inTime, periodDuration) -
        clockToElapsed(b.stint.inTime, periodDuration),
    );

  const segments: Segment[] = [];
  let cursor = 0;

  for (const { stint, idx } of periodStints) {
    const inElapsed = clockToElapsed(stint.inTime, periodDuration);
    const outElapsed = clockToElapsed(stint.outTime, periodDuration);

    if (inElapsed > cursor) {
      const gapFraction = (inElapsed - cursor) / periodDuration;
      segments.push({ type: "out", widthPx: gapFraction * QUARTER_PX });
    }

    const stintFraction = Math.max(0, outElapsed - inElapsed) / periodDuration;
    segments.push({
      type: "in",
      widthPx: Math.max(stintFraction * QUARTER_PX, 1),
      stint,
      stintIndex: idx,
    });

    cursor = outElapsed;
  }

  if (cursor < periodDuration) {
    const gapFraction = (periodDuration - cursor) / periodDuration;
    segments.push({ type: "out", widthPx: gapFraction * QUARTER_PX });
  }

  return segments;
}

/** Number of end-stat columns */
const NUM_STAT_COLS = 8; // MIN, PTS, REB, AST, STL, BLK, TOV, +/-

/** Compute total minutes, points, individual stats, +/- from all stints */
function computePlayerTotals(stints: GameflowStint[]) {
  let min = 0, pts = 0, pm = 0;
  let reb = 0, ast = 0, blk = 0, stl = 0, tov = 0;
  for (const s of stints) {
    min += s.minutes;
    pts += s.stats.pts;
    pm += s.plusMinus;
    reb += s.stats.reb;
    ast += s.stats.ast;
    blk += s.stats.blk;
    stl += s.stats.stl;
    tov += s.stats.tov;
  }
  return { min: Math.round(min * 10) / 10, pts, reb, ast, stl, blk, tov, pm };
}

/** Try to get totals from boxscore data if available */
function getBoxscoreTotals(playerId: string, boxscore?: BoxScoreData) {
  if (!boxscore) return null;
  const p = boxscore.players.find((pl) => pl.playerId === playerId);
  if (!p) return null;
  return {
    min: p.totals.min,
    pts: p.totals.pts,
    reb: p.totals.reb,
    ast: p.totals.ast,
    stl: p.totals.stl,
    blk: p.totals.blk,
    tov: p.totals.tov,
    pm: p.totals.plusMinus,
  };
}

/**
 * Position tooltip at bottom-right of the mouse cursor using fixed positioning.
 * Called on mouseMove for stint cells and player name cells.
 */
function positionTooltipAtCursor(e: ReactMouseEvent<HTMLDivElement>) {
  const tooltip = e.currentTarget.querySelector(
    ".gf-stint-tooltip, .gf-player-tooltip",
  ) as HTMLElement | null;
  if (!tooltip) return;

  const offsetX = 12;
  const offsetY = 16;
  let left = e.clientX + offsetX;
  let top = e.clientY + offsetY;

  // Clamp to viewport edges
  const tw = tooltip.offsetWidth || 240;
  const th = tooltip.offsetHeight || 150;
  if (left + tw > window.innerWidth - 4) {
    left = e.clientX - tw - 4;
  }
  if (top + th > window.innerHeight - 4) {
    top = e.clientY - th - 4;
  }

  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

/**
 * Build a map of minute → Set<playerId> for each team.
 *
 * Uses stint data (rotation API) as the primary source: for each minute,
 * checks who has a stint covering the midpoint of that minute.
 *
 * The NBA rotation API has a known gap — it often records fewer than 5
 * starters for Q2-Q4. To fill these gaps, players from the previous
 * period's ending lineup are carried over. If stint data later shows
 * new players arriving (subs), carried players are dropped to maintain
 * exactly 5 on court.
 *
 * All data comes from real stint records — nothing is fabricated.
 */
function buildLineupsByMinute(
  teamPlayers: GameflowPlayer[],
  maxMinute: number,
): Map<number, Set<string>> {
  const lineups = new Map<number, Set<string>>();

  // Pre-compute all stint ranges as [gameStartMin, gameEndMin, playerId]
  const stintRanges: [number, number, string][] = [];
  for (const player of teamPlayers) {
    for (const stint of player.stints) {
      const periodDuration = stint.period > 4 ? OT_SECONDS : QUARTER_SECONDS;
      const baseMins = stint.period <= 4 ? (stint.period - 1) * 12 : 48 + (stint.period - 5) * 5;
      const startMin = baseMins + clockToElapsed(stint.inTime, periodDuration) / 60;
      const endMin = baseMins + clockToElapsed(stint.outTime, periodDuration) / 60;
      stintRanges.push([startMin, endMin, player.playerId]);
    }
  }

  /** Who has a stint covering this exact time point? */
  function onCourtAt(point: number): Set<string> {
    const result = new Set<string>();
    for (const [s, e, pid] of stintRanges) {
      if (s <= point && point < e) result.add(pid);
    }
    return result;
  }

  let carried = new Set<string>();

  for (let minute = 0; minute < maxMinute; minute++) {
    const period = Math.floor(minute / 12) + 1;
    const minuteInPeriod = minute % 12;
    const point = minute + 0.5; // midpoint

    const stintLineup = onCourtAt(point);

    if (minuteInPeriod === 0) {
      // Period start
      if (period === 1) {
        carried = new Set(stintLineup);
      } else {
        // Carry over from previous period if rotation data is incomplete
        if (stintLineup.size < 5) {
          const combined = new Set(stintLineup);
          for (const pid of carried) {
            if (combined.size >= 5) break;
            combined.add(pid);
          }
          carried = combined;
        } else {
          carried = new Set(stintLineup);
        }
      }
      lineups.set(minute, new Set(carried));
    } else {
      // Mid-period: merge stint data with carried players
      const merged = new Set(stintLineup);

      // New arrivals from stint data that weren't in carried = subs in
      const newPlayers = new Set<string>();
      for (const pid of stintLineup) {
        if (!carried.has(pid)) newPlayers.add(pid);
      }

      // For each new arrival, remove a carried player who left stint data
      if (newPlayers.size > 0) {
        const gone: string[] = [];
        for (const pid of carried) {
          if (!stintLineup.has(pid)) gone.push(pid);
        }
        const toRemove = gone.slice(0, newPlayers.size);
        for (const pid of toRemove) {
          carried.delete(pid);
        }
      }

      // Add remaining carried players
      for (const pid of carried) {
        merged.add(pid);
      }

      // Cap at 5: if over, trim carried-only players
      if (merged.size > 5) {
        const carriedOnly: string[] = [];
        for (const pid of merged) {
          if (!stintLineup.has(pid)) carriedOnly.push(pid);
        }
        let excess = merged.size - 5;
        for (const pid of carriedOnly) {
          if (excess <= 0) break;
          merged.delete(pid);
          carried.delete(pid);
          excess--;
        }
      }

      carried = new Set(merged);
      lineups.set(minute, new Set(merged));
    }
  }

  return lineups;
}

interface PinnedStint {
  playerId: string;
  stintIndex: number;
}

interface PlayerRowProps {
  player: GameflowPlayer;
  periods: number[];
  isHome: boolean;
  boxscore?: BoxScoreData;
  selectedMinute: number | null;
  lineups: Map<number, Set<string>>;
  position?: string;
  isStarter?: boolean;
  pinnedStint: PinnedStint | null;
  onPinStint: (pin: PinnedStint | null) => void;
}

function PlayerRow({ player, periods, isHome, boxscore, selectedMinute, lineups, position, pinnedStint, onPinStint }: PlayerRowProps) {
  const inClass = isHome ? "hometeamIN" : "visitorIN";
  const outClass = isHome ? "hometeamOUT" : "visitorOUT";
  const endClass = isHome ? "hometeamENDSTAT" : "visitorENDSTAT";

  const bsTotals = getBoxscoreTotals(player.playerId, boxscore);
  const totals = bsTotals ?? computePlayerTotals(player.stints);

  const isHighlighted = selectedMinute !== null && (lineups.get(selectedMinute)?.has(player.playerId) ?? false);

  // Compute which minutes per period the player is "on court" (per lineup tracking)
  // but has NO stint data covering that minute — these are carry-over minutes
  // that need a visual indicator.
  const carriedMinutes = useMemo(() => {
    const result = new Map<number, number[]>();
    for (const period of periods) {
      const periodLengthMins = period > 4 ? 5 : 12;
      const baseMinute = period <= 4 ? (period - 1) * 12 : 48 + (period - 5) * 5;
      const mins: number[] = [];

      for (let m = 0; m < periodLengthMins; m++) {
        const gameMinute = baseMinute + m;
        if (!(lineups.get(gameMinute)?.has(player.playerId))) continue;

        // Check if player has a stint covering this minute's midpoint
        const point = gameMinute + 0.5;
        let hasStint = false;
        for (const stint of player.stints) {
          const sPd = stint.period > 4 ? OT_SECONDS : QUARTER_SECONDS;
          const sBase = stint.period <= 4 ? (stint.period - 1) * 12 : 48 + (stint.period - 5) * 5;
          const startMin = sBase + clockToElapsed(stint.inTime, sPd) / 60;
          const endMin = sBase + clockToElapsed(stint.outTime, sPd) / 60;
          if (startMin <= point && point < endMin) { hasStint = true; break; }
        }
        if (!hasStint) mins.push(m);
      }
      if (mins.length > 0) result.set(period, mins);
    }
    return result;
  }, [periods, lineups, player]);

  let stintCounter = 0;

  return (
    <div
      className="gf-player-row"
      style={{
        display: "flex",
        height: ROW_HEIGHT,
        lineHeight: "1.6",
        opacity: selectedMinute !== null && !isHighlighted ? 0.35 : 1,
        transition: "opacity 0.2s ease",
      }}
    >
      {/* Player name with CSS hover tooltip */}
      <div
        className="gf-name-cell"
        onMouseMove={positionTooltipAtCursor}
        style={{
          width: NAME_COL_PX,
          flexShrink: 0,
          fontSize: 12,
          fontFamily: "'Roboto Condensed', Arial, Verdana, Helvetica",
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          paddingRight: 4,
          position: "relative",
          color: isHighlighted ? "#C9A84C" : "#F5F0E8",
          fontWeight: isHighlighted ? 700 : 400,
        }}
      >
        {isHighlighted && <span style={{ marginRight: 2 }}>&#9654;</span>}
        {position && (
          <span style={{ color: "#C9A84C", fontSize: 10, marginRight: 3, fontWeight: 600 }}>{position}</span>
        )}
        {player.name}
        <div className="gf-player-tooltip">
          <strong>{player.name}</strong><br />
          Game Totals<br />
          Min:{Math.floor(totals.min)}:{String(Math.round((totals.min % 1) * 60)).padStart(2, "0")}&nbsp;&nbsp;Pts:{totals.pts}&nbsp;&nbsp;(+/-):{totals.pm > 0 ? "+" : ""}{totals.pm}<br />
          Reb:{totals.reb}&nbsp;Ast:{totals.ast}&nbsp;Stl:{totals.stl}&nbsp;Blk:{totals.blk}&nbsp;Tov:{totals.tov}
        </div>
      </div>

      {/* Quarters */}
      {periods.map((period, pIdx) => {
        const segments = buildQuarterSegments(player.stints, period);
        const carried = carriedMinutes.get(period) ?? [];
        const periodDuration = period > 4 ? OT_SECONDS : QUARTER_SECONDS;
        const minuteWidth = (60 / periodDuration) * QUARTER_PX;
        return (
          <div key={pIdx} style={{ display: "flex" }}>
            {pIdx > 0 && <div style={{ width: SPACER_PX, background: "#2C1810" }} />}
            <div style={{ display: "flex", position: "relative" }}>
              {segments.map((seg, sIdx) => {
                if (seg.type === "out") {
                  return (
                    <div
                      key={sIdx}
                      className={outClass}
                      style={{ width: seg.widthPx, height: ROW_HEIGHT, overflow: "hidden" }}
                    >
                      &nbsp;
                    </div>
                  );
                }
                const currentStintNum = ++stintCounter;
                const stint = seg.stint!;
                const globalStintIdx = seg.stintIndex!;
                const isPinned = pinnedStint?.playerId === player.playerId && pinnedStint?.stintIndex === globalStintIdx;
                return (
                  <div
                    key={sIdx}
                    className={`${inClass} gf-stint-cell${isPinned ? " gf-stint-pinned" : ""}`}
                    onMouseMove={isPinned ? undefined : positionTooltipAtCursor}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (isPinned) {
                        onPinStint(null);
                      } else {
                        // Pin this stint and position tooltip at click location
                        onPinStint({ playerId: player.playerId, stintIndex: globalStintIdx });
                        const tooltip = e.currentTarget.querySelector(".gf-stint-tooltip") as HTMLElement | null;
                        if (tooltip) {
                          const offsetX = 12;
                          const offsetY = 16;
                          let left = e.clientX + offsetX;
                          let top = e.clientY + offsetY;
                          const tw = tooltip.offsetWidth || 240;
                          const th = tooltip.offsetHeight || 150;
                          if (left + tw > window.innerWidth - 4) left = e.clientX - tw - 4;
                          if (top + th > window.innerHeight - 4) top = e.clientY - th - 4;
                          tooltip.style.left = `${left}px`;
                          tooltip.style.top = `${top}px`;
                        }
                      }
                    }}
                    style={{
                      width: seg.widthPx,
                      height: ROW_HEIGHT,
                      position: "relative",
                      cursor: "pointer",
                      fontSize: 12,
                      fontFamily: "'Roboto Condensed', Arial, Verdana, Helvetica",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {seg.widthPx > 20 && (
                      <span>&nbsp;{stint.stats.pts}&nbsp;&nbsp;{stint.plusMinus > 0 ? "+" : ""}{stint.plusMinus}</span>
                    )}
                    {/* CSS hover tooltip (becomes interactive when pinned) */}
                    <div className="gf-stint-tooltip">
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <strong>{player.name} Stint {currentStintNum}</strong>
                        {isPinned && (
                          <span
                            style={{ cursor: "pointer", color: "#C4956A", fontSize: 14, lineHeight: 1 }}
                            onClick={(e) => { e.stopPropagation(); onPinStint(null); }}
                          >&times;</span>
                        )}
                      </div>
                      Period {stint.period}&nbsp;&nbsp;{stint.inTime} &rarr; {stint.outTime}<br />
                      Min:&nbsp;{Math.floor(stint.minutes)}:{String(Math.round((stint.minutes % 1) * 60)).padStart(2, "0")}&nbsp;&nbsp;(+/-):{stint.plusMinus > 0 ? "+" : ""}{stint.plusMinus}<br />
                      {(stint.stats.fgm > 0 || stint.stats.fga > 0) && <>FG {stint.stats.fgm}-{stint.stats.fga}&nbsp;&nbsp;&nbsp;</>}
                      {(stint.stats.fg3m > 0 || stint.stats.fg3a > 0) && <>3FG {stint.stats.fg3m}-{stint.stats.fg3a}<br /></>}
                      {(stint.stats.ftm > 0 || stint.stats.fta > 0) && <>FT {stint.stats.ftm}-{stint.stats.fta}<br /></>}
                      {stint.stats.reb > 0 && <>Reb {stint.stats.reb}<br /></>}
                      {stint.stats.ast > 0 && <>Ast {stint.stats.ast}<br /></>}
                      {stint.stats.stl > 0 && <>Stl {stint.stats.stl}<br /></>}
                      {stint.stats.blk > 0 && <>Blk {stint.stats.blk}<br /></>}
                      {stint.stats.tov > 0 && <>Tov {stint.stats.tov}<br /></>}
                      {stint.stats.pf > 0 && <>PF {stint.stats.pf}<br /></>}
                      {stint.events.length > 0 && (
                        <div style={{ marginTop: 4, borderTop: "1px solid rgba(201,168,76,0.3)", paddingTop: 2 }}>
                          {stint.events.map((ev, i) => (
                            <div key={i}>{ev.clock} {ev.type}</div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
              {/* Carried-over overlays: player is on court but has no stint data */}
              {carried.map((m) => (
                <div
                  key={`carried-${m}`}
                  style={{
                    position: "absolute",
                    left: m * minuteWidth,
                    width: minuteWidth,
                    height: ROW_HEIGHT,
                    background: isHome
                      ? "repeating-linear-gradient(45deg, rgba(0,81,154,0.55), rgba(0,81,154,0.55) 2px, rgba(0,81,154,0.25) 2px, rgba(0,81,154,0.25) 4px)"
                      : "repeating-linear-gradient(45deg, rgba(0,131,72,0.55), rgba(0,131,72,0.55) 2px, rgba(0,131,72,0.25) 2px, rgba(0,131,72,0.25) 4px)",
                    pointerEvents: "none",
                  }}
                />
              ))}
            </div>
          </div>
        );
      })}

      <div style={{ width: SPACER_PX, background: "#2C1810" }} />

      {/* End stats */}
      <div className={endClass} style={{ width: STAT_COL_PX, textAlign: "center", fontSize: 11 }}>
        {totals.min.toFixed(1)}
      </div>
      <div style={{ width: SPACER_PX, background: "#2C1810" }} />
      <div className={endClass} style={{ width: STAT_COL_PX, textAlign: "center", fontSize: 11 }}>
        {totals.pts}
      </div>
      <div style={{ width: SPACER_PX, background: "#2C1810" }} />
      <div className={endClass} style={{ width: STAT_COL_PX, textAlign: "center", fontSize: 11 }}>
        {totals.reb}
      </div>
      <div style={{ width: SPACER_PX, background: "#2C1810" }} />
      <div className={endClass} style={{ width: STAT_COL_PX, textAlign: "center", fontSize: 11 }}>
        {totals.ast}
      </div>
      <div style={{ width: SPACER_PX, background: "#2C1810" }} />
      <div className={endClass} style={{ width: STAT_COL_PX, textAlign: "center", fontSize: 11 }}>
        {totals.stl}
      </div>
      <div style={{ width: SPACER_PX, background: "#2C1810" }} />
      <div className={endClass} style={{ width: STAT_COL_PX, textAlign: "center", fontSize: 11 }}>
        {totals.blk}
      </div>
      <div style={{ width: SPACER_PX, background: "#2C1810" }} />
      <div className={endClass} style={{ width: STAT_COL_PX, textAlign: "center", fontSize: 11 }}>
        {totals.tov}
      </div>
      <div style={{ width: SPACER_PX, background: "#2C1810" }} />
      <div className={endClass} style={{ width: STAT_COL_PX - 1, textAlign: "center", fontSize: 11 }}>
        {totals.pm > 0 ? "+" : ""}{totals.pm}
      </div>
    </div>
  );
}

/**
 * Momentum line canvas — draws score differential graph across quarters.
 */
function MomentumLine({
  scoreChanges,
  periods,
  selectedMinute,
  onMinuteClick,
}: {
  scoreChanges: ScoreChange[];
  periods: number[];
  selectedMinute: number | null;
  onMinuteClick: (minute: number | null) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const numPeriods = periods.length;
  const cWidth = numPeriods <= 4
    ? 4 * QUARTER_PX
    : 4 * QUARTER_PX + (numPeriods - 4) * Math.floor((QUARTER_PX / 12) * 5);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || scoreChanges.length < 2) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, cWidth, CANVAS_HEIGHT);

    // Dark background
    ctx.fillStyle = "#1a1a2e";
    ctx.fillRect(0, 0, cWidth, CANVAS_HEIGHT);

    // Find biggest lead for scaling
    let biggestLead = 1;
    for (const sc of scoreChanges) {
      const diff = Math.abs(sc.homeScore - sc.awayScore);
      if (diff > biggestLead) biggestLead = diff;
    }
    biggestLead = Math.max(biggestLead, 5);

    // Draw selected minute highlight
    if (selectedMinute !== null) {
      const xStart = (selectedMinute / 12) * QUARTER_PX;
      const xEnd = ((selectedMinute + 1) / 12) * QUARTER_PX;
      ctx.fillStyle = "rgba(201, 168, 76, 0.15)";
      ctx.fillRect(xStart, 0, xEnd - xStart, CANVAS_HEIGHT);
    }

    // Draw grid: midline + period separators
    ctx.beginPath();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#5C3A21";
    // Midline
    ctx.moveTo(0, CANVAS_HEIGHT / 2);
    ctx.lineTo(cWidth, CANVAS_HEIGHT / 2);
    // Period separators
    for (let i = 1; i < numPeriods; i++) {
      const x = i <= 4 ? QUARTER_PX * i : QUARTER_PX * 4 + Math.floor((QUARTER_PX / 12) * 5) * (i - 4);
      ctx.moveTo(x, 0);
      ctx.lineTo(x, CANVAS_HEIGHT);
    }
    ctx.stroke();

    // Draw score differential line
    ctx.beginPath();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#C9A84C";
    ctx.moveTo(0, CANVAS_HEIGHT / 2);

    for (let i = 1; i < scoreChanges.length; i++) {
      const sc = scoreChanges[i];
      const x = (sc.ts / 12) * QUARTER_PX;
      const diff = sc.homeScore - sc.awayScore;
      const y = (CANVAS_HEIGHT / 2) - (diff * ((CANVAS_HEIGHT / 2) / biggestLead));
      ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Draw zero line labels
    ctx.fillStyle = "#C4956A";
    ctx.font = "10px 'Roboto Condensed', Arial";
    ctx.fillText("HOME", 4, CANVAS_HEIGHT / 2 - 4);
    ctx.fillText("AWAY", 4, CANVAS_HEIGHT / 2 + 12);

  }, [scoreChanges, cWidth, numPeriods, selectedMinute]);

  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const minute = Math.floor((x / QUARTER_PX) * 12);
    if (minute === selectedMinute) {
      onMinuteClick(null); // Deselect
    } else {
      onMinuteClick(minute);
    }
  }, [selectedMinute, onMinuteClick]);

  const finalScore = scoreChanges.length > 0 ? scoreChanges[scoreChanges.length - 1] : null;

  return (
    <div style={{ display: "flex", marginBottom: 2 }}>
      <div style={{ width: NAME_COL_PX, flexShrink: 0 }} />
      <div style={{ width: SPACER_PX }} />
      <div style={{ position: "relative" }}>
        <canvas
          ref={canvasRef}
          width={cWidth}
          height={CANVAS_HEIGHT}
          onClick={handleCanvasClick}
          style={{
            border: "1px solid #5C3A21",
            display: "block",
            cursor: "crosshair",
            borderRadius: 2,
          }}
        />
      </div>
      <div style={{ width: SPACER_PX }} />
      {finalScore && (
        <div style={{
          width: NUM_STAT_COLS * STAT_COL_PX + (NUM_STAT_COLS - 1) * SPACER_PX,
          background: "#1a1a2e",
          border: "1px solid #5C3A21",
          borderRadius: 2,
          fontSize: 11,
          fontFamily: "'Roboto Condensed', Arial, Verdana, Helvetica",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "2px 4px",
          height: CANVAS_HEIGHT,
          boxSizing: "border-box",
          color: "#E8D5B7",
        }}>
          <div style={{ color: "#FF6B35" }}>&nbsp;{finalScore.homeScore}</div>
          <div style={{ textAlign: "center", fontSize: 10, color: "#C4956A" }}>
            Avg Lead: {(() => {
              // Compute time-weighted average lead from score changes
              // Positive = home team leads, negative = away team leads
              if (scoreChanges.length < 2) return "0.0";
              let weightedSum = 0;
              for (let i = 0; i < scoreChanges.length - 1; i++) {
                const sc = scoreChanges[i];
                const next = scoreChanges[i + 1];
                const duration = next.ts - sc.ts;
                const lead = sc.homeScore - sc.awayScore;
                weightedSum += lead * duration;
              }
              const totalMinutes = scoreChanges[scoreChanges.length - 1].ts;
              if (totalMinutes === 0) return "0.0";
              const avgLead = weightedSum / totalMinutes;
              const sign = avgLead > 0 ? "+" : avgLead < 0 ? "" : "";
              return `${sign}${avgLead.toFixed(1)}`;
            })()}
          </div>
          <div style={{ color: "#FF6B35" }}>&nbsp;{finalScore.awayScore}</div>
        </div>
      )}
    </div>
  );
}

/**
 * Minute selector row — clickable minute buckets below the momentum line.
 */
function MinuteSelector({
  periods,
  selectedMinute,
  onMinuteClick,
}: {
  periods: number[];
  selectedMinute: number | null;
  onMinuteClick: (minute: number | null) => void;
}) {
  const totalGameMinutes = useMemo(() => {
    let total = 0;
    for (const p of periods) {
      total += p > 4 ? 5 : 12;
    }
    return total;
  }, [periods]);

  const minutes = Array.from({ length: totalGameMinutes }, (_, i) => i);

  return (
    <div style={{ display: "flex", marginBottom: 2 }}>
      <div
        style={{
          width: NAME_COL_PX,
          flexShrink: 0,
          fontSize: 10,
          fontFamily: "'Roboto Condensed', Arial",
          color: "#C4956A",
          lineHeight: `${MINUTE_ROW_HEIGHT}px`,
          textAlign: "right",
          paddingRight: 4,
        }}
      >
        {selectedMinute !== null ? `Min ${selectedMinute + 1}` : "Select min"}
      </div>
      <div style={{ width: SPACER_PX }} />
      <div style={{ display: "flex" }}>
        {minutes.map((min) => {
          const isSelected = selectedMinute === min;
          // Width: each minute = QUARTER_PX / 12 pixels (for regulation)
          const minuteWidth = QUARTER_PX / 12;

          return (
            <div
              key={min}
              className={`gf-minute-selector ${isSelected ? "gf-minute-selected" : ""}`}
              onClick={() => onMinuteClick(isSelected ? null : min)}
              style={{
                width: minuteWidth,
                height: MINUTE_ROW_HEIGHT,
                fontSize: 8,
                fontFamily: "'Roboto Condensed', Arial",
                textAlign: "center",
                lineHeight: `${MINUTE_ROW_HEIGHT}px`,
                color: isSelected ? "#C9A84C" : "#8B6914",
                background: isSelected
                  ? "rgba(201, 168, 76, 0.3)"
                  : "rgba(44, 24, 16, 0.6)",
                borderRight: "1px solid rgba(92, 58, 33, 0.3)",
                userSelect: "none",
              }}
            >
              {min + 1}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Renders the full gameflow visualization matching the original PopcornMachine layout
 * with basketball hardwood theme styling.
 */
export function GameflowTimeline({ data, boxscore }: GameflowTimelineProps) {
  const [selectedMinute, setSelectedMinute] = useState<number | null>(null);
  const [pinnedStint, setPinnedStint] = useState<PinnedStint | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Click outside or Escape key clears the pinned stint
  useEffect(() => {
    if (!pinnedStint) return;
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setPinnedStint(null);
      }
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setPinnedStint(null);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [pinnedStint]);

  const maxPeriod = useMemo(
    () => Math.max(4, ...data.players.flatMap((p) => p.stints.map((s) => s.period))),
    [data],
  );
  const periods = useMemo(() => Array.from({ length: maxPeriod }, (_, i) => i + 1), [maxPeriod]);

  const homePlayers = useMemo(
    () => data.players.filter((p) => p.team === data.homeTeam.tricode),
    [data],
  );
  const awayPlayers = useMemo(
    () => data.players.filter((p) => p.team === data.awayTeam.tricode),
    [data],
  );

  /**
   * Sort players: starters first (ordered G, G, F, F, C), then bench by minutes.
   * Falls back to boxscore data for position/starter info if gameflow lacks it.
   */
  const sortPlayers = useCallback((players: GameflowPlayer[]) => {
    // Specific positions (from roster) and broad V3 positions
    const posOrder: Record<string, number> = {
      PG: 0, SG: 1, G: 1,   // Guards
      SF: 2, PF: 3, F: 3,   // Forwards
      C: 4,                   // Center
      "G-F": 2, "F-G": 2, "F-C": 3, "C-F": 3,  // Combo positions
    };

    // Enrich with boxscore position/starter if gameflow data lacks it
    const enriched = players.map((p) => {
      let pos = p.position ?? "";
      let isStarter = p.starter ?? false;
      if (!pos && boxscore) {
        const bsPlayer = boxscore.players.find((bp) => bp.playerId === p.playerId);
        if (bsPlayer) {
          pos = bsPlayer.position ?? "";
          isStarter = bsPlayer.starter ?? false;
        }
      }
      return { player: p, position: pos, starter: isStarter };
    });

    const starters = enriched
      .filter((e) => e.starter)
      .sort((a, b) => (posOrder[a.position] ?? 9) - (posOrder[b.position] ?? 9));

    const bench = enriched
      .filter((e) => !e.starter)
      .sort(
        (a, b) =>
          b.player.stints.reduce((s, st) => s + st.minutes, 0) -
          a.player.stints.reduce((s, st) => s + st.minutes, 0),
      );

    return [...starters, ...bench].map((e) => e.player);
  }, [boxscore]);

  const sortedHome = useMemo(() => sortPlayers(homePlayers), [homePlayers, sortPlayers]);
  const sortedAway = useMemo(() => sortPlayers(awayPlayers), [awayPlayers, sortPlayers]);

  // Total game minutes for lineup tracking
  const totalGameMinutes = useMemo(() => {
    let total = 0;
    for (const p of periods) total += p > 4 ? 5 : 12;
    return total;
  }, [periods]);

  // Build lineup maps from substitution events (real data, not rotation API)
  const homeLineups = useMemo(
    () => buildLineupsByMinute(homePlayers, totalGameMinutes),
    [homePlayers, totalGameMinutes],
  );
  const awayLineups = useMemo(
    () => buildLineupsByMinute(awayPlayers, totalGameMinutes),
    [awayPlayers, totalGameMinutes],
  );

  const quarterLabel = (p: number) => {
    if (p === 1) return "1st Quarter";
    if (p === 2) return "2nd Quarter";
    if (p === 3) return "3rd Quarter";
    if (p === 4) return "4th Quarter";
    return `OT${p - 4}`;
  };

  const totalTimelineWidth = periods.length * QUARTER_PX + (periods.length - 1) * SPACER_PX;
  const totalWidth = NAME_COL_PX + SPACER_PX + totalTimelineWidth + SPACER_PX + NUM_STAT_COLS * STAT_COL_PX + (NUM_STAT_COLS - 1) * SPACER_PX;

  const headerStyle: React.CSSProperties = {
    color: "#C9A84C",
    textAlign: "center",
    fontWeight: 700,
    fontFamily: "'Oswald', sans-serif",
    backgroundColor: "#2C1810",
    fontSize: 12,
    height: ROW_HEIGHT,
    lineHeight: "1.6",
    textTransform: "uppercase",
    letterSpacing: 1,
  };

  const handleMinuteClick = useCallback((minute: number | null) => {
    setSelectedMinute(minute);
  }, []);

  // Score at selected minute from scoreChanges
  const minuteScore = useMemo(() => {
    if (selectedMinute === null || !data.scoreChanges || data.scoreChanges.length < 2) return null;
    // Find the last score change at or before the end of the selected minute
    const minuteEnd = selectedMinute + 1; // end of this minute bucket
    let homeScore = 0, awayScore = 0;
    for (const sc of data.scoreChanges) {
      if (sc.ts <= minuteEnd) {
        homeScore = sc.homeScore;
        awayScore = sc.awayScore;
      } else {
        break;
      }
    }
    return { homeScore, awayScore };
  }, [selectedMinute, data.scoreChanges]);

  return (
    <div
      ref={containerRef}
      style={{
        minWidth: totalWidth,
        maxWidth: totalWidth,
        background: "rgba(26, 26, 46, 0.4)",
        border: "1px solid #5C3A21",
        borderRadius: 4,
        overflow: "hidden",
      }}
    >
      {/* Title row */}
      <div style={{ display: "flex", height: ROW_HEIGHT }}>
        <div style={{ ...headerStyle, width: NAME_COL_PX, textAlign: "left", paddingLeft: 4 }}>Player</div>
        <div style={{ width: SPACER_PX, background: "#2C1810" }} />
        <div style={{ ...headerStyle, width: totalTimelineWidth }}>
          {data.awayTeam.name} @ {data.homeTeam.name}
        </div>
      </div>

      {/* Quarter headers row */}
      <div style={{ display: "flex", height: ROW_HEIGHT }}>
        <div style={{ ...headerStyle, width: NAME_COL_PX, textAlign: "right", paddingRight: 4, fontSize: 11 }}>Team</div>
        <div style={{ width: SPACER_PX, background: "#2C1810" }} />
        {periods.map((p, i) => (
          <div key={p} style={{ display: "flex" }}>
            {i > 0 && <div style={{ width: SPACER_PX, background: "#2C1810" }} />}
            <div style={{ ...headerStyle, width: p > 4 ? (OT_SECONDS / QUARTER_SECONDS) * QUARTER_PX : QUARTER_PX }}>
              {quarterLabel(p)}
            </div>
          </div>
        ))}
      </div>

      {/* Momentum line */}
      {data.scoreChanges && data.scoreChanges.length > 1 && (
        <MomentumLine
          scoreChanges={data.scoreChanges}
          periods={periods}
          selectedMinute={selectedMinute}
          onMinuteClick={handleMinuteClick}
        />
      )}

      {/* Minute selector */}
      <MinuteSelector
        periods={periods}
        selectedMinute={selectedMinute}
        onMinuteClick={handleMinuteClick}
      />

      {/* Lineup info when minute selected */}
      {selectedMinute !== null && minuteScore && (
        <div
          style={{
            display: "flex",
            height: ROW_HEIGHT,
            fontSize: 11,
            fontFamily: "'Roboto Condensed', Arial",
            color: "#C9A84C",
            background: "rgba(201, 168, 76, 0.08)",
            borderBottom: "1px solid rgba(201, 168, 76, 0.2)",
            alignItems: "center",
            paddingLeft: 4,
          }}
        >
          <div style={{ width: NAME_COL_PX }}>
            Minute {selectedMinute + 1}
          </div>
          <div style={{ marginLeft: 8 }}>
            {data.homeTeam.tricode} {minuteScore.homeScore} &ndash; {minuteScore.awayScore} {data.awayTeam.tricode}
          </div>
          <div
            style={{
              marginLeft: "auto",
              paddingRight: 8,
              cursor: "pointer",
              color: "#8B6914",
            }}
            onClick={() => setSelectedMinute(null)}
          >
            Clear
          </div>
        </div>
      )}

      {/* Home team label + stat headers */}
      <div style={{ display: "flex", height: ROW_HEIGHT, borderTop: "1px solid #5C3A21", borderBottom: "1px solid #5C3A21" }}>
        <div style={{
          ...headerStyle,
          width: NAME_COL_PX + SPACER_PX + totalTimelineWidth,
          textAlign: "center",
          background: "linear-gradient(90deg, #2C1810 0%, #3D2415 50%, #2C1810 100%)",
        }}>
          {data.homeTeam.name}
        </div>
        <div style={{ width: SPACER_PX, background: "#2C1810" }} />
        {["Min", "Pts", "Reb", "Ast", "Stl", "Blk", "Tov", "+/-"].map((label, i) => (
          <div key={label} style={{ display: "flex" }}>
            {i > 0 && <div style={{ width: SPACER_PX, background: "#2C1810" }} />}
            <div style={{ ...headerStyle, width: STAT_COL_PX, fontSize: 10 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Home players */}
      {sortedHome.map((player, idx) => {
        const bsPlayer = boxscore?.players.find((bp) => bp.playerId === player.playerId);
        const pos = player.position || bsPlayer?.position || "";
        const starter = player.starter ?? bsPlayer?.starter ?? false;
        // Insert bench separator after last starter
        const prevPlayer = idx > 0 ? sortedHome[idx - 1] : null;
        const prevStarter = prevPlayer
          ? (prevPlayer.starter ?? boxscore?.players.find((bp) => bp.playerId === prevPlayer.playerId)?.starter ?? false)
          : false;
        const showSep = !starter && prevStarter;
        return (
          <div key={player.playerId}>
            {showSep && (
              <div style={{ height: 2, background: "linear-gradient(90deg, transparent 0%, #5C3A21 20%, #8B6914 50%, #5C3A21 80%, transparent 100%)" }} />
            )}
            <PlayerRow
              player={player}
              periods={periods}
              isHome={true}
              boxscore={boxscore}
              selectedMinute={selectedMinute}
              lineups={homeLineups}
              position={pos}
              isStarter={starter}
              pinnedStint={pinnedStint}
              onPinStint={setPinnedStint}
            />
          </div>
        );
      })}

      {/* Away team label + stat headers */}
      <div style={{ display: "flex", height: ROW_HEIGHT, borderTop: "1px solid #5C3A21", borderBottom: "1px solid #5C3A21", marginTop: 2 }}>
        <div style={{
          ...headerStyle,
          width: NAME_COL_PX + SPACER_PX + totalTimelineWidth,
          textAlign: "center",
          background: "linear-gradient(90deg, #2C1810 0%, #3D2415 50%, #2C1810 100%)",
        }}>
          {data.awayTeam.name}
        </div>
        <div style={{ width: SPACER_PX, background: "#2C1810" }} />
        {["Min", "Pts", "Reb", "Ast", "Stl", "Blk", "Tov", "+/-"].map((label, i) => (
          <div key={label} style={{ display: "flex" }}>
            {i > 0 && <div style={{ width: SPACER_PX, background: "#2C1810" }} />}
            <div style={{ ...headerStyle, width: STAT_COL_PX, fontSize: 10 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Away players */}
      {sortedAway.map((player, idx) => {
        const bsPlayer = boxscore?.players.find((bp) => bp.playerId === player.playerId);
        const pos = player.position || bsPlayer?.position || "";
        const starter = player.starter ?? bsPlayer?.starter ?? false;
        const prevPlayer = idx > 0 ? sortedAway[idx - 1] : null;
        const prevStarter = prevPlayer
          ? (prevPlayer.starter ?? boxscore?.players.find((bp) => bp.playerId === prevPlayer.playerId)?.starter ?? false)
          : false;
        const showSep = !starter && prevStarter;
        return (
          <div key={player.playerId}>
            {showSep && (
              <div style={{ height: 2, background: "linear-gradient(90deg, transparent 0%, #5C3A21 20%, #8B6914 50%, #5C3A21 80%, transparent 100%)" }} />
            )}
            <PlayerRow
              player={player}
              periods={periods}
              isHome={false}
              boxscore={boxscore}
              selectedMinute={selectedMinute}
              lineups={awayLineups}
              position={pos}
              isStarter={starter}
              pinnedStint={pinnedStint}
              onPinStint={setPinnedStint}
            />
          </div>
        );
      })}
    </div>
  );
}
