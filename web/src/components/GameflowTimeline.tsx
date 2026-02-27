import { useState, useRef, useEffect } from "react";
import type { GameflowData } from "../types/api";
import { StintBar } from "./StintBar";
import { StintDetailCard } from "./StintDetailCard";
import { Popover, PopoverTrigger, PopoverContent } from "./ui/popover";
import { getQuarterBoundaries, getStintPixelRange, TOTAL_REGULATION_SECONDS, OT_DURATION_SECONDS } from "../lib/timeline";

interface GameflowTimelineProps {
  data: GameflowData;
}

/**
 * Renders the full gameflow visualization with player lanes and stint bars
 * AC3.1: Each player has horizontal timeline lane across quarters
 * AC3.2: Stints color-coded by team
 * AC3.4: Timeline aligns correctly across players
 */
export function GameflowTimeline({ data }: GameflowTimelineProps) {
  const timelineRef = useRef<HTMLDivElement>(null);
  const [timelineWidth, setTimelineWidth] = useState(800);

  // Calculate total game seconds
  const maxPeriod = Math.max(...data.players.flatMap((p) => p.stints.map((s) => s.period)));
  const totalSeconds = maxPeriod > 4
    ? TOTAL_REGULATION_SECONDS + (maxPeriod - 4) * OT_DURATION_SECONDS
    : TOTAL_REGULATION_SECONDS;

  const quarterBoundaries = getQuarterBoundaries(maxPeriod);

  // Update timeline width on mount and resize
  useEffect(() => {
    if (timelineRef.current) {
      setTimelineWidth(timelineRef.current.clientWidth);
    }

    const handleResize = () => {
      if (timelineRef.current) {
        setTimelineWidth(timelineRef.current.clientWidth);
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Group players by team
  const homePlayers = data.players.filter((p) => p.team === data.homeTeam.tricode);
  const awayPlayers = data.players.filter((p) => p.team === data.awayTeam.tricode);

  const quarterLabels = quarterBoundaries.map((qb) => {
    if (qb.period <= 4) {
      return `Q${qb.period}`;
    } else {
      return `OT${qb.period - 4}`;
    }
  });

  return (
    <div className="w-full overflow-x-auto">
      {/* Quarter labels */}
      <div className="flex mb-2">
        <div className="w-24 flex-shrink-0" />
        <div ref={timelineRef} className="flex-1 relative h-8 bg-gray-50 border border-gray-200 rounded">
          {quarterBoundaries.map((qb, idx) => (
            <div
              key={idx}
              data-testid="quarter-boundary"
              style={{
                position: "absolute",
                left: `${((qb.startSeconds / totalSeconds) * timelineWidth) | 0}px`,
                height: "100%",
                width: "1px",
                backgroundColor: "#ccc",
              }}
            >
              <span className="absolute top-0.5 left-0.5 text-xs font-bold text-gray-700 bg-white px-1 rounded">
                {quarterLabels[idx]}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Home team section */}
      {homePlayers.length > 0 && (
        <div className="mb-4">
          <div className="text-xs font-bold text-gray-600 uppercase px-2 py-1 bg-blue-50">
            {data.homeTeam.name}
          </div>
          {homePlayers.map((player) => (
            <div key={player.playerId} className="flex items-center border-b border-gray-100">
              <div className="w-24 flex-shrink-0 px-2 py-3 text-sm font-medium">
                <span data-testid="player-name">{player.name}</span>
              </div>
              <div className="flex-1 relative h-16 bg-white border-l border-gray-100 overflow-hidden">
                {/* Quarter boundary lines */}
                {quarterBoundaries.map((qb, idx) => (
                  <div
                    key={idx}
                    style={{
                      position: "absolute",
                      left: `${((qb.startSeconds / totalSeconds) * (timelineWidth - 24)) | 0}px`,
                      height: "100%",
                      width: "1px",
                      backgroundColor: "#e5e7eb",
                    }}
                  />
                ))}

                {/* Stint bars */}
                {player.stints.map((stint, idx) => {
                  const pixelRange = getStintPixelRange(
                    stint.inTime,
                    stint.outTime,
                    stint.period,
                    timelineWidth - 24,
                    totalSeconds
                  );

                  return (
                    <Popover key={idx}>
                      <PopoverTrigger asChild>
                        <div>
                          <StintBar
                            stint={stint}
                            team={player.team}
                            x={pixelRange.x}
                            width={Math.max(pixelRange.width, 2)}
                            homeTeamTricode={data.homeTeam.tricode}
                            onStintClick={() => {
                              // Stint clicked - popover opens automatically via Radix
                            }}
                          />
                        </div>
                      </PopoverTrigger>
                      <PopoverContent side="top" align="center" className="w-auto p-0">
                        <StintDetailCard stint={stint} />
                      </PopoverContent>
                    </Popover>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Away team section */}
      {awayPlayers.length > 0 && (
        <div>
          <div className="text-xs font-bold text-gray-600 uppercase px-2 py-1 bg-red-50">
            {data.awayTeam.name}
          </div>
          {awayPlayers.map((player) => (
            <div key={player.playerId} className="flex items-center border-b border-gray-100">
              <div className="w-24 flex-shrink-0 px-2 py-3 text-sm font-medium">
                <span data-testid="player-name">{player.name}</span>
              </div>
              <div className="flex-1 relative h-16 bg-white border-l border-gray-100 overflow-hidden">
                {/* Quarter boundary lines */}
                {quarterBoundaries.map((qb, idx) => (
                  <div
                    key={idx}
                    style={{
                      position: "absolute",
                      left: `${((qb.startSeconds / totalSeconds) * (timelineWidth - 24)) | 0}px`,
                      height: "100%",
                      width: "1px",
                      backgroundColor: "#e5e7eb",
                    }}
                  />
                ))}

                {/* Stint bars */}
                {player.stints.map((stint, idx) => {
                  const pixelRange = getStintPixelRange(
                    stint.inTime,
                    stint.outTime,
                    stint.period,
                    timelineWidth - 24,
                    totalSeconds
                  );

                  return (
                    <Popover key={idx}>
                      <PopoverTrigger asChild>
                        <div>
                          <StintBar
                            stint={stint}
                            team={player.team}
                            x={pixelRange.x}
                            width={Math.max(pixelRange.width, 2)}
                            homeTeamTricode={data.homeTeam.tricode}
                            onStintClick={() => {
                              // Stint clicked - popover opens automatically via Radix
                            }}
                          />
                        </div>
                      </PopoverTrigger>
                      <PopoverContent side="top" align="center" className="w-auto p-0">
                        <StintDetailCard stint={stint} />
                      </PopoverContent>
                    </Popover>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
