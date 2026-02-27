import { useParams } from "react-router-dom";
import { useJsonData } from "@/hooks/useJsonData";
import { BoxScoreData } from "@/types/api";
import { PlayerStatsTable } from "@/components/PlayerStatsTable";
import { Card } from "@/components/ui/card";

export default function BoxScorePage() {
  const { gameId } = useParams<{ gameId: string }>();
  const url = gameId ? `/data/games/${gameId}/boxscore.json` : null;
  const { data, loading, error } = useJsonData<BoxScoreData>(url);

  if (loading) {
    return (
      <div className="p-4">
        <p>Loading box score...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <Card className="border-red-200 bg-red-50 p-4">
          <h2 className="text-lg font-bold text-red-800">Game not found</h2>
          <p className="text-red-700">Unable to load box score for game {gameId}</p>
        </Card>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-4">
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
    <div className="min-h-screen bg-background">
      <div className="p-4">
        {/* Game Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold mb-2">{data.date}</h1>
          <div className="text-xl font-semibold">
            <span>{data.homeTeam.name}</span>
            <span className="mx-4">{data.homeTeam.score}</span>
            <span>-</span>
            <span className="mx-4">{data.awayTeam.score}</span>
            <span>{data.awayTeam.name}</span>
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
