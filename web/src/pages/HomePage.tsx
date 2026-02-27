import { useJsonData } from "@/hooks/useJsonData";
import type { IndexData, ScoreEntry } from "@/types/api";
import { GameCard } from "@/components/GameCard";
import { useEffect, useState } from "react";

export default function HomePage() {
  const { data: indexData, loading: indexLoading, error: indexError } =
    useJsonData<IndexData>("/data/index.json");

  const [games, setGames] = useState<ScoreEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Fetch score files for each date
  useEffect(() => {
    if (!indexData) {
      if (!indexLoading) {
        setLoading(false);
      }
      return;
    }

    const fetchAllGames = async () => {
      try {
        const allGames: ScoreEntry[] = [];

        // Fetch scores for each date
        for (const dateEntry of indexData.dates) {
          try {
            const response = await fetch(
              `/data/scores/${dateEntry.date}.json`
            );
            if (response.ok) {
              const scoreData = await response.json();
              allGames.push(...scoreData);
            }
          } catch (err) {
            // Silently skip dates that don't have score files
            console.warn(`Failed to fetch scores for ${dateEntry.date}:`, err);
          }
        }

        setGames(allGames);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err : new Error(String(err)));
      } finally {
        setLoading(false);
      }
    };

    fetchAllGames();
  }, [indexData, indexLoading]);

  // Handle index file loading errors
  useEffect(() => {
    if (indexError && !indexLoading) {
      setError(indexError);
      setLoading(false);
    }
  }, [indexError, indexLoading]);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto p-4">
        <h1 className="text-4xl font-bold mb-8">NBA Scores</h1>

        {loading && (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-gray-600">Loading games...</span>
          </div>
        )}

        {error && !loading && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-red-800 font-medium">
              Unable to load games. Please try again later.
            </p>
            <p className="text-red-600 text-sm mt-1">{error.message}</p>
          </div>
        )}

        {!loading && !error && games.length === 0 && (
          <div className="rounded-lg border border-gray-200 bg-gray-100 p-8 text-center">
            <p className="text-gray-700 font-medium">No games available</p>
            <p className="text-gray-500 text-sm mt-1">
              Check back soon for upcoming NBA games.
            </p>
          </div>
        )}

        {!loading && !error && games.length > 0 && (
          <div>
            {indexData?.dates.map((dateEntry) => {
              const dateGames = games.filter((g) => g.date === dateEntry.date);
              if (dateGames.length === 0) return null;

              return (
                <div key={dateEntry.date} className="mb-8">
                  <h2 className="text-xl font-semibold mb-4 text-gray-800">
                    {new Date(dateEntry.date + "T00:00:00").toLocaleDateString(
                      "en-US",
                      { weekday: "long", month: "short", day: "numeric" }
                    )}
                  </h2>
                  <div>
                    {dateGames.map((game) => (
                      <GameCard key={game.gameId} game={game} />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
