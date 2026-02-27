import { useParams } from "react-router-dom";
import { useJsonData } from "@/hooks/useJsonData";
import type { BoxScoreData } from "@/types/api";
import { PlayerStatsTable } from "@/components/PlayerStatsTable";

export default function BoxScorePage() {
  const { gameId } = useParams<{ gameId: string }>();
  const url = gameId ? `/data/games/${gameId}/boxscore.json` : null;
  const { data, loading, error } = useJsonData<BoxScoreData>(url);

  if (loading) {
    return (
      <div style={{ padding: 24, color: "#E8D5B7" }}>
        <p>Loading box score...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <div
          style={{
            border: "1px solid #EB003C",
            background: "rgba(235, 0, 60, 0.1)",
            borderRadius: 6,
            padding: 16,
          }}
        >
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "#EB003C" }}>Game not found</h2>
          <p style={{ color: "#C4956A" }}>Unable to load box score for game {gameId}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ padding: 24, color: "#E8D5B7" }}>
        <p>No data available</p>
      </div>
    );
  }

  // Split players into home and away
  const homePlayers = data.players.filter((p) => p.team === data.homeTeam.tricode);
  const awayPlayers = data.players.filter((p) => p.team === data.awayTeam.tricode);

  // Get period totals for each team
  const homePeriodTotals = data.periodTotals.home;
  const awayPeriodTotals = data.periodTotals.away;

  return (
    <div style={{ minHeight: "calc(100vh - 60px)" }}>
      <div style={{ padding: "16px 24px" }}>
        {/* Game Header */}
        <div style={{ marginBottom: 32, textAlign: "center" }}>
          <h1
            style={{
              fontFamily: "'Oswald', sans-serif",
              fontSize: 18,
              fontWeight: 500,
              color: "#C4956A",
              marginBottom: 8,
            }}
          >
            {data.date}
          </h1>
          <div
            style={{
              fontFamily: "'Oswald', sans-serif",
              fontSize: 24,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 16,
            }}
          >
            <span style={{ color: "#C9A84C" }}>{data.homeTeam.name}</span>
            <span style={{ color: "#F5F0E8" }}>{data.homeTeam.score}</span>
            <span style={{ color: "#5C3A21" }}>-</span>
            <span style={{ color: "#F5F0E8" }}>{data.awayTeam.score}</span>
            <span style={{ color: "#C9A84C" }}>{data.awayTeam.name}</span>
          </div>
        </div>

        {/* Home Team Stats Table */}
        <PlayerStatsTable
          players={homePlayers}
          teamTotals={data.teamTotals.home}
          periodTotals={homePeriodTotals}
          teamName={data.homeTeam.name}
          teamTricode={data.homeTeam.tricode}
        />

        {/* Away Team Stats Table */}
        <PlayerStatsTable
          players={awayPlayers}
          teamTotals={data.teamTotals.away}
          periodTotals={awayPeriodTotals}
          teamName={data.awayTeam.name}
          teamTricode={data.awayTeam.tricode}
        />
      </div>
    </div>
  );
}
