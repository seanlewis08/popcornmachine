import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import GameflowPage from "./GameflowPage";
import type { GameflowData } from "../types/api";

// Mock react-router-dom
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useParams: () => ({ gameId: "0022500001" }),
  };
});

describe("GameflowPage", () => {
  const mockGameflowData: GameflowData = {
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
        ],
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders game header with team names", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGameflowData),
        } as Response)
      )
    );

    const { container } = render(
      <BrowserRouter>
        <GameflowPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(container.textContent).toContain("Detroit Pistons");
      expect(container.textContent).toContain("Boston Celtics");
    });
  });

  it("renders the timeline with player lanes when data loads (AC3.1)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGameflowData),
        } as Response)
      )
    );

    render(
      <BrowserRouter>
        <GameflowPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Player A")).toBeInTheDocument();
    });
  });

  it("shows loading state while fetching", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise(() => {
            // Never resolves - simulate loading
          })
      )
    );

    render(
      <BrowserRouter>
        <GameflowPage />
      </BrowserRouter>
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("shows fallback message when fetch returns 404 (AC3.5)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 404,
        } as Response)
      )
    );

    render(
      <BrowserRouter>
        <GameflowPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/gameflow data not available/i)
      ).toBeInTheDocument();
    });
  });

  it("shows fallback message when players array is empty (AC3.5)", async () => {
    const emptyData: GameflowData = {
      ...mockGameflowData,
      players: [],
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(emptyData),
        } as Response)
      )
    );

    render(
      <BrowserRouter>
        <GameflowPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/gameflow data not available/i)
      ).toBeInTheDocument();
    });
  });

  it("shows fallback message on fetch error (AC3.5)", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("Network error"))));

    render(
      <BrowserRouter>
        <GameflowPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/gameflow data not available/i)
      ).toBeInTheDocument();
    });
  });

  it("fetches gameflow data for the correct gameId", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockGameflowData),
      } as Response)
    );

    vi.stubGlobal("fetch", fetchMock);

    render(
      <BrowserRouter>
        <GameflowPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "data/games/0022500001/gameflow.json",
        expect.any(Object)
      );
    });
  });

  it("renders vs separator between home and away teams", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGameflowData),
        } as Response)
      )
    );

    const { container } = render(
      <BrowserRouter>
        <GameflowPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(container.textContent).toContain("vs");
    });
  });
});
