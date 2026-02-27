import { forwardRef } from "react";
import type { GameflowStint } from "../types/api";

interface StintBarProps {
  stint: GameflowStint;
  team: string;
  x: number;
  width: number;
  homeTeamTricode: string;
  onStintClick?: (stint: GameflowStint) => void;
}

/**
 * Renders a single stint as a colored horizontal bar positioned absolutely
 * within a player's timeline lane
 *
 * AC3.2: Color-coded by team (home vs away)
 * AC3.3: Clickable to show detail card
 *
 * Uses forwardRef to allow Radix PopoverTrigger (asChild) to attach its ref
 * and merge trigger behavior with keyboard event handling for accessibility.
 */
export const StintBar = forwardRef<HTMLDivElement, StintBarProps>(
  (
    {
      stint,
      team,
      x,
      width,
      homeTeamTricode,
      onStintClick,
    },
    ref
  ) => {
    const isHomeTeam = team === homeTeamTricode;
    const bgColor = isHomeTeam ? "bg-blue-500" : "bg-red-500";
    const tooltip = `${stint.minutes.toFixed(1)}m +${stint.plusMinus}`;

    return (
      <div
        ref={ref}
        data-testid="stint-bar"
        style={{
          position: "absolute",
          left: `${x}px`,
          width: `${width}px`,
          top: "50%",
          transform: "translateY(-50%)",
          height: "24px",
          cursor: "pointer",
        }}
        className={`${bgColor} rounded opacity-90 hover:opacity-100 transition-opacity`}
        title={tooltip}
        aria-label={`Stint: ${stint.minutes.toFixed(1)} minutes, ${stint.plusMinus > 0 ? "+" : ""}${stint.plusMinus}`}
        onClick={() => onStintClick?.(stint)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onStintClick?.(stint);
          }
        }}
      />
    );
  }
);

StintBar.displayName = "StintBar";
