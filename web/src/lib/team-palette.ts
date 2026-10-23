// pattern: Functional Core
/**
 * Picks the on-court / bench / text colors for the two teams in a game.
 *
 * Rules, in order:
 * 1. A team's on-court color is the first entry in its palette that reads
 *    against the site background (dark brown).
 * 2. The away team additionally must be distinct from the home team's
 *    on-court color, so Bulls–Rockets (both #CE1141) don't collapse into
 *    one color. It walks down its palette until one qualifies.
 * 3. Bench color is the on-court color blended most of the way toward the
 *    background, so the row still reads as that team.
 * 4. Text is white unless the on-court color is light (Lakers gold,
 *    Warriors yellow), then near-black.
 *
 * Unknown tricodes get the colors the site used before team colors existed.
 */

import rawCatalog from "../data/teamColors.json";

export type TeamColorEntry = {
  readonly name: string;
  readonly colors: ReadonlyArray<string>;
};

export type TeamColorCatalog = Readonly<Record<string, TeamColorEntry>>;

export type TeamColors = {
  readonly onCourt: string;
  readonly bench: string;
  readonly text: string;
};

export type GamePalette = {
  readonly home: TeamColors;
  readonly away: TeamColors;
};

export type BuildTeamPaletteOptions = {
  readonly home: string;
  readonly away: string;
  readonly catalog?: TeamColorCatalog;
};

/** The page background the timeline sits on (see index.css). */
export const SITE_BACKGROUND = "#2C1810";

/**
 * Minimum RGB-space distance (0–441) between two colors for them to count
 * as distinct. 90 is roughly "clearly a different color" on a dark page;
 * every real matchup clears it (checked by the test suite).
 */
export const MIN_TEAM_DISTANCE = 90;

/** How far the bench color is blended from on-court toward the background. */
const BENCH_BLEND = 0.62;

const LEGACY_HOME_ON_COURT = "#00519A";
const LEGACY_AWAY_ON_COURT = "#008348";
const DARK_TEXT = "#1A1A1A";
const LIGHT_TEXT = "#FFFFFF";

/** Light-text threshold on relative luminance (0 black – 1 white). */
const LIGHT_LUMINANCE = 0.45;

type Rgb = readonly [number, number, number];

const HEX_PATTERN = /^#?([0-9a-f]{6})$/i;

function hexToRgb(hex: string): Rgb | null {
  const m = HEX_PATTERN.exec(hex.trim());
  if (m === null) return null;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff];
}

function rgbToHex(rgb: Rgb): string {
  return "#" + rgb.map((c) => Math.round(c).toString(16).padStart(2, "0")).join("").toUpperCase();
}

/** Euclidean distance in RGB space, 0 (identical) to ~441 (black ↔ white). */
export function colorDistance(a: string, b: string): number {
  const ra = hexToRgb(a);
  const rb = hexToRgb(b);
  if (ra === null || rb === null) return 0;
  const dr = ra[0] - rb[0];
  const dg = ra[1] - rb[1];
  const db = ra[2] - rb[2];
  return Math.sqrt(dr * dr + dg * dg + db * db);
}

/** WCAG relative luminance, 0 (black) to 1 (white). */
export function relativeLuminance(hex: string): number {
  const rgb = hexToRgb(hex);
  if (rgb === null) return 0;
  const lin = (c: number): number => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2]);
}

/** Linear blend from `from` toward `to` by `t` in [0, 1]. */
function mixHex(from: string, to: string, t: number): string {
  const a = hexToRgb(from);
  const b = hexToRgb(to);
  if (a === null || b === null) return from;
  return rgbToHex([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]);
}

function readsAgainstBackground(hex: string): boolean {
  return colorDistance(hex, SITE_BACKGROUND) >= MIN_TEAM_DISTANCE;
}

function teamColorsFor(onCourt: string): TeamColors {
  return {
    onCourt,
    bench: mixHex(onCourt, SITE_BACKGROUND, BENCH_BLEND),
    text: relativeLuminance(onCourt) >= LIGHT_LUMINANCE ? DARK_TEXT : LIGHT_TEXT,
  };
}

/** Tints tried, in order, when a palette has no distinct legible entry. */
const TINT_STEPS: ReadonlyArray<number> = [0.3, 0.45, 0.6];

function isDistinctFrom(color: string, avoid: ReadonlyArray<string>): boolean {
  return avoid.every((o) => colorDistance(color, o) >= MIN_TEAM_DISTANCE);
}

/**
 * First palette entry that reads against the background and is at least
 * MIN_TEAM_DISTANCE from every color in `avoid`.
 *
 * Some palettes are just "primary + black" (Bulls, Blazers), so when the
 * primary clashes there is nothing else to pick. Then we lighten the first
 * legible color step by step until it is distinct — still recognisably the
 * team's hue, but clearly a different bar. Last resort: the first legible
 * entry, then the first entry at all.
 */
function pickOnCourt(colors: ReadonlyArray<string>, avoid: ReadonlyArray<string>): string | null {
  const usable = colors.filter((c) => hexToRgb(c) !== null);
  if (usable.length === 0) return null;
  const legible = usable.filter(readsAgainstBackground);
  const distinct = legible.find((c) => isDistinctFrom(c, avoid));
  if (distinct !== undefined) return distinct;

  const base = legible[0] ?? null;
  if (base !== null) {
    for (const t of TINT_STEPS) {
      // Lighten first (keeps dark primaries vivid); darken when the base is
      // already light, since lightening silver only drifts toward white.
      for (const target of ["#FFFFFF", SITE_BACKGROUND]) {
        const tint = mixHex(base, target, t);
        if (readsAgainstBackground(tint) && isDistinctFrom(tint, avoid)) return tint;
      }
    }
  }
  return base ?? usable[0] ?? null;
}

function isTeamColorEntry(value: unknown): value is TeamColorEntry {
  return (
    typeof value === "object" &&
    value !== null &&
    "name" in value &&
    typeof value.name === "string" &&
    "colors" in value &&
    Array.isArray(value.colors) &&
    value.colors.every((c) => typeof c === "string")
  );
}

/** Validate the bundled JSON at load time; malformed entries are dropped, not trusted. */
function loadCatalog(raw: unknown): TeamColorCatalog {
  if (typeof raw !== "object" || raw === null) return {};
  const out: Record<string, TeamColorEntry> = {};
  for (const [tricode, entry] of Object.entries(raw)) {
    if (isTeamColorEntry(entry)) out[tricode] = { name: entry.name, colors: entry.colors };
  }
  return out;
}

export const TEAM_COLOR_CATALOG: TeamColorCatalog = loadCatalog(rawCatalog);

/**
 * The CSS custom properties index.css reads (`.hometeamIN` etc.). Set these
 * on the timeline root so every descendant picks up the matchup's colors.
 */
export function paletteToCssVars(palette: GamePalette): Readonly<Record<string, string>> {
  return {
    "--home-on-court": palette.home.onCourt,
    "--home-bench": palette.home.bench,
    "--home-text": palette.home.text,
    "--away-on-court": palette.away.onCourt,
    "--away-bench": palette.away.bench,
    "--away-text": palette.away.text,
  };
}

export function buildTeamPalette(options: BuildTeamPaletteOptions): GamePalette {
  const { home, away, catalog = TEAM_COLOR_CATALOG } = options;

  const homeEntry = catalog[home] ?? null;
  const homeOnCourt = (homeEntry && pickOnCourt(homeEntry.colors, [])) ?? LEGACY_HOME_ON_COURT;

  const awayEntry = catalog[away] ?? null;
  const awayOnCourt = (awayEntry && pickOnCourt(awayEntry.colors, [homeOnCourt])) ?? LEGACY_AWAY_ON_COURT;

  return { home: teamColorsFor(homeOnCourt), away: teamColorsFor(awayOnCourt) };
}
