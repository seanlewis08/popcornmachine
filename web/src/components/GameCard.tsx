import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import type { ScoreEntry } from "@/types/api";

interface GameCardProps {
  game: ScoreEntry;
}

export function GameCard({ game }: GameCardProps) {
  return (
    <Card className="mb-4">
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-4">
          {/* Home Team */}
          <div className="flex-1 text-center">
            <div className="text-lg font-semibold">{game.homeTeam.tricode}</div>
            <div className="text-sm text-gray-600">{game.homeTeam.name}</div>
          </div>

          {/* Score */}
          <div className="flex flex-col items-center gap-1">
            <div className="text-2xl font-bold">
              {game.homeTeam.score} - {game.awayTeam.score}
            </div>
            <div className="text-xs font-medium text-gray-500">
              {game.status}
            </div>
          </div>

          {/* Away Team */}
          <div className="flex-1 text-center">
            <div className="text-lg font-semibold">{game.awayTeam.tricode}</div>
            <div className="text-sm text-gray-600">{game.awayTeam.name}</div>
          </div>
        </div>

        {/* Links */}
        <div className="mt-4 flex gap-2">
          <Link
            to={`/game/${game.gameId}/boxscore`}
            className="flex-1 rounded bg-blue-500 px-3 py-2 text-center text-sm font-medium text-white hover:bg-blue-600"
          >
            Box Score
          </Link>
          <Link
            to={`/game/${game.gameId}/gameflow`}
            className="flex-1 rounded bg-green-500 px-3 py-2 text-center text-sm font-medium text-white hover:bg-green-600"
          >
            Gameflow
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
