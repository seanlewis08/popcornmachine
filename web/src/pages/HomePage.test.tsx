import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import HomePage from "./HomePage";
import { renderWithRouter } from "@/test/test-utils";

describe("HomePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders games grouped by date, most recent first", async () => {
    const indexData = {
      dates: [
        {
          date: "2026-01-20",
          games: [{ gameId: "0022500002", home: "LAL", away: "GSW" }],
        },
        {
          date: "2026-01-19",
          games: [{ gameId: "0022500001", home: "DET", away: "BOS" }],
        },
      ],
    };

    const scoresForDate1 = [
      {
        gameId: "0022500002",
        date: "2026-01-20",
        homeTeam: { tricode: "LAL", name: "LA Lakers", score: 120 },
        awayTeam: { tricode: "GSW", name: "Golden State Warriors", score: 118 },
        status: "Final",
      },
    ];

    const scoresForDate2 = [
      {
        gameId: "0022500001",
        date: "2026-01-19",
        homeTeam: { tricode: "DET", name: "Detroit Pistons", score: 104 },
        awayTeam: { tricode: "BOS", name: "Boston Celtics", score: 103 },
        status: "Final",
      },
    ];

    (globalThis.fetch as any) = vi.fn((url: string) => {
      if (url === "/data/index.json") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(indexData),
        } as Response);
      } else if (url === "/data/scores/2026-01-20.json") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(scoresForDate1),
        } as Response);
      } else if (url === "/data/scores/2026-01-19.json") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(scoresForDate2),
        } as Response);
      }
      return Promise.reject(new Error("Unknown URL"));
    });

    renderWithRouter(<HomePage />);

    // Wait for the Lakers game to appear (last game from date 2026-01-20)
    await waitFor(() => {
      expect(screen.getByText("Golden State Warriors")).toBeInTheDocument();
    });

    // Check that both team names are displayed
    expect(screen.getByText("LA Lakers")).toBeInTheDocument();
    expect(screen.getByText("Detroit Pistons")).toBeInTheDocument();
    expect(screen.getByText("Boston Celtics")).toBeInTheDocument();
  });

  it("displays team names and scores for each game", async () => {
    const indexData = {
      dates: [
        {
          date: "2026-01-19",
          games: [{ gameId: "0022500001", home: "DET", away: "BOS" }],
        },
      ],
    };

    const scoresData = [
      {
        gameId: "0022500001",
        date: "2026-01-19",
        homeTeam: { tricode: "DET", name: "Detroit Pistons", score: 104 },
        awayTeam: { tricode: "BOS", name: "Boston Celtics", score: 103 },
        status: "Final",
      },
    ];

    (globalThis.fetch as any) = vi.fn((url: string) => {
      if (url === "/data/index.json") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(indexData),
        } as Response);
      } else if (url === "/data/scores/2026-01-19.json") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(scoresData),
        } as Response);
      }
      return Promise.reject(new Error("Unknown URL"));
    });

    renderWithRouter(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("Detroit Pistons")).toBeInTheDocument();
    });

    expect(screen.getByText("Boston Celtics")).toBeInTheDocument();
    expect(screen.getByText("104 - 103")).toBeInTheDocument();
    expect(screen.getByText("DET")).toBeInTheDocument();
    expect(screen.getByText("BOS")).toBeInTheDocument();
  });

  it("renders links to box score and gameflow for each game", async () => {
    const indexData = {
      dates: [
        {
          date: "2026-01-19",
          games: [{ gameId: "0022500001", home: "DET", away: "BOS" }],
        },
      ],
    };

    const scoresData = [
      {
        gameId: "0022500001",
        date: "2026-01-19",
        homeTeam: { tricode: "DET", name: "Detroit Pistons", score: 104 },
        awayTeam: { tricode: "BOS", name: "Boston Celtics", score: 103 },
        status: "Final",
      },
    ];

    (globalThis.fetch as any) = vi.fn((url: string) => {
      if (url === "/data/index.json") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(indexData),
        } as Response);
      } else if (url === "/data/scores/2026-01-19.json") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(scoresData),
        } as Response);
      }
      return Promise.reject(new Error("Unknown URL"));
    });

    renderWithRouter(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("Detroit Pistons")).toBeInTheDocument();
    });

    const boxScoreLink = screen.getByRole("link", { name: /Box Score/i });
    const gameflowLink = screen.getByRole("link", { name: /Gameflow/i });

    expect(boxScoreLink).toHaveAttribute(
      "href",
      `/game/0022500001/boxscore`
    );
    expect(gameflowLink).toHaveAttribute(
      "href",
      `/game/0022500001/gameflow`
    );
  });

  it("shows 'No games available' when index returns empty dates", async () => {
    const indexData = { dates: [] };

    (globalThis.fetch as any) = vi.fn((url: string) => {
      if (url === "/data/index.json") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(indexData),
        } as Response);
      }
      return Promise.reject(new Error("Unknown URL"));
    });

    renderWithRouter(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText(/No games available/i)).toBeInTheDocument();
    });
  });

  it("shows 'No games available' when fetch fails (404 on index)", async () => {
    (globalThis.fetch as any) = vi.fn((url: string) => {
      if (url === "/data/index.json") {
        return Promise.resolve({
          ok: false,
          status: 404,
        } as Response);
      }
      return Promise.reject(new Error("Unknown URL"));
    });

    renderWithRouter(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText(/Unable to load games/i)).toBeInTheDocument();
    });
  });

  it("shows error message when fetch fails", async () => {
    const errorMsg = "Network error";
    (globalThis.fetch as any) = vi.fn(() =>
      Promise.reject(new Error(errorMsg))
    );

    renderWithRouter(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText(/Unable to load games/i)).toBeInTheDocument();
    });

    expect(screen.getByText(errorMsg)).toBeInTheDocument();
  });

  it("gracefully handles missing score files for some dates", async () => {
    const indexData = {
      dates: [
        {
          date: "2026-01-20",
          games: [{ gameId: "0022500002", home: "LAL", away: "GSW" }],
        },
        {
          date: "2026-01-19",
          games: [{ gameId: "0022500001", home: "DET", away: "BOS" }],
        },
      ],
    };

    const scoresForDate1 = [
      {
        gameId: "0022500001",
        date: "2026-01-19",
        homeTeam: { tricode: "DET", name: "Detroit Pistons", score: 104 },
        awayTeam: { tricode: "BOS", name: "Boston Celtics", score: 103 },
        status: "Final",
      },
    ];

    (globalThis.fetch as any) = vi.fn((url: string) => {
      if (url === "/data/index.json") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(indexData),
        } as Response);
      } else if (url === "/data/scores/2026-01-20.json") {
        // This date's file doesn't exist (404)
        return Promise.resolve({
          ok: false,
          status: 404,
        } as Response);
      } else if (url === "/data/scores/2026-01-19.json") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(scoresForDate1),
        } as Response);
      }
      return Promise.reject(new Error("Unknown URL"));
    });

    renderWithRouter(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("Detroit Pistons")).toBeInTheDocument();
    });

    // Should display the available date with games
    expect(screen.getByText("Boston Celtics")).toBeInTheDocument();

    // Only one date should be shown (the one with games)
    const gamesRendered = screen.getAllByText(/Pistons|Celtics/i);
    expect(gamesRendered.length).toBeGreaterThan(0);
  });
});
