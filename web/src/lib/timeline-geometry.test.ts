import { describe, it, expect } from "vitest";
import {
  MINUTE_PX,
  QUARTER_PX,
  SPACER_PX,
  periodWidthPx,
  periodStartMinute,
  isPeriodStartMinute,
  totalGameMinutes,
  totalRowWidthPx,
  totalChartWidthPx,
  minuteToRowX,
  rowXToMinute,
  minuteToChartX,
  chartXToMinute,
  minuteBucket,
} from "./timeline-geometry";

describe("period sizing", () => {
  it("regulation quarters are 216px (12 min × 18px) and OT periods are 90px (5 min)", () => {
    expect(QUARTER_PX).toBe(12 * MINUTE_PX);
    expect(periodWidthPx(1)).toBe(216);
    expect(periodWidthPx(4)).toBe(216);
    expect(periodWidthPx(5)).toBe(90);
    expect(periodWidthPx(6)).toBe(90);
  });

  it("period start minutes", () => {
    expect(periodStartMinute(1)).toBe(0);
    expect(periodStartMinute(4)).toBe(36);
    expect(periodStartMinute(5)).toBe(48);
    expect(periodStartMinute(6)).toBe(53);
  });

  it("recognises period-start minutes, including overtime", () => {
    expect([0, 12, 24, 36, 48, 53, 58].every(isPeriodStartMinute)).toBe(true);
    expect([1, 11, 47, 49, 52, 55].some(isPeriodStartMinute)).toBe(false);
  });

  it("total minutes and widths", () => {
    expect(totalGameMinutes(4)).toBe(48);
    expect(totalGameMinutes(6)).toBe(58);
    // Player rows have a 1px spacer between periods; the chart does not.
    expect(totalRowWidthPx(4)).toBe(4 * 216 + 3 * SPACER_PX);
    expect(totalRowWidthPx(5)).toBe(4 * 216 + 90 + 4 * SPACER_PX);
    expect(totalChartWidthPx(5)).toBe(4 * 216 + 90);
  });
});

describe("row coordinates (player stint rows)", () => {
  it("minute → x accounts for spacers between periods", () => {
    expect(minuteToRowX(0, 4)).toBe(0);
    expect(minuteToRowX(12, 4)).toBe(216 + SPACER_PX); // start of Q2
    expect(minuteToRowX(36, 4)).toBe(3 * (216 + SPACER_PX)); // start of Q4
    expect(minuteToRowX(48, 5)).toBe(4 * (216 + SPACER_PX)); // start of OT1
    expect(minuteToRowX(50.5, 5)).toBe(4 * (216 + SPACER_PX) + 2.5 * MINUTE_PX);
  });

  it("x → minute is the inverse within a period", () => {
    for (const m of [0, 5.25, 11.99, 12, 23.5, 36, 47.9]) {
      expect(rowXToMinute(minuteToRowX(m, 4), 4)).toBeCloseTo(m, 6);
    }
    expect(rowXToMinute(minuteToRowX(52.5, 5), 5)).toBeCloseTo(52.5, 6);
  });

  it("x inside a spacer snaps to the start of the following period", () => {
    const spacerX = 216; // the 1px gap between Q1 and Q2 at x = 216
    expect(rowXToMinute(spacerX, 4)).toBe(12);
  });

  it("x outside the timeline is null", () => {
    expect(rowXToMinute(-1, 4)).toBeNull();
    expect(rowXToMinute(totalRowWidthPx(4) + 0.001, 4)).toBeNull();
  });

  it("x at the very end maps to the final minute, not past it", () => {
    expect(rowXToMinute(totalRowWidthPx(4), 4)).toBe(48);
  });
});

describe("chart coordinates (momentum canvas)", () => {
  it("is 18px per minute with no spacers, including OT", () => {
    expect(minuteToChartX(12)).toBe(216);
    expect(minuteToChartX(48)).toBe(864);
    expect(minuteToChartX(50)).toBe(864 + 2 * MINUTE_PX);
    expect(chartXToMinute(864 + 2 * MINUTE_PX)).toBe(50);
  });

  it("round-trips", () => {
    for (const m of [0, 7.3, 24, 47.5, 52]) {
      expect(chartXToMinute(minuteToChartX(m))).toBeCloseTo(m, 9);
    }
  });
});

describe("minuteBucket", () => {
  it("floors to the 0-based minute and clamps into the game", () => {
    expect(minuteBucket(0.2, 4)).toBe(0);
    expect(minuteBucket(11.99, 4)).toBe(11);
    expect(minuteBucket(47.5, 4)).toBe(47);
    expect(minuteBucket(48, 4)).toBe(47); // end of regulation → last bucket
    expect(minuteBucket(-3, 4)).toBe(0);
    expect(minuteBucket(57.9, 6)).toBe(57);
    expect(minuteBucket(99, 6)).toBe(57);
  });
});
