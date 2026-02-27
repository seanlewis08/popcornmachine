import { describe, it, expect, afterEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import BoxScorePage from "@/pages/BoxScorePage";
import { render } from "@testing-library/react";
import type { BoxScoreData } from "@/types/api";

const mockBoxScoreData: BoxScoreData = {
  gameId: "0022500001",
  date: "2026-01-19",
  homeTeam: { tricode: "DET", name: "Detroit Pistons", score: 104 },
  awayTeam: { tricode: "BOS", name: "Boston Celtics", score: 103 },
  players: [
    {
      playerId: "1234",
      name: "C Cunningham",
      team: "DET",
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
    },
    {
      playerId: "5678",
      name: "J Holiday",
      team: "BOS",
      totals: {
        min: 38.2,
        fgm: 6,
        fga: 15,
        fg3m: 2,
        fg3a: 7,
        ftm: 5,
        fta: 6,
        oreb: 0,
        reb: 2,
        ast: 8,
        blk: 0,
        stl: 2,
        tov: 1,
        pf: 2,
        pts: 19,
        plusMinus: -1,
        hv: 11,
        prod: 0.79,
        eff: 18,
      },
      stints: [
        {
          period: 1,
          inTime: "12:00",
          outTime: "2:30",
          minutes: 9.5,
          plusMinus: 2,
          fgm: 1,
          fga: 3,
          fg3m: 1,
          fg3a: 2,
          ftm: 2,
          fta: 2,
          oreb: 0,
          reb: 0,
          ast: 2,
          blk: 0,
          stl: 1,
          tov: 0,
          pf: 0,
          pts: 5,
        },
      ],
    },
  ],
  teamTotals: {
    home: {
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
    },
    away: {
      fgm: 33,
      fga: 83,
      fg3m: 13,
      fg3a: 41,
      ftm: 24,
      fta: 30,
      oreb: 16,
      reb: 47,
      ast: 13,
      blk: 4,
      stl: 5,
      tov: 11,
      pf: 26,
      pts: 103,
    },
  },
  periodTotals: {
    home: [
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
    ],
    away: [
      {
        period: 1,
        fgm: 9,
        fga: 25,
        fg3m: 4,
        fg3a: 12,
        ftm: 7,
        fta: 8,
        pts: 29,
      },
    ],
  },
};

function renderBoxScorePage(gameId: string) {
  return render(
    <MemoryRouter initialEntries={[`/game/${gameId}/boxscore`]}>
      <Routes>
        <Route path="/game/:gameId/boxscore" element={<BoxScorePage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("BoxScorePage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders both home and away team tables with valid boxscore data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockBoxScoreData),
      })
    );

    renderBoxScorePage("0022500001");

    // Wait for data to load and verify both team headers are rendered
    await waitFor(() => {
      expect(screen.getByText("Detroit Pistons (DET)")).toBeInTheDocument();
      expect(screen.getByText("Boston Celtics (BOS)")).toBeInTheDocument();
    });

    // Verify game header information
    expect(screen.getByText("2026-01-19")).toBeInTheDocument();
    // Scores appear multiple times (header + team totals), so use getAllByText
    expect(screen.getAllByText("104")).toHaveLength(2); // Header and team totals
    expect(screen.getAllByText("103")).toHaveLength(2); // Header and team totals

    // Verify player data renders for both teams
    expect(screen.getByText("C Cunningham")).toBeInTheDocument();
    expect(screen.getByText("J Holiday")).toBeInTheDocument();

    // Verify team totals rows render
    const teamTotalRows = screen.getAllByText("Team Totals");
    expect(teamTotalRows).toHaveLength(2);
  });

  it("displays loading state while fetching data", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              ok: true,
              json: () => Promise.resolve(mockBoxScoreData),
            });
          }, 100);
        });
      })
    );

    renderBoxScorePage("0022500001");

    // Verify loading message appears
    expect(screen.getByText("Loading box score...")).toBeInTheDocument();
  });

  it("renders error UI when fetch fails with 404 response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
      })
    );

    renderBoxScorePage("invalid");

    // Wait for error UI to render
    await waitFor(() => {
      expect(screen.getByText("Game not found")).toBeInTheDocument();
      expect(
        screen.getByText(/Unable to load box score for game/i)
      ).toBeInTheDocument();
    });
  });

  it("renders error UI when fetch throws an error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("Network error"))
    );

    renderBoxScorePage("0022500001");

    // Wait for error UI to render
    await waitFor(() => {
      expect(screen.getByText("Game not found")).toBeInTheDocument();
    });
  });

  it("verifies all stat columns render for both teams", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockBoxScoreData),
      })
    );

    renderBoxScorePage("0022500001");

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText("Detroit Pistons (DET)")).toBeInTheDocument();
    });

    // Verify header columns are present (Player appears twice, once per table)
    expect(screen.getAllByText("Player")).toHaveLength(2);
    expect(screen.getAllByText("Min")).toHaveLength(2);
    expect(screen.getAllByText("FG")).toHaveLength(2);
    expect(screen.getAllByText("3PT")).toHaveLength(2);
    expect(screen.getAllByText("FT")).toHaveLength(2);
    expect(screen.getAllByText("OREB")).toHaveLength(2);
    expect(screen.getAllByText("REB")).toHaveLength(2);
    expect(screen.getAllByText("AST")).toHaveLength(2);
    expect(screen.getAllByText("BLK")).toHaveLength(2);
    expect(screen.getAllByText("STL")).toHaveLength(2);
    expect(screen.getAllByText("TO")).toHaveLength(2);
    expect(screen.getAllByText("PF")).toHaveLength(2);
    expect(screen.getAllByText("PTS")).toHaveLength(2);
    expect(screen.getAllByText("+/-")).toHaveLength(2); // Two tables
    expect(screen.getAllByText("HV")).toHaveLength(2);
    expect(screen.getAllByText("PROD")).toHaveLength(2);
    expect(screen.getAllByText("EFF")).toHaveLength(2);

    // Verify player stat data renders
    expect(screen.getByText("4-17")).toBeInTheDocument(); // C Cunningham FG
    expect(screen.getByText("6-15")).toBeInTheDocument(); // J Holiday FG
  });

  it("exports the component and can be rendered", () => {
    expect(BoxScorePage).toBeDefined();
  });
});
