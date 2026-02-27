import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
              fgm: 2,
              fga: 4,
              fg3m: 1,
              fg3a: 2,
              ftm: 1,
              fta: 1,
              pts: 6,
              ast: 1,
              reb: 2,
              stl: 0,
              blk: 0,
              tov: 0,
              pf: 0,
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
              fgm: 1,
              fga: 2,
              fg3m: 0,
              fg3a: 0,
              ftm: 0,
              fta: 0,
              pts: 2,
              ast: 0,
              reb: 1,
              stl: 0,
              blk: 0,
              tov: 0,
              pf: 0,
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
              fgm: 1,
              fga: 3,
              fg3m: 0,
              fg3a: 1,
              ftm: 0,
              fta: 0,
              pts: 2,
              ast: 0,
              reb: 1,
              stl: 0,
              blk: 0,
              tov: 1,
              pf: 1,
            },
            events: [],
          },
        ],
      },
    ],
  };

  it("renders the timeline with player lanes (AC3.1)", () => {
    render(<GameflowTimeline data={mockData} />);

    expect(screen.getByText("Player A")).toBeInTheDocument();
    expect(screen.getByText("Player B")).toBeInTheDocument();
  });

  it("groups players by team with team headers", () => {
    render(<GameflowTimeline data={mockData} />);

    // Should show team names as headers
    expect(screen.getByText(/detroit/i)).toBeInTheDocument();
    expect(screen.getByText(/boston/i)).toBeInTheDocument();
  });

  it("displays home team first, then away team", () => {
    const { container } = render(<GameflowTimeline data={mockData} />);

    const players = container.querySelectorAll("[data-testid='player-name']");
    expect(players[0]).toHaveTextContent("Player A"); // Home team player
    expect(players[1]).toHaveTextContent("Player B"); // Away team player
  });

  it("renders stint bars for each player (AC3.1)", () => {
    const { container } = render(<GameflowTimeline data={mockData} />);

    const stintBars = container.querySelectorAll("[data-testid='stint-bar']");
    expect(stintBars.length).toBe(3); // Player A has 2 stints, Player B has 1
  });

  it("applies different colors to stint bars based on team (AC3.2)", () => {
    const { container } = render(<GameflowTimeline data={mockData} />);

    const stintBars = container.querySelectorAll("[data-testid='stint-bar']");

    // Home team stints should be blue
    expect(stintBars[0]).toHaveClass("bg-blue-500");
    expect(stintBars[1]).toHaveClass("bg-blue-500");
    // Away team stint should be red
    expect(stintBars[2]).toHaveClass("bg-red-500");
  });

  it("shows quarter divider labels", () => {
    const { container } = render(<GameflowTimeline data={mockData} />);

    const quarterLabels = container.querySelectorAll("span");
    const labelText = Array.from(quarterLabels).map((el) => el.textContent);

    expect(labelText.some((text) => text?.includes("Q1"))).toBe(true);
    expect(labelText.some((text) => text?.includes("Q2"))).toBe(true);
    expect(labelText.some((text) => text?.includes("Q3"))).toBe(true);
    expect(labelText.some((text) => text?.includes("Q4"))).toBe(true);
  });

  it("stint bar is keyboard accessible with proper ARIA attributes", () => {
    const { container } = render(<GameflowTimeline data={mockData} />);

    const stintBar = container.querySelector("[data-testid='stint-bar']") as HTMLElement;
    expect(stintBar).toBeInTheDocument();

    // Verify keyboard accessibility: has role button and is focusable
    expect(stintBar).toHaveAttribute("role", "button");
    expect(stintBar).toHaveAttribute("tabIndex", "0");

    // Verify aria-label exists
    expect(stintBar).toHaveAttribute("aria-label");

    // Verify it has ARIA label with stint info
    const ariaLabel = stintBar.getAttribute("aria-label");
    expect(ariaLabel).toMatch(/Stint:/);
    expect(ariaLabel).toMatch(/minutes/);
  });

  it("handles multiple stints per player", () => {
    const dataMultiStints: GameflowData = {
      ...mockData,
      players: [
        {
          ...mockData.players[0],
          stints: [
            mockData.players[0].stints[0],
            {
              period: 2,
              inTime: "12:00",
              outTime: "10:00",
              minutes: 2.0,
              plusMinus: 1,
              stats: {
                fgm: 1,
                fga: 2,
                fg3m: 0,
                fg3a: 0,
                ftm: 0,
                fta: 0,
                pts: 2,
                ast: 0,
                reb: 1,
                stl: 0,
                blk: 0,
                tov: 0,
                pf: 0,
              },
              events: [],
            },
          ],
        },
        mockData.players[1],
      ],
    };

    const { container } = render(<GameflowTimeline data={dataMultiStints} />);

    // Should have 3 stint bars total (2 for first player, 1 for second)
    const stintBars = container.querySelectorAll("[data-testid='stint-bar']");
    expect(stintBars.length).toBe(3);
  });

  it("has vertical alignment guide for quarters (AC3.4)", () => {
    const { container } = render(<GameflowTimeline data={mockData} />);

    // Should have quarter boundary lines for alignment
    const quarterLines = container.querySelectorAll("[data-testid='quarter-boundary']");
    expect(quarterLines.length).toBeGreaterThan(0);
  });

  it("supports keyboard navigation - Tab to focus stint bars for keyboard accessibility", async () => {
    const user = userEvent.setup();
    const { container } = render(<GameflowTimeline data={mockData} />);

    // Get all stint bars
    const stintBars = container.querySelectorAll("[data-testid='stint-bar']");
    expect(stintBars.length).toBeGreaterThan(0);

    const firstStintBar = stintBars[0] as HTMLElement;

    // Initially, stint bar should not be focused
    expect(firstStintBar).not.toHaveFocus();

    // Tab to focus the stint bar
    await user.tab();

    // The stint bar should now be focused (Radix PopoverTrigger will handle keyboard)
    expect(firstStintBar).toHaveFocus();

    // Verify the focused stint bar has keyboard event handlers
    // by checking it has role="button" and tabIndex="0"
    expect(firstStintBar).toHaveAttribute("role", "button");
    expect(firstStintBar).toHaveAttribute("tabIndex", "0");
  });
});
