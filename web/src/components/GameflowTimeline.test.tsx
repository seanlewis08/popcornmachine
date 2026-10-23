import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { GameflowTimeline } from "./GameflowTimeline";
import type { GameflowData } from "../types/api";

describe("GameflowTimeline", () => {
  const mockData: GameflowData = {
    gameId: "0022500001",
    homeTeam: { tricode: "DET", name: "Detroit Pistons" },
    awayTeam: { tricode: "BOS", name: "Boston Celtics" },
    players: [
      {
        playerId: "1234",
        name: "Player A",
        team: "DET",
        stints: [
          {
            period: 1,
            inTime: "12:00",
            outTime: "6:00",
            minutes: 6.0,
            plusMinus: 2,
            stats: {
              fgm: 2, fga: 4, fg3m: 1, fg3a: 2, ftm: 1, fta: 1,
              pts: 6, ast: 1, reb: 2, stl: 0, blk: 0, tov: 0, pf: 0,
            },
            events: [],
          },
          {
            period: 4,
            inTime: "12:00",
            outTime: "6:00",
            minutes: 6.0,
            plusMinus: 1,
            stats: {
              fgm: 1, fga: 2, fg3m: 0, fg3a: 0, ftm: 0, fta: 0,
              pts: 2, ast: 0, reb: 1, stl: 0, blk: 0, tov: 0, pf: 0,
            },
            events: [],
          },
        ],
      },
      {
        playerId: "5678",
        name: "Player B",
        team: "BOS",
        stints: [
          {
            period: 1,
            inTime: "12:00",
            outTime: "8:00",
            minutes: 4.0,
            plusMinus: -1,
            stats: {
              fgm: 1, fga: 3, fg3m: 0, fg3a: 1, ftm: 0, fta: 0,
              pts: 2, ast: 0, reb: 1, stl: 0, blk: 0, tov: 1, pf: 1,
            },
            events: [],
          },
        ],
      },
    ],
  };

  it("renders player names", () => {
    render(<GameflowTimeline data={mockData} />);
    // Names appear in the row label and again in the hover tooltip.
    expect(screen.getAllByText("Player A").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Player B").length).toBeGreaterThan(0);
  });

  it("shows team section headers", () => {
    render(<GameflowTimeline data={mockData} />);
    // Home and away team names appear in header and section labels
    expect(screen.getAllByText(/Detroit Pistons/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Boston Celtics/).length).toBeGreaterThan(0);
  });

  it("shows quarter headers", () => {
    render(<GameflowTimeline data={mockData} />);
    expect(screen.getByText("1st Quarter")).toBeInTheDocument();
    expect(screen.getByText("2nd Quarter")).toBeInTheDocument();
    expect(screen.getByText("3rd Quarter")).toBeInTheDocument();
    expect(screen.getByText("4th Quarter")).toBeInTheDocument();
  });

  it("shows totals column headers", () => {
    render(<GameflowTimeline data={mockData} />);
    // Each team block has its own header row, so headers appear twice.
    for (const label of ["Min", "Pts", "+/-"]) {
      expect(screen.getAllByText(label).length, label).toBe(2);
    }
  });

  it("renders IN segments with team-specific CSS classes", () => {
    const { container } = render(<GameflowTimeline data={mockData} />);
    // Home team uses hometeamIN class
    const homeIn = container.querySelectorAll(".hometeamIN");
    expect(homeIn.length).toBeGreaterThan(0);
    // Away team uses visitorIN class
    const awayIn = container.querySelectorAll(".visitorIN");
    expect(awayIn.length).toBeGreaterThan(0);
  });

  it("exposes the matchup's team colors as CSS variables on the timeline root", () => {
    const { container } = render(<GameflowTimeline data={mockData} />);
    const root = container.firstElementChild;
    expect(root).not.toBeNull();
    const style = (root as HTMLElement).style;
    // DET home → Pistons red; BOS away → Celtics green (see teamColors.json).
    expect(style.getPropertyValue("--home-on-court")).toBe("#C8102E");
    expect(style.getPropertyValue("--away-on-court")).toBe("#007A33");
    for (const name of ["--home-bench", "--home-text", "--away-bench", "--away-text"]) {
      expect(style.getPropertyValue(name), name).toMatch(/^#[0-9A-F]{6}$/);
    }
  });

  it("draws overtime periods at 90px (5 min × 18px), matching the header and chart", () => {
    const otData: GameflowData = {
      ...mockData,
      players: [
        {
          ...mockData.players[0],
          stints: [
            ...mockData.players[0].stints,
            { ...mockData.players[0].stints[0], period: 5, inTime: "5:00", outTime: "0:00", minutes: 5 },
          ],
        },
      ],
    };
    const { container } = render(<GameflowTimeline data={otData} />);
    const otHeader = screen.getByText("OT1") as HTMLElement;
    expect(otHeader.style.width).toBe("90px");
    // The player's full-OT stint is one IN segment spanning the whole 90px block.
    const inSegments = Array.from(container.querySelectorAll(".hometeamIN")) as HTMLElement[];
    expect(inSegments.map((el) => el.style.width)).toContain("90px");
    expect(inSegments.map((el) => el.style.width)).not.toContain("216px");
  });

  it("renders OUT segments with team-specific CSS classes", () => {
    const { container } = render(<GameflowTimeline data={mockData} />);
    const homeOut = container.querySelectorAll(".hometeamOUT");
    expect(homeOut.length).toBeGreaterThan(0);
    const awayOut = container.querySelectorAll(".visitorOUT");
    expect(awayOut.length).toBeGreaterThan(0);
  });

  it("renders one end-stat cell per column per player", () => {
    const { container } = render(<GameflowTimeline data={mockData} />);
    const endStats = container.querySelectorAll(".hometeamENDSTAT, .visitorENDSTAT");
    // 8 stat columns (Min Pts Reb Ast Stl Blk Tov +/-) × 2 players
    expect(endStats.length).toBe(16);
  });

  it("displays stint points inside IN segments", () => {
    const { container } = render(<GameflowTimeline data={mockData} />);
    // Player A stint 1 has pts=6, plusMinus=+2
    const homeInSegments = container.querySelectorAll(".hometeamIN");
    const texts = Array.from(homeInSegments).map((el) => el.textContent?.trim());
    // At least one segment should contain the points
    expect(texts.some((t) => t?.includes("6"))).toBe(true);
  });
});
