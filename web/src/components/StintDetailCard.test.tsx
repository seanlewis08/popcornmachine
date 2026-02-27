import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StintDetailCard } from "./StintDetailCard";
import type { GameflowStint } from "../types/api";

describe("StintDetailCard", () => {
  const mockStint: GameflowStint = {
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
      pf: 1,
    },
    events: [
      { clock: "10:30", type: "2pt", description: "Made 2PT" },
      { clock: "8:15", type: "fta", description: "Made FTA" },
      { clock: "7:45", type: "reb", description: "Rebound" },
    ],
  };

  it("renders stint period and time information", () => {
    render(<StintDetailCard stint={mockStint} />);

    expect(screen.getByText(/period 1/i)).toBeInTheDocument();
    expect(screen.getByText(/12:00.*6:00/)).toBeInTheDocument();
  });

  it("displays minutes played and plus-minus", () => {
    const { container } = render(<StintDetailCard stint={mockStint} />);

    expect(screen.getByText("Minutes")).toBeInTheDocument();
    expect(container.textContent).toContain("6.0");
    expect(screen.getByText(/\+2/)).toBeInTheDocument();
  });

  it("displays all stat categories with values", () => {
    render(<StintDetailCard stint={mockStint} />);

    // Check stats are displayed
    expect(screen.getByText("PTS")).toBeInTheDocument();
    expect(screen.getByText("AST")).toBeInTheDocument();
    expect(screen.getByText("REB")).toBeInTheDocument();
    expect(screen.getByText("STL")).toBeInTheDocument();
    expect(screen.getByText("BLK")).toBeInTheDocument();
  });

  it("displays shooting splits", () => {
    render(<StintDetailCard stint={mockStint} />);

    expect(screen.getByText(/2-4/)).toBeInTheDocument(); // FG
    expect(screen.getByText(/1-2/)).toBeInTheDocument(); // 3PT
    expect(screen.getByText(/1-1/)).toBeInTheDocument(); // FT
  });

  it("displays play-by-play events in chronological order", () => {
    render(<StintDetailCard stint={mockStint} />);

    const events = screen.getAllByRole("listitem");
    expect(events).toHaveLength(3);
    expect(events[0]).toHaveTextContent("10:30");
    expect(events[1]).toHaveTextContent("8:15");
    expect(events[2]).toHaveTextContent("7:45");
  });

  it("shows event description for each play-by-play entry", () => {
    render(<StintDetailCard stint={mockStint} />);

    expect(screen.getByText("Made 2PT")).toBeInTheDocument();
    expect(screen.getByText("Made FTA")).toBeInTheDocument();
    expect(screen.getByText("Rebound")).toBeInTheDocument();
  });

  it("handles stints with no events", () => {
    const stintNoEvents: GameflowStint = {
      ...mockStint,
      events: [],
    };

    const { container } = render(<StintDetailCard stint={stintNoEvents} />);

    expect(screen.getByText("Period 1")).toBeInTheDocument();
    expect(container.textContent).toContain("6.0");
  });

  it("handles stints with zero stats", () => {
    const stintZeroStats: GameflowStint = {
      ...mockStint,
      plusMinus: 0,
      stats: {
        fgm: 0,
        fga: 0,
        fg3m: 0,
        fg3a: 0,
        ftm: 0,
        fta: 0,
        pts: 0,
        ast: 0,
        reb: 0,
        stl: 0,
        blk: 0,
        tov: 0,
        pf: 0,
      },
    };

    render(<StintDetailCard stint={stintZeroStats} />);

    expect(screen.getByText("+0")).toBeInTheDocument();
  });
});
