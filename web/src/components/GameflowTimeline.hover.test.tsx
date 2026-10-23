import { describe, it, expect } from "vitest";
import { render, fireEvent, screen } from "@testing-library/react";
import { GameflowTimeline } from "./GameflowTimeline";
import { minuteToRowX } from "../lib/timeline-geometry";
import type { GameflowData, GameflowStint } from "../types/api";

const NAME_COL_PX = 120;

function stint(period: number, inTime: string, outTime: string, minutes: number): GameflowStint {
  return {
    period,
    inTime,
    outTime,
    minutes,
    plusMinus: 0,
    stats: { fgm: 0, fga: 0, fg3m: 0, fg3a: 0, ftm: 0, fta: 0, pts: 0, ast: 0, reb: 0, stl: 0, blk: 0, tov: 0, pf: 0 },
    events: [],
  };
}

/**
 * Away team: B starts and leaves at the 8:00 mark of Q1 (minute 4);
 * C replaces B. So at minute 2 B is on and C is off; at minute 5.5 C is
 * on and B is off. Home: A plays the whole first quarter.
 */
const data: GameflowData = {
  gameId: "0022600001",
  homeTeam: { tricode: "DET", name: "Detroit Pistons" },
  awayTeam: { tricode: "BOS", name: "Boston Celtics" },
  players: [
    { playerId: "A", name: "Player A", team: "DET", stints: [stint(1, "12:00", "0:00", 12)] },
    { playerId: "B", name: "Player B", team: "BOS", stints: [stint(1, "12:00", "8:00", 4)] },
    { playerId: "C", name: "Player C", team: "BOS", stints: [stint(1, "8:00", "0:00", 8)] },
  ],
};

function rowOf(name: string): HTMLElement {
  // The visible name cell lives inside the .gf-player-row; the tooltip repeats
  // the name, so take the first match and walk up to the row.
  const el = screen.getAllByText(name)[0];
  const row = el.closest(".gf-player-row");
  if (!(row instanceof HTMLElement)) throw new Error(`no row for ${name}`);
  return row;
}

function hoverAtMinute(rows: HTMLElement, minute: number): void {
  // jsdom reports getBoundingClientRect() as all zeros, so clientX is the
  // offset within the rows container.
  fireEvent.mouseMove(rows, { clientX: NAME_COL_PX + minuteToRowX(minute, 4), clientY: 10 });
}

describe("GameflowTimeline hover cursor", () => {
  it("shows a vertical cursor at the hovered minute, spanning the player rows", () => {
    render(<GameflowTimeline data={data} />);
    const rows = screen.getByTestId("gf-rows");

    expect(screen.queryByTestId("gf-hover-cursor")).toBeNull();
    hoverAtMinute(rows, 5.5);

    const cursor = screen.getByTestId("gf-hover-cursor");
    expect(cursor.style.left).toBe(`${NAME_COL_PX + minuteToRowX(5.5, 4)}px`);
    expect(cursor.style.pointerEvents).toBe("none");
  });

  it("dims players who are not on court at the hovered minute", () => {
    render(<GameflowTimeline data={data} />);
    const rows = screen.getByTestId("gf-rows");

    hoverAtMinute(rows, 5.5);
    expect(rowOf("Player A").style.opacity).toBe("1");
    expect(rowOf("Player B").style.opacity).toBe("0.35");
    expect(rowOf("Player C").style.opacity).toBe("1");

    hoverAtMinute(rows, 2);
    expect(rowOf("Player B").style.opacity).toBe("1");
    expect(rowOf("Player C").style.opacity).toBe("0.35");
  });

  it("leaving the rows removes the cursor and restores everyone", () => {
    render(<GameflowTimeline data={data} />);
    const rows = screen.getByTestId("gf-rows");

    hoverAtMinute(rows, 5.5);
    expect(rowOf("Player B").style.opacity).toBe("0.35");

    fireEvent.mouseLeave(rows);
    expect(screen.queryByTestId("gf-hover-cursor")).toBeNull();
    expect(rowOf("Player B").style.opacity).toBe("1");
  });

  it("hovering the name column (left of the timeline) shows no cursor", () => {
    render(<GameflowTimeline data={data} />);
    const rows = screen.getByTestId("gf-rows");

    fireEvent.mouseMove(rows, { clientX: 40, clientY: 10 });
    expect(screen.queryByTestId("gf-hover-cursor")).toBeNull();
    expect(rowOf("Player B").style.opacity).toBe("1");
  });

  it("a pinned minute wins: hover neither moves the highlight nor shows the cursor", () => {
    render(<GameflowTimeline data={data} />);
    const rows = screen.getByTestId("gf-rows");

    // Pin minute 2 (0-based bucket 1) via the minute selector; B on, C off.
    fireEvent.click(screen.getByTestId("gf-minute-2"));
    expect(screen.getByTestId("gf-pinned-band")).toBeInTheDocument();
    expect(rowOf("Player B").style.opacity).toBe("1");
    expect(rowOf("Player C").style.opacity).toBe("0.35");

    hoverAtMinute(rows, 5.5);
    expect(screen.queryByTestId("gf-hover-cursor")).toBeNull();
    expect(rowOf("Player B").style.opacity).toBe("1");
    expect(rowOf("Player C").style.opacity).toBe("0.35");

    // Unpin → hover takes over again.
    fireEvent.click(screen.getByTestId("gf-minute-2"));
    expect(screen.queryByTestId("gf-pinned-band")).toBeNull();
    hoverAtMinute(rows, 5.5);
    expect(screen.getByTestId("gf-hover-cursor")).toBeInTheDocument();
    expect(rowOf("Player B").style.opacity).toBe("0.35");
  });
});
