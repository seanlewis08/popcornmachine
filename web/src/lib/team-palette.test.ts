import { describe, it, expect } from "vitest";
import {
  buildTeamPalette,
  colorDistance,
  relativeLuminance,
  TEAM_COLOR_CATALOG,
  MIN_TEAM_DISTANCE,
  type TeamColorCatalog,
} from "./team-palette";

const SITE_BACKGROUND = "#2C1810";

const catalog: TeamColorCatalog = {
  RED: { name: "Reds", colors: ["#CE1141", "#000000", "#C4CED4"] },
  ALSO_RED: { name: "Also Reds", colors: ["#CE1141", "#000000"] },
  BLACK: { name: "Blacks", colors: ["#000000", "#FFFFFF"] },
  YELLOW: { name: "Yellows", colors: ["#FDB927", "#552583"] },
  NAVY: { name: "Navies", colors: ["#1D428A", "#FEC524"] },
};

describe("colorDistance", () => {
  it("is zero for identical colors and symmetric", () => {
    expect(colorDistance("#CE1141", "#ce1141")).toBe(0);
    expect(colorDistance("#000000", "#FFFFFF")).toBeCloseTo(colorDistance("#FFFFFF", "#000000"));
  });

  it("black to white is the maximum", () => {
    expect(colorDistance("#000000", "#FFFFFF")).toBeCloseTo(Math.sqrt(3 * 255 * 255));
  });
});

describe("relativeLuminance", () => {
  it("orders black < navy < yellow < white", () => {
    const l = (hex: string) => relativeLuminance(hex);
    expect(l("#000000")).toBeLessThan(l("#0E2240"));
    expect(l("#0E2240")).toBeLessThan(l("#FDB927"));
    expect(l("#FDB927")).toBeLessThan(l("#FFFFFF"));
  });
});

describe("buildTeamPalette", () => {
  it("home team gets its primary when it reads against the background", () => {
    const p = buildTeamPalette({ home: "RED", away: "YELLOW", catalog });
    expect(p.home.onCourt).toBe("#CE1141");
    expect(p.away.onCourt).toBe("#FDB927");
  });

  it("away team falls back down its palette when its primary matches home", () => {
    // RED is away here; its third color (silver) is the first legible, distinct one.
    const p = buildTeamPalette({ home: "ALSO_RED", away: "RED", catalog });
    expect(p.home.onCourt).toBe("#CE1141");
    expect(p.away.onCourt).toBe("#C4CED4");
  });

  it("away team gets a lighter tint of its own hue when its palette has no usable alternative", () => {
    // ALSO_RED is red + black; black is invisible on the page, so nothing in
    // the palette works. Expect a lighter red: distinct, still red-dominant.
    const p = buildTeamPalette({ home: "RED", away: "ALSO_RED", catalog });
    expect(p.away.onCourt).not.toBe("#CE1141");
    expect(colorDistance(p.home.onCourt, p.away.onCourt)).toBeGreaterThanOrEqual(MIN_TEAM_DISTANCE);
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(p.away.onCourt.slice(i, i + 2), 16));
    expect(r).toBeGreaterThan(g);
    expect(r).toBeGreaterThan(b);
    expect(relativeLuminance(p.away.onCourt)).toBeGreaterThan(relativeLuminance("#CE1141"));
  });

  it("skips colors that vanish against the site background", () => {
    // Black on the dark-brown page is invisible; white is the next option.
    const p = buildTeamPalette({ home: "BLACK", away: "YELLOW", catalog });
    expect(p.home.onCourt).toBe("#FFFFFF");
  });

  it("uses dark text on light on-court colors and white text on dark ones", () => {
    const p = buildTeamPalette({ home: "YELLOW", away: "NAVY", catalog });
    expect(relativeLuminance(p.home.text)).toBeLessThan(0.2);
    expect(p.away.text).toBe("#FFFFFF");
  });

  it("bench color is a darker, same-family version of the on-court color", () => {
    const p = buildTeamPalette({ home: "RED", away: "YELLOW", catalog });
    expect(p.home.bench).not.toBe(p.home.onCourt);
    expect(relativeLuminance(p.home.bench)).toBeLessThan(relativeLuminance(p.home.onCourt));
    // Closer to the on-court color than to an unrelated hue.
    expect(colorDistance(p.home.bench, p.home.onCourt)).toBeLessThan(colorDistance(p.home.bench, "#FDB927"));
  });

  it("unknown tricodes get the legacy fallback colors without throwing", () => {
    const p = buildTeamPalette({ home: "???", away: "XXX", catalog });
    expect(p.home.onCourt).toBe("#00519A");
    expect(p.away.onCourt).toBe("#008348");
  });

  it("is deterministic", () => {
    const a = buildTeamPalette({ home: "RED", away: "ALSO_RED", catalog });
    const b = buildTeamPalette({ home: "RED", away: "ALSO_RED", catalog });
    expect(a).toEqual(b);
  });
});

describe("real catalog", () => {
  const tricodes = Object.keys(TEAM_COLOR_CATALOG);

  it("has all 30 teams with at least one color each", () => {
    expect(tricodes).toHaveLength(30);
    for (const t of tricodes) {
      expect(TEAM_COLOR_CATALOG[t]?.colors.length ?? 0).toBeGreaterThan(0);
    }
  });

  it("every matchup yields two on-court colors that are distinct from each other and the background", () => {
    for (const home of tricodes) {
      for (const away of tricodes) {
        if (home === away) continue;
        const p = buildTeamPalette({ home, away });
        expect(colorDistance(p.home.onCourt, p.away.onCourt), `${home} vs ${away}`).toBeGreaterThanOrEqual(
          MIN_TEAM_DISTANCE,
        );
        expect(colorDistance(p.home.onCourt, SITE_BACKGROUND), `${home} bg`).toBeGreaterThanOrEqual(MIN_TEAM_DISTANCE);
        expect(colorDistance(p.away.onCourt, SITE_BACKGROUND), `${away} bg`).toBeGreaterThanOrEqual(MIN_TEAM_DISTANCE);
      }
    }
  });
});
