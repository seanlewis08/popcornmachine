import type { GameflowStint } from "../types/api";

interface StintDetailCardProps {
  stint: GameflowStint;
}

/**
 * Displays detailed information for a stint including stats and play-by-play
 * Rendered inside a popover when a stint is clicked (AC3.3)
 */
export function StintDetailCard({ stint }: StintDetailCardProps) {
  const plusMinusText = stint.plusMinus >= 0 ? `+${stint.plusMinus}` : `${stint.plusMinus}`;

  return (
    <div className="w-96 p-4">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-bold">Period {stint.period}</h3>
        <p className="text-sm text-gray-600">
          {stint.inTime} - {stint.outTime}
        </p>
      </div>

      {/* Time and Plus/Minus */}
      <div className="grid grid-cols-2 gap-4 mb-4 pb-4 border-b">
        <div>
          <div className="text-xs text-gray-500 uppercase">Minutes</div>
          <div className="text-lg font-semibold">{stint.minutes.toFixed(1)}m</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase">Plus/Minus</div>
          <div
            className={`text-lg font-semibold ${
              stint.plusMinus >= 0 ? "text-green-600" : "text-red-600"
            }`}
          >
            {plusMinusText}
          </div>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="mb-4 pb-4 border-b">
        <h4 className="text-sm font-bold mb-2 uppercase">Stats</h4>
        <div className="grid grid-cols-3 gap-2 text-sm">
          <div>
            <div className="text-xs text-gray-500">PTS</div>
            <div className="font-semibold">{stint.stats.pts}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">AST</div>
            <div className="font-semibold">{stint.stats.ast}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">REB</div>
            <div className="font-semibold">{stint.stats.reb}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">STL</div>
            <div className="font-semibold">{stint.stats.stl}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">BLK</div>
            <div className="font-semibold">{stint.stats.blk}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">TOV</div>
            <div className="font-semibold">{stint.stats.tov}</div>
          </div>
        </div>
      </div>

      {/* Shooting Splits */}
      <div className="mb-4 pb-4 border-b">
        <h4 className="text-sm font-bold mb-2 uppercase">Shooting</h4>
        <div className="grid grid-cols-3 gap-2 text-sm">
          <div>
            <div className="text-xs text-gray-500">FG</div>
            <div className="font-semibold">
              {stint.stats.fgm}-{stint.stats.fga}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500">3PT</div>
            <div className="font-semibold">
              {stint.stats.fg3m}-{stint.stats.fg3a}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500">FT</div>
            <div className="font-semibold">
              {stint.stats.ftm}-{stint.stats.fta}
            </div>
          </div>
        </div>
      </div>

      {/* Play-by-Play Events */}
      {stint.events.length > 0 && (
        <div>
          <h4 className="text-sm font-bold mb-2 uppercase">Play-by-Play</h4>
          <ul className="space-y-1 max-h-48 overflow-y-auto text-sm">
            {stint.events.map((event, idx) => (
              <li key={idx} className="text-gray-700">
                <span className="font-semibold text-gray-900">{event.clock}</span>
                {" - "}
                <span>{event.description}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
