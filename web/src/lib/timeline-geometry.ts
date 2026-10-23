// pattern: Functional Core
/**
 * Pixel ↔ game-minute conversions for the gameflow timeline.
 *
 * Every period is drawn at 18px per minute: 216px for a 12-minute quarter,
 * 90px for a 5-minute overtime. Two horizontal layouts share that scale:
 *
 * - "row" coordinates (player stint rows): periods are separated by a 1px
 *   spacer, so Q2 starts at x = 217, not 216.
 * - "chart" coordinates (momentum canvas, minute selector): periods are
 *   contiguous, so Q2 starts at x = 216.
 *
 * Minutes are elapsed game minutes: 0 at tip-off, 12 at the end of Q1,
 * 48 at the end of regulation, 53 at the end of OT1.
 */

export const MINUTE_PX = 18;
export const QUARTER_MINUTES = 12;
export const OT_MINUTES = 5;
export const REGULATION_PERIODS = 4;
export const QUARTER_PX = QUARTER_MINUTES * MINUTE_PX;
export const OT_PX = OT_MINUTES * MINUTE_PX;
export const SPACER_PX = 1;

export function periodMinutes(period: number): number {
  return period <= REGULATION_PERIODS ? QUARTER_MINUTES : OT_MINUTES;
}

export function periodWidthPx(period: number): number {
  return periodMinutes(period) * MINUTE_PX;
}

/** Elapsed game minute at which `period` (1-based) begins. */
export function periodStartMinute(period: number): number {
  if (period <= REGULATION_PERIODS) return (period - 1) * QUARTER_MINUTES;
  return REGULATION_PERIODS * QUARTER_MINUTES + (period - REGULATION_PERIODS - 1) * OT_MINUTES;
}

/** True when `minute` is the first minute of some period (0, 12, 24, 36, 48, 53, …). */
export function isPeriodStartMinute(minute: number): boolean {
  const regulation = REGULATION_PERIODS * QUARTER_MINUTES;
  if (minute < regulation) return minute % QUARTER_MINUTES === 0;
  return (minute - regulation) % OT_MINUTES === 0;
}

export function totalGameMinutes(numPeriods: number): number {
  return periodStartMinute(numPeriods) + periodMinutes(numPeriods);
}

export function totalChartWidthPx(numPeriods: number): number {
  return totalGameMinutes(numPeriods) * MINUTE_PX;
}

export function totalRowWidthPx(numPeriods: number): number {
  return totalChartWidthPx(numPeriods) + (numPeriods - 1) * SPACER_PX;
}

/** Row-layout x at which `period` begins (after its leading spacer). */
function rowPeriodOffsetPx(period: number): number {
  return periodStartMinute(period) * MINUTE_PX + (period - 1) * SPACER_PX;
}

function periodContaining(minute: number, numPeriods: number): number {
  for (let p = numPeriods; p >= 1; p--) {
    if (minute >= periodStartMinute(p)) return p;
  }
  return 1;
}

export function minuteToRowX(minute: number, numPeriods: number): number {
  const p = periodContaining(minute, numPeriods);
  return rowPeriodOffsetPx(p) + (minute - periodStartMinute(p)) * MINUTE_PX;
}

/**
 * Inverse of minuteToRowX. An x inside a spacer snaps to the start of the
 * following period. Returns null outside [0, totalRowWidthPx].
 */
export function rowXToMinute(x: number, numPeriods: number): number | null {
  if (x < 0 || x > totalRowWidthPx(numPeriods)) return null;
  for (let p = numPeriods; p >= 1; p--) {
    const offset = rowPeriodOffsetPx(p);
    if (x >= offset) return periodStartMinute(p) + (x - offset) / MINUTE_PX;
    // x lies in the spacer just before period p.
    if (x >= offset - SPACER_PX) return periodStartMinute(p);
  }
  return 0;
}

export function minuteToChartX(minute: number): number {
  return minute * MINUTE_PX;
}

export function chartXToMinute(x: number): number {
  return x / MINUTE_PX;
}

/** 0-based whole-minute bucket, clamped to the game's minutes. */
export function minuteBucket(minute: number, numPeriods: number): number {
  const last = totalGameMinutes(numPeriods) - 1;
  return Math.min(Math.max(Math.floor(minute), 0), last);
}
