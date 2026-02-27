import { describe, it, expect } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { render } from "@testing-library/react";
import { PlayerStatsTable } from "@/components/PlayerStatsTable";
import type {
  PlayerData,
  TeamTotals,
  PeriodTotals,
} from "@/types/api";

// Fixture data from design plan
const createFixturePlayer = (
  id: string,
  name: string,
  team: string
): PlayerData => ({
  playerId: id,
  name,
  team,
  totals: {
    min: 40.3,
    fgm: 4,
    fga: 17,
    fg3m: 0,
    fg3a: 4,
    ftm: 8,
    fta: 10,
    oreb: 1,
    reb: 3,
    ast: 14,
    blk: 2,
    stl: 1,
    tov: 0,
    pf: 3,
    pts: 16,
    plusMinus: 2,
    hv: 20,
    prod: 0.89,
    eff: 21,
  },
  stints: [
    {
      period: 1,
      inTime: "12:00",
      outTime: "1:54",
      minutes: 10.1,
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
    },
  ],
});

const teamTotals: TeamTotals = {
  fgm: 38,
  fga: 88,
  fg3m: 11,
  fg3a: 33,
  ftm: 17,
  fta: 23,
  oreb: 9,
  reb: 40,
  ast: 24,
  blk: 9,
  stl: 9,
  tov: 5,
  pf: 26,
  pts: 104,
};

const periodTotals: PeriodTotals[] = [
  {
    period: 1,
    fgm: 8,
    fga: 24,
    fg3m: 1,
    fg3a: 7,
    ftm: 9,
    fta: 12,
    pts: 26,
  },
];

describe("PlayerStatsTable", () => {
  // AC2.1: All stat columns render
  it("AC2.1: renders all stat columns", () => {
    const players = [createFixturePlayer("1234", "C Cunningham", "DET")];

    render(
      <PlayerStatsTable
        players={players}
        teamTotals={teamTotals}
        periodTotals={periodTotals}
        teamName="Detroit Pistons"
        teamTricode="DET"
      />
    );

    // Check for all column headers
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
    expect(screen.getByText("HV")).toBeInTheDocument();
    expect(screen.getByText("PROD")).toBeInTheDocument();
    expect(screen.getByText("EFF")).toBeInTheDocument();
  });

  // AC2.2: Derived metrics display correctly
  it("AC2.2: displays derived metrics (hv, prod, eff) correctly", () => {
    const players = [createFixturePlayer("1234", "C Cunningham", "DET")];

    render(
      <PlayerStatsTable
        players={players}
        teamTotals={teamTotals}
        periodTotals={periodTotals}
        teamName="Detroit Pistons"
        teamTricode="DET"
      />
    );

    // Check for derived metric values
    expect(screen.getByText("20")).toBeInTheDocument(); // HV
    expect(screen.getByText("0.89")).toBeInTheDocument(); // PROD (formatted to 2 decimals)
    expect(screen.getAllByText("21")[0]).toBeInTheDocument(); // EFF
  });

  // AC2.3: Clicking a player row expands stint breakdown
  it("AC2.3: expands stint breakdown when clicking a player row", async () => {
    const players = [createFixturePlayer("1234", "C Cunningham", "DET")];

    render(
      <PlayerStatsTable
        players={players}
        teamTotals={teamTotals}
        periodTotals={periodTotals}
        teamName="Detroit Pistons"
        teamTricode="DET"
      />
    );

    // Find the player row and click it
    const playerCell = screen.getByText("C Cunningham");
    fireEvent.click(playerCell);

    // Check that stint data appears
    expect(screen.getByText("12:00")).toBeInTheDocument(); // inTime
    expect(screen.getByText("1:54")).toBeInTheDocument(); // outTime
  });

  // AC2.4: Team totals row renders with aggregate stats
  it("AC2.4: renders team totals row with aggregate stats", () => {
    const players = [createFixturePlayer("1234", "C Cunningham", "DET")];

    render(
      <PlayerStatsTable
        players={players}
        teamTotals={teamTotals}
        periodTotals={periodTotals}
        teamName="Detroit Pistons"
        teamTricode="DET"
      />
    );

    // Check for team totals row
    expect(screen.getByText("Team Totals")).toBeInTheDocument();
    // Check aggregate stat values
    expect(screen.getByText("38-88")).toBeInTheDocument(); // FG
    expect(screen.getByText("11-33")).toBeInTheDocument(); // 3PT
    expect(screen.getByText("17-23")).toBeInTheDocument(); // FT
  });

  // AC2.5: Period breakdown rows render with per-quarter stats
  it("AC2.5: renders period breakdown rows with per-quarter stats", () => {
    const players = [createFixturePlayer("1234", "C Cunningham", "DET")];

    render(
      <PlayerStatsTable
        players={players}
        teamTotals={teamTotals}
        periodTotals={periodTotals}
        teamName="Detroit Pistons"
        teamTricode="DET"
      />
    );

    // Check for period rows
    expect(screen.getByText("Q1")).toBeInTheDocument();
    // Check period stats
    expect(screen.getByText("8-24")).toBeInTheDocument(); // Q1 FG
  });

  // Additional: Verify team header renders
  it("renders team header with name and tricode", () => {
    const players = [createFixturePlayer("1234", "C Cunningham", "DET")];

    render(
      <PlayerStatsTable
        players={players}
        teamTotals={teamTotals}
        periodTotals={periodTotals}
        teamName="Detroit Pistons"
        teamTricode="DET"
      />
    );

    expect(screen.getByText("Detroit Pistons (DET)")).toBeInTheDocument();
  });

  // Additional: Verify +/- color coding
  it("displays +/- with correct color for positive values", () => {
    const players = [createFixturePlayer("1234", "C Cunningham", "DET")];

    render(
      <PlayerStatsTable
        players={players}
        teamTotals={teamTotals}
        periodTotals={periodTotals}
        teamName="Detroit Pistons"
        teamTricode="DET"
      />
    );

    // The player has plusMinus: 2 (positive)
    const plusMinusCell = screen.getByTestId("plus-minus-1234");
    expect(plusMinusCell).toHaveClass("text-green-600");
  });

  // Additional: Verify minutes formatting
  it("formats minutes correctly (M:SS)", () => {
    const players = [createFixturePlayer("1234", "C Cunningham", "DET")];

    render(
      <PlayerStatsTable
        players={players}
        teamTotals={teamTotals}
        periodTotals={periodTotals}
        teamName="Detroit Pistons"
        teamTricode="DET"
      />
    );

    // Player has 40.3 minutes, should display as 40:18
    expect(screen.getByText("40:18")).toBeInTheDocument();
  });
});
