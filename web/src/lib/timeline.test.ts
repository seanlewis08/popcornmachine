import { describe, it, expect } from "vitest";
import {
  clockToSeconds,
  secondsToPixelX,
  getQuarterBoundaries,
  getStintPixelRange,
  QUARTER_DURATION_SECONDS,
  OT_DURATION_SECONDS,
  TOTAL_REGULATION_SECONDS,
} from "./timeline";

describe("timeline utilities", () => {
  describe("clockToSeconds", () => {
    it("converts Q1 start (12:00) to 0 seconds", () => {
      expect(clockToSeconds(1, "12:00")).toBe(0);
    });

    it("converts Q1 end (0:00) to 720 seconds", () => {
      expect(clockToSeconds(1, "0:00")).toBe(QUARTER_DURATION_SECONDS);
    });

    it("converts Q1 middle (6:00) to 360 seconds", () => {
      expect(clockToSeconds(1, "6:00")).toBe(360);
    });

    it("converts Q2 start (12:00) to 720 seconds", () => {
      expect(clockToSeconds(2, "12:00")).toBe(QUARTER_DURATION_SECONDS);
    });

    it("converts Q2 end (0:00) to 1440 seconds", () => {
      expect(clockToSeconds(2, "0:00")).toBe(2 * QUARTER_DURATION_SECONDS);
    });

    it("converts Q3 start (12:00) to 1440 seconds", () => {
      expect(clockToSeconds(3, "12:00")).toBe(2 * QUARTER_DURATION_SECONDS);
    });

    it("converts Q3 end (0:00) to 2160 seconds", () => {
      expect(clockToSeconds(3, "0:00")).toBe(3 * QUARTER_DURATION_SECONDS);
    });

    it("converts Q4 start (12:00) to 2160 seconds", () => {
      expect(clockToSeconds(4, "12:00")).toBe(3 * QUARTER_DURATION_SECONDS);
    });

    it("converts Q4 end (0:00) to 2880 seconds", () => {
      expect(clockToSeconds(4, "0:00")).toBe(TOTAL_REGULATION_SECONDS);
    });

    it("converts OT start (5:00) to 2880 seconds", () => {
      // OT period 5 starts after regulation (2880 seconds)
      // Clock "5:00" means no time has elapsed in OT yet
      expect(clockToSeconds(5, "5:00")).toBe(TOTAL_REGULATION_SECONDS);
    });

    it("converts OT end (0:00) to 3180 seconds", () => {
      // OT period 5 clock "0:00" means all 5 minutes of OT have elapsed
      expect(clockToSeconds(5, "0:00")).toBe(
        TOTAL_REGULATION_SECONDS + OT_DURATION_SECONDS
      );
    });

    it("converts OT2 start (5:00) to 3180 seconds", () => {
      // Second OT period starts at end of first OT
      expect(clockToSeconds(6, "5:00")).toBe(
        TOTAL_REGULATION_SECONDS + OT_DURATION_SECONDS
      );
    });

    it("converts arbitrary clock times correctly", () => {
      // Q1 10:30
      expect(clockToSeconds(1, "10:30")).toBe(90); // 1:30 elapsed
      // Q2 8:45
      expect(clockToSeconds(2, "8:45")).toBe(720 + 195); // 3:15 elapsed in Q2
    });

    it("handles malformed time inputs gracefully with NaN", () => {
      // Malformed inputs should result in NaN behavior from parseInt
      // This documents current behavior - real code should validate inputs
      const result = clockToSeconds(1, "xx:xx");
      expect(Number.isNaN(result)).toBe(true);
    });
  });

  describe("secondsToPixelX", () => {
    it("converts seconds to pixel position proportionally", () => {
      const totalWidth = 1000;
      const totalSeconds = 2880; // 48 minutes

      // At halfway point in time, should be halfway across
      const pixelX = secondsToPixelX(1440, totalWidth, totalSeconds);
      expect(pixelX).toBe(500);
    });

    it("returns 0 for 0 seconds", () => {
      expect(secondsToPixelX(0, 1000, 2880)).toBe(0);
    });

    it("returns totalWidth for totalSeconds", () => {
      const totalWidth = 800;
      const totalSeconds = 2880;
      expect(secondsToPixelX(totalSeconds, totalWidth, totalSeconds)).toBe(
        totalWidth
      );
    });

    it("scales correctly with different widths", () => {
      const totalSeconds = 2880;
      const halfSeconds = 1440;

      const pixel800 = secondsToPixelX(halfSeconds, 800, totalSeconds);
      const pixel1600 = secondsToPixelX(halfSeconds, 1600, totalSeconds);

      expect(pixel1600).toBe(2 * pixel800);
    });

    it("handles fractional seconds", () => {
      const totalWidth = 1000;
      const totalSeconds = 2880;

      // Quarter way through
      const pixelX = secondsToPixelX(720, totalWidth, totalSeconds);
      expect(pixelX).toBeCloseTo(250, 1);
    });
  });

  describe("getQuarterBoundaries", () => {
    it("returns correct boundaries for 4-period game", () => {
      const boundaries = getQuarterBoundaries(4);

      expect(boundaries).toHaveLength(4);
      expect(boundaries[0]).toEqual({
        period: 1,
        startSeconds: 0,
        endSeconds: QUARTER_DURATION_SECONDS,
      });
      expect(boundaries[1]).toEqual({
        period: 2,
        startSeconds: QUARTER_DURATION_SECONDS,
        endSeconds: 2 * QUARTER_DURATION_SECONDS,
      });
      expect(boundaries[2]).toEqual({
        period: 3,
        startSeconds: 2 * QUARTER_DURATION_SECONDS,
        endSeconds: 3 * QUARTER_DURATION_SECONDS,
      });
      expect(boundaries[3]).toEqual({
        period: 4,
        startSeconds: 3 * QUARTER_DURATION_SECONDS,
        endSeconds: TOTAL_REGULATION_SECONDS,
      });
    });

    it("returns correct boundaries for 5-period game (1 OT)", () => {
      const boundaries = getQuarterBoundaries(5);

      expect(boundaries).toHaveLength(5);
      expect(boundaries[4]).toEqual({
        period: 5,
        startSeconds: TOTAL_REGULATION_SECONDS,
        endSeconds: TOTAL_REGULATION_SECONDS + OT_DURATION_SECONDS,
      });
    });

    it("returns correct boundaries for multiple OT periods", () => {
      const boundaries = getQuarterBoundaries(7);

      expect(boundaries).toHaveLength(7);
      // OT1 (Period 5)
      expect(boundaries[4]).toEqual({
        period: 5,
        startSeconds: TOTAL_REGULATION_SECONDS,
        endSeconds: TOTAL_REGULATION_SECONDS + OT_DURATION_SECONDS,
      });
      // OT2 (Period 6)
      expect(boundaries[5]).toEqual({
        period: 6,
        startSeconds: TOTAL_REGULATION_SECONDS + OT_DURATION_SECONDS,
        endSeconds: TOTAL_REGULATION_SECONDS + 2 * OT_DURATION_SECONDS,
      });
      // OT3 (Period 7)
      expect(boundaries[6]).toEqual({
        period: 7,
        startSeconds: TOTAL_REGULATION_SECONDS + 2 * OT_DURATION_SECONDS,
        endSeconds: TOTAL_REGULATION_SECONDS + 3 * OT_DURATION_SECONDS,
      });
    });

    it("has no gaps between consecutive periods", () => {
      const boundaries = getQuarterBoundaries(6);

      for (let i = 0; i < boundaries.length - 1; i++) {
        expect(boundaries[i + 1].startSeconds).toBe(boundaries[i].endSeconds);
      }
    });
  });

  describe("getStintPixelRange", () => {
    it("calculates pixel range for a stint within a quarter", () => {
      const totalWidth = 1000;
      const totalSeconds = 2880;

      // Stint from 12:00 to 6:00 in Q1 = 6 minutes = 360 seconds
      const range = getStintPixelRange("12:00", "6:00", 1, totalWidth, totalSeconds);

      expect(range.x).toBe(0); // Starts at beginning
      expect(range.width).toBeCloseTo(125, 1); // 360/2880 * 1000 = 125
    });

    it("calculates pixel range for a stint at quarter end", () => {
      const totalWidth = 1000;
      const totalSeconds = 2880;

      // Stint from 1:54 to 0:00 in Q1 = 114 seconds
      // 1:54 = 114 seconds on clock, so 606 seconds have elapsed (720 - 114)
      const range = getStintPixelRange(
        "1:54",
        "0:00",
        1,
        totalWidth,
        totalSeconds
      );

      expect(range.x).toBeCloseTo(210.4, 1); // 606 / 2880 * 1000 ≈ 210.4
      expect(range.width).toBeCloseTo(39.6, 1); // 114 / 2880 * 1000 ≈ 39.6
    });

    it("calculates pixel range for stint spanning multiple time values", () => {
      const totalWidth = 2880; // 1 pixel per second for easy verification
      const totalSeconds = 2880;

      // 10 minute stint starting at 12:00 of Q1
      const range = getStintPixelRange("12:00", "2:00", 1, totalWidth, totalSeconds);

      expect(range.x).toBe(0);
      expect(range.width).toBe(600); // 10 minutes = 600 seconds
    });

    it("calculates correct position for stints in different quarters", () => {
      const totalWidth = 2880;
      const totalSeconds = 2880;

      // Same clock time in different quarters should have different x positions
      const q1Range = getStintPixelRange("12:00", "6:00", 1, totalWidth, totalSeconds);
      const q2Range = getStintPixelRange("12:00", "6:00", 2, totalWidth, totalSeconds);

      expect(q2Range.x).toBe(q1Range.x + QUARTER_DURATION_SECONDS);
    });

    it("ensures stints in same game time align horizontally (AC3.4)", () => {
      const totalWidth = 1000;
      const totalSeconds = 2880;

      // Two stints ending at same clock time in same period
      // Should have same x + width = end position
      const stint1 = getStintPixelRange("12:00", "6:00", 1, totalWidth, totalSeconds);
      const stint2 = getStintPixelRange("9:00", "6:00", 1, totalWidth, totalSeconds);

      const stint1End = stint1.x + stint1.width;
      const stint2End = stint2.x + stint2.width;

      expect(stint1End).toBeCloseTo(stint2End, 1);
    });

    it("calculates non-overlapping ranges for consecutive stints", () => {
      const totalWidth = 1000;
      const totalSeconds = 2880;

      // Player 1: 12:00 to 6:00
      const stint1 = getStintPixelRange("12:00", "6:00", 1, totalWidth, totalSeconds);
      // Player 2: 6:00 to 0:00 (right after Player 1 ends)
      const stint2 = getStintPixelRange("6:00", "0:00", 1, totalWidth, totalSeconds);

      const stint1End = stint1.x + stint1.width;

      // Second stint should start where first ends
      expect(stint2.x).toBeCloseTo(stint1End, 1);
    });

    it("handles fractional pixel positions", () => {
      const totalWidth = 500;
      const totalSeconds = 2880;

      const range = getStintPixelRange("11:55", "11:50", 1, totalWidth, totalSeconds);

      // Should not throw and should return valid pixel values
      expect(typeof range.x).toBe("number");
      expect(typeof range.width).toBe("number");
      expect(range.x).toBeGreaterThanOrEqual(0);
      expect(range.width).toBeGreaterThan(0);
    });
  });

  describe("integration: timeline alignment across players (AC3.4)", () => {
    it("aligns stints at same game time across multiple players", () => {
      const totalWidth = 1000;
      const totalSeconds = 2880;

      // Three players, all subbed out at the same clock time
      const player1Stint = getStintPixelRange("12:00", "8:00", 1, totalWidth, totalSeconds);
      const player2Stint = getStintPixelRange("12:00", "8:00", 1, totalWidth, totalSeconds);
      const player3Stint = getStintPixelRange("10:00", "8:00", 1, totalWidth, totalSeconds);

      // Player 1 and 2 should have identical ranges (same times)
      expect(player1Stint.x).toEqual(player2Stint.x);
      expect(player1Stint.width).toEqual(player2Stint.width);

      // Player 3 starts later but ends at same time
      const player1End = player1Stint.x + player1Stint.width;
      const player3End = player3Stint.x + player3Stint.width;

      expect(player1End).toBeCloseTo(player3End, 1);
    });

    it("maintains consistent scaling across quarter boundaries", () => {
      const totalWidth = 2880;
      const totalSeconds = 2880;

      // End of Q1
      const q1End = getStintPixelRange("0:30", "0:00", 1, totalWidth, totalSeconds);
      // Beginning of Q2
      const q2Start = getStintPixelRange("12:00", "11:30", 2, totalWidth, totalSeconds);

      // Q1 ends at pixel 690, Q2 starts after that
      const q1EndPixel = q1End.x + q1End.width;
      expect(q1EndPixel).toBeCloseTo(720, 0);

      // Q2 start should be right after Q1 end
      expect(q2Start.x).toBeCloseTo(720, 0);
    });
  });
});
