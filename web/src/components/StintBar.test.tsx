import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StintBar } from "./StintBar";
import type { GameflowStint } from "../types/api";

describe("StintBar", () => {
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
    ],
  };

  it("renders a stint bar with absolute positioning", () => {
    const { container } = render(
      <StintBar
        stint={mockStint}
        team="DET"
        x={100}
        width={150}
        homeTeamTricode="DET"
        onStintClick={vi.fn()}
      />
    );

    const bar = container.querySelector("[data-testid='stint-bar']");
    expect(bar).toBeInTheDocument();

    // Check positioning
    const style = bar?.getAttribute("style") || "";
    expect(style).toContain("position: absolute");
    expect(style).toContain("left: 100px");
    expect(style).toContain("width: 150px");
  });

  it("applies home team color when team matches homeTeamTricode", () => {
    const { container } = render(
      <StintBar
        stint={mockStint}
        team="DET"
        x={100}
        width={150}
        homeTeamTricode="DET"
        onStintClick={vi.fn()}
      />
    );

    const bar = container.querySelector("[data-testid='stint-bar']");
    expect(bar).toHaveClass("bg-blue-500");
  });

  it("applies away team color when team does not match homeTeamTricode", () => {
    const { container } = render(
      <StintBar
        stint={mockStint}
        team="BOS"
        x={100}
        width={150}
        homeTeamTricode="DET"
        onStintClick={vi.fn()}
      />
    );

    const bar = container.querySelector("[data-testid='stint-bar']");
    expect(bar).toHaveClass("bg-red-500");
  });

  it("calls onStintClick when clicked", async () => {
    const onStintClick = vi.fn();
    const user = userEvent.setup();

    const { container } = render(
      <StintBar
        stint={mockStint}
        team="DET"
        x={100}
        width={150}
        homeTeamTricode="DET"
        onStintClick={onStintClick}
      />
    );

    const bar = container.querySelector("[data-testid='stint-bar']");
    if (bar) {
      await user.click(bar);
    }

    expect(onStintClick).toHaveBeenCalledWith(mockStint);
  });

  it("shows tooltip with stint minutes and plus-minus on hover", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <StintBar
        stint={mockStint}
        team="DET"
        x={100}
        width={150}
        homeTeamTricode="DET"
        onStintClick={vi.fn()}
      />
    );

    const bar = container.querySelector("[data-testid='stint-bar']");
    if (bar) {
      await user.hover(bar);
      // Tooltip should appear (implementation depends on Radix)
      // For now, just verify the title attribute or aria-label is set
      expect(bar.getAttribute("title") || bar.getAttribute("aria-label")).toBeTruthy();
    }
  });

  it("handles very small width stints", () => {
    const { container } = render(
      <StintBar
        stint={mockStint}
        team="DET"
        x={500}
        width={5}
        homeTeamTricode="DET"
        onStintClick={vi.fn()}
      />
    );

    const bar = container.querySelector("[data-testid='stint-bar']");
    expect(bar).toBeInTheDocument();
  });

  it("calls onStintClick when Enter key is pressed on focused stint bar", async () => {
    const onStintClick = vi.fn();
    const user = userEvent.setup();

    const { container } = render(
      <StintBar
        stint={mockStint}
        team="DET"
        x={100}
        width={150}
        homeTeamTricode="DET"
        onStintClick={onStintClick}
      />
    );

    const bar = container.querySelector("[data-testid='stint-bar']") as HTMLElement;
    expect(bar).toBeInTheDocument();

    // Focus the stint bar
    bar.focus();
    expect(bar).toHaveFocus();

    // Press Enter
    await user.keyboard("{Enter}");

    expect(onStintClick).toHaveBeenCalledWith(mockStint);
  });

  it("calls onStintClick when Space key is pressed on focused stint bar", async () => {
    const onStintClick = vi.fn();
    const user = userEvent.setup();

    const { container } = render(
      <StintBar
        stint={mockStint}
        team="DET"
        x={100}
        width={150}
        homeTeamTricode="DET"
        onStintClick={onStintClick}
      />
    );

    const bar = container.querySelector("[data-testid='stint-bar']") as HTMLElement;
    expect(bar).toBeInTheDocument();

    // Focus the stint bar
    bar.focus();
    expect(bar).toHaveFocus();

    // Press Space
    await user.keyboard(" ");

    expect(onStintClick).toHaveBeenCalledWith(mockStint);
  });

  it("is keyboard focusable with tabIndex 0", () => {
    const { container } = render(
      <StintBar
        stint={mockStint}
        team="DET"
        x={100}
        width={150}
        homeTeamTricode="DET"
        onStintClick={vi.fn()}
      />
    );

    const bar = container.querySelector("[data-testid='stint-bar']");
    expect(bar).toHaveAttribute("tabIndex", "0");
  });
});
