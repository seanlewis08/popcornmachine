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
    <div style={{ minHeight: "calc(100vh - 60px)" }}>
      <div style={{ maxWidth: 640, margin: "0 auto", padding: "24px 16px" }}>
        <h1
          style={{
            fontFamily: "'Oswald', sans-serif",
            fontSize: 32,
            fontWeight: 700,
            color: "#C9A84C",
            marginBottom: 24,
            textTransform: "uppercase",
            letterSpacing: 2,
          }}
        >
          NBA Scores
        </h1>

        {loading && (
          <div style={{ textAlign: "center", padding: "48px 0", color: "#E8D5B7" }}>
            <div
              style={{
                width: 40,
                height: 40,
                border: "3px solid #5C3A21",
                borderTopColor: "#C9A84C",
                borderRadius: "50%",
                margin: "0 auto 12px",
                animation: "spin 1s linear infinite",
              }}
            />
            Loading games...
          </div>
        )}

        {error && !loading && (
          <div
            style={{
              border: "1px solid #EB003C",
              background: "rgba(235, 0, 60, 0.1)",
              borderRadius: 6,
              padding: 16,
              color: "#F5F0E8",
            }}
          >
            <p style={{ fontWeight: 600 }}>Unable to load games. Please try again later.</p>
            <p style={{ fontSize: 13, marginTop: 4, opacity: 0.7 }}>{error.message}</p>
          </div>
        )}

        {!loading && !error && games.length === 0 && (
          <div
            style={{
              border: "1px solid #5C3A21",
              background: "rgba(92, 58, 33, 0.3)",
              borderRadius: 6,
              padding: 32,
              textAlign: "center",
              color: "#E8D5B7",
            }}
          >
            <p style={{ fontWeight: 600 }}>No games available</p>
            <p style={{ fontSize: 13, marginTop: 4, opacity: 0.7 }}>
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
                <div key={dateEntry.date} style={{ marginBottom: 32 }}>
                  <h2
                    style={{
                      fontFamily: "'Oswald', sans-serif",
                      fontSize: 20,
                      fontWeight: 500,
                      color: "#E8D5B7",
                      marginBottom: 12,
                      borderBottom: "1px solid #5C3A21",
                      paddingBottom: 8,
                    }}
                  >
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
