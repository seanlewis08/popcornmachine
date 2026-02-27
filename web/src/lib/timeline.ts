/**
 * Timeline utility functions for converting game time to pixel coordinates
 * Used for gameflow visualization timeline layout
 */

export const QUARTER_DURATION_SECONDS = 720; // 12 minutes
export const OT_DURATION_SECONDS = 300; // 5 minutes
export const TOTAL_REGULATION_SECONDS = 2880; // 48 minutes (4 quarters)

/**
 * Convert a period number and clock string to absolute seconds from game start
 *
 * Clock format: "MM:SS" (e.g., "12:00", "10:30")
 * Period 1 clock "12:00" = 0 seconds (game start)
 * Period 1 clock "0:00" = 720 seconds (end of Q1)
 * Period 2 clock "12:00" = 720 seconds (start of Q2)
 * Period 2 clock "0:00" = 1440 seconds (end of Q2)
 * Period 5 (OT1) clock "5:00" = 2880 seconds (start of OT1)
 * Period 5 (OT1) clock "0:00" = 3180 seconds (end of OT1)
 * etc.
 */
export function clockToSeconds(period: number, clock: string): number {
  const [minutesStr, secondsStr] = clock.split(":");
  const minutes = parseInt(minutesStr, 10);
  const seconds = parseInt(secondsStr, 10);

  // Determine if this is a regular period or overtime
  const isOT = period > 4;
  const periodDuration = isOT ? OT_DURATION_SECONDS : QUARTER_DURATION_SECONDS;

  // Convert clock time (counting down from max to 0) to elapsed seconds in period
  const elapsedInPeriod = periodDuration - (minutes * 60 + seconds);

  // Calculate start seconds for this period
  let startSeconds = 0;
  if (isOT) {
    // For overtime: start after regulation + all previous OT periods
    startSeconds = TOTAL_REGULATION_SECONDS + (period - 5) * OT_DURATION_SECONDS;
  } else {
    // For regular quarters: start after all previous quarters
    startSeconds = (period - 1) * QUARTER_DURATION_SECONDS;
  }

  return startSeconds + elapsedInPeriod;
}

/**
 * Convert absolute seconds to pixel X position within timeline
 * @param seconds - Absolute seconds from game start
 * @param totalWidth - Total width of timeline in pixels
 * @param totalSeconds - Total game length in seconds
 * @returns X position in pixels
 */
export function secondsToPixelX(
  seconds: number,
  totalWidth: number,
  totalSeconds: number
): number {
  return (seconds / totalSeconds) * totalWidth;
}

export interface QuarterBoundary {
  period: number;
  startSeconds: number;
  endSeconds: number;
}

/**
 * Calculate start and end second boundaries for each quarter/OT period
 * @param numPeriods - Total number of periods (4 for regulation, 5+ for OT)
 * @returns Array of quarter boundaries
 */
export function getQuarterBoundaries(numPeriods: number): QuarterBoundary[] {
  const boundaries: QuarterBoundary[] = [];

  for (let period = 1; period <= numPeriods; period++) {
    const isOT = period > 4;
    const duration = isOT ? OT_DURATION_SECONDS : QUARTER_DURATION_SECONDS;

    let startSeconds = 0;
    if (isOT) {
      startSeconds = TOTAL_REGULATION_SECONDS + (period - 5) * OT_DURATION_SECONDS;
    } else {
      startSeconds = (period - 1) * QUARTER_DURATION_SECONDS;
    }

    boundaries.push({
      period,
      startSeconds,
      endSeconds: startSeconds + duration,
    });
  }

  return boundaries;
}

export interface StintPixelRange {
  x: number;
  width: number;
}

/**
 * Convert stint in/out clock times to pixel position and width
 * @param inTime - In clock time (e.g., "12:00")
 * @param outTime - Out clock time (e.g., "1:54")
 * @param period - Period number
 * @param totalWidth - Total timeline width in pixels
 * @param totalSeconds - Total game length in seconds
 * @returns Object with x position and width in pixels
 */
export function getStintPixelRange(
  inTime: string,
  outTime: string,
  period: number,
  totalWidth: number,
  totalSeconds: number
): StintPixelRange {
  const inSeconds = clockToSeconds(period, inTime);
  const outSeconds = clockToSeconds(period, outTime);

  const x = secondsToPixelX(inSeconds, totalWidth, totalSeconds);
  const width = secondsToPixelX(
    outSeconds - inSeconds,
    totalWidth,
    totalSeconds
  );

  return { x, width };
}
