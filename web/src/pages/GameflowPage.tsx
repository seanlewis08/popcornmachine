import { useParams } from "react-router-dom";
import { useJsonData } from "../hooks/useJsonData";
import { GameflowTimeline } from "../components/GameflowTimeline";
import type { GameflowData } from "../types/api";

export default function GameflowPage() {
  const { gameId } = useParams<{ gameId: string }>();

  // Fetch gameflow data
  const url = gameId ? `data/games/${gameId}/gameflow.json` : null;
  const { data, loading, error } = useJsonData<GameflowData>(url);

  // Show loading state
  if (loading) {
    return (
      <div className="p-4">
        <h1 className="text-2xl font-bold mb-4">Gameflow</h1>
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  // Show fallback for missing or empty data
  if (error || !data || !data.players || data.players.length === 0) {
    return (
      <div className="p-4">
        <h1 className="text-2xl font-bold mb-4">Gameflow</h1>
        <div className="text-yellow-700 bg-yellow-50 p-4 rounded border border-yellow-200">
          Gameflow data not available for this game.
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      {/* Game header */}
      <div className="mb-4">
        <h1 className="text-3xl font-bold text-center mb-2">
          <span className="text-blue-600">{data.homeTeam.tricode}</span>
          <span className="text-gray-400 mx-3">vs</span>
          <span className="text-red-600">{data.awayTeam.tricode}</span>
        </h1>
        <p className="text-center text-gray-600 text-sm">
          {data.homeTeam.name} vs {data.awayTeam.name}
        </p>
      </div>

      {/* Timeline */}
      <div className="mt-6">
        <GameflowTimeline data={data} />
      </div>
    </div>
  );
}
