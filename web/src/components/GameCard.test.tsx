import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { GameCard } from "./GameCard";
import type { ScoreEntry } from "@/types/api";
import { renderWithRouter } from "@/test/test-utils";

describe("GameCard", () => {
  const mockGame: ScoreEntry = {
    gameId: "0022500001",
    date: "2026-01-19",
    homeTeam: { tricode: "DET", name: "Detroit Pistons", score: 104 },
    awayTeam: { tricode: "BOS", name: "Boston Celtics", score: 103 },
    status: "Final",
  };

  it("renders game information correctly", () => {
    renderWithRouter(<GameCard game={mockGame} />);

    // Check team tricodes
    expect(screen.getByText("DET")).toBeInTheDocument();
    expect(screen.getByText("BOS")).toBeInTheDocument();

    // Check team names
    expect(screen.getByText("Detroit Pistons")).toBeInTheDocument();
    expect(screen.getByText("Boston Celtics")).toBeInTheDocument();

    // Check scores
    expect(screen.getByText("104 - 103")).toBeInTheDocument();

    // Check status
    expect(screen.getByText("Final")).toBeInTheDocument();
  });

  it("renders links to box score and gameflow pages", () => {
    renderWithRouter(<GameCard game={mockGame} />);

    const boxScoreLink = screen.getByRole("link", { name: /Box Score/i });
    const gameflowLink = screen.getByRole("link", { name: /Gameflow/i });

    expect(boxScoreLink).toHaveAttribute(
      "href",
      `/game/${mockGame.gameId}/boxscore`
    );
    expect(gameflowLink).toHaveAttribute(
      "href",
      `/game/${mockGame.gameId}/gameflow`
    );
  });

  it("links use correct game ID from props", () => {
    const customGame: ScoreEntry = {
      ...mockGame,
      gameId: "9999999999",
    };

    renderWithRouter(<GameCard game={customGame} />);

    const boxScoreLink = screen.getByRole("link", { name: /Box Score/i });
    const gameflowLink = screen.getByRole("link", { name: /Gameflow/i });

    expect(boxScoreLink).toHaveAttribute(
      "href",
      `/game/9999999999/boxscore`
    );
    expect(gameflowLink).toHaveAttribute(
      "href",
      `/game/9999999999/gameflow`
    );
  });
});
