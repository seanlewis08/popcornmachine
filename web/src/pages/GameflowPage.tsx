import { useParams } from "react-router-dom";
import { useJsonData } from "../hooks/useJsonData";
import { GameflowTimeline } from "../components/GameflowTimeline";
import type { GameflowData, BoxScoreData } from "../types/api";

export default function GameflowPage() {
  const { gameId } = useParams<{ gameId: string }>();

  // Fetch gameflow data
  const gameflowUrl = gameId ? `data/games/${gameId}/gameflow.json` : null;
  const { data, loading, error } = useJsonData<GameflowData>(gameflowUrl);

  // Also fetch boxscore for player totals (Min, Pts, hv, +/-)
  const boxscoreUrl = gameId ? `data/games/${gameId}/boxscore.json` : null;
  const { data: boxscore } = useJsonData<BoxScoreData>(boxscoreUrl);

  // Show loading state
  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <h1
          style={{
            fontFamily: "'Oswald', sans-serif",
            fontSize: 24,
            fontWeight: 700,
            color: "#C9A84C",
            marginBottom: 16,
          }}
        >
          Gameflow
        </h1>
        <div style={{ color: "#E8D5B7" }}>Loading...</div>
      </div>
    );
  }

  // Show fallback for missing or empty data
  if (error || !data || !data.players || data.players.length === 0) {
    return (
      <div style={{ padding: 24 }}>
        <h1
          style={{
            fontFamily: "'Oswald', sans-serif",
            fontSize: 24,
            fontWeight: 700,
            color: "#C9A84C",
            marginBottom: 16,
          }}
        >
          Gameflow
        </h1>
        <div
          style={{
            color: "#C9A84C",
            background: "rgba(201, 168, 76, 0.1)",
            padding: 16,
            borderRadius: 6,
            border: "1px solid rgba(201, 168, 76, 0.3)",
          }}
        >
          Gameflow data not available for this game.
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 16, overflowX: "auto" }}>
      <GameflowTimeline data={data} boxscore={boxscore ?? undefined} />
    </div>
  );
}
