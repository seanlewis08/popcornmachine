import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { render } from "@testing-library/react";
import { StintBreakdown } from "@/components/StintBreakdown";
import { StintData } from "@/types/api";

const createFixtureStint = (
  period: number,
  inTime: string,
  outTime: string,
  minutes: number
): StintData => ({
  period,
  inTime,
  outTime,
  minutes,
  plusMinus: -4,
  fgm: 0,
  fga: 4,
  fg3m: 0,
  fg3a: 1,
  ftm: 3,
  fta: 4,
  oreb: 1,
  reb: 1,
  ast: 3,
  blk: 0,
  stl: 0,
  tov: 0,
  pf: 1,
  pts: 3,
});

describe("StintBreakdown", () => {
  it("renders stint data table with all columns", () => {
    const stints = [createFixtureStint(1, "12:00", "1:54", 10.1)];

    render(<StintBreakdown stints={stints} />);

    // Check for column headers
    expect(screen.getByText("Period")).toBeInTheDocument();
    expect(screen.getByText("In")).toBeInTheDocument();
    expect(screen.getByText("Out")).toBeInTheDocument();
    expect(screen.getByText("Min")).toBeInTheDocument();
    expect(screen.getByText("FG")).toBeInTheDocument();
    expect(screen.getByText("3PT")).toBeInTheDocument();
    expect(screen.getByText("FT")).toBeInTheDocument();
    expect(screen.getByText("OREB")).toBeInTheDocument();
    expect(screen.getByText("REB")).toBeInTheDocument();
    expect(screen.getByText("AST")).toBeInTheDocument();
    expect(screen.getByText("BLK")).toBeInTheDocument();
    expect(screen.getByText("STL")).toBeInTheDocument();
    expect(screen.getByText("TO")).toBeInTheDocument();
    expect(screen.getByText("PF")).toBeInTheDocument();
    expect(screen.getByText("PTS")).toBeInTheDocument();
    expect(screen.getByText("+/-")).toBeInTheDocument();
  });

  it("renders stint data with correct values", () => {
    const stints = [createFixtureStint(1, "12:00", "1:54", 10.1)];

    const { container } = render(<StintBreakdown stints={stints} />);

    // Check times
    expect(screen.getByText("12:00")).toBeInTheDocument();
    expect(screen.getByText("1:54")).toBeInTheDocument();
    // Check stats
    expect(screen.getByText("0-4")).toBeInTheDocument(); // FG
    expect(screen.getByText("0-1")).toBeInTheDocument(); // 3PT
    expect(screen.getByText("3-4")).toBeInTheDocument(); // FT
    // Check for period value in table
    const table = container.querySelector("table");
    expect(table?.textContent).toContain("1");
  });

  it("formats minutes correctly (M:SS)", () => {
    const stints = [createFixtureStint(1, "12:00", "1:54", 10.1)];

    render(<StintBreakdown stints={stints} />);

    // 10.1 minutes should be 10:06
    expect(screen.getByText("10:06")).toBeInTheDocument();
  });

  it("renders multiple stints", () => {
    const stints = [
      createFixtureStint(1, "12:00", "1:54", 10.1),
      createFixtureStint(2, "12:00", "3:00", 9.0),
    ];

    render(<StintBreakdown stints={stints} />);

    // Check both periods appear
    const periodCells = screen.getAllByText(/^1$|^2$/);
    expect(periodCells.length).toBeGreaterThanOrEqual(2);
  });

  it("renders with muted background styling", () => {
    const stints = [createFixtureStint(1, "12:00", "1:54", 10.1)];

    const { container } = render(<StintBreakdown stints={stints} />);

    // Check for muted background class
    const wrapper = container.querySelector("div");
    expect(wrapper).toHaveClass("bg-muted/30");
  });
});
