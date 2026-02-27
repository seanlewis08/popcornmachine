import { Link } from "react-router-dom";
import type { ScoreEntry } from "@/types/api";

interface GameCardProps {
  game: ScoreEntry;
}

export function GameCard({ game }: GameCardProps) {
  return (
    <div
      style={{
        background: "linear-gradient(135deg, rgba(92, 58, 33, 0.6) 0%, rgba(44, 24, 16, 0.8) 100%)",
        border: "1px solid #5C3A21",
        borderRadius: 8,
        padding: 16,
        marginBottom: 12,
        boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        {/* Home Team */}
        <div style={{ flex: 1, textAlign: "center" }}>
          <div
            style={{
              fontFamily: "'Oswald', sans-serif",
              fontSize: 22,
              fontWeight: 600,
              color: "#C9A84C",
            }}
          >
            {game.homeTeam.tricode}
          </div>
          <div style={{ fontSize: 12, color: "#C4956A" }}>{game.homeTeam.name}</div>
        </div>

        {/* Score */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
          <div
            style={{
              fontFamily: "'Oswald', sans-serif",
              fontSize: 28,
              fontWeight: 700,
              color: "#F5F0E8",
              letterSpacing: 2,
            }}
          >
            {game.homeTeam.score} - {game.awayTeam.score}
          </div>
          <div
            style={{
              fontSize: 11,
              fontWeight: 500,
              color: game.status === "Final" ? "#C9A84C" : "#FF6B35",
              textTransform: "uppercase",
              letterSpacing: 1,
            }}
          >
            {game.status}
          </div>
        </div>

        {/* Away Team */}
        <div style={{ flex: 1, textAlign: "center" }}>
          <div
            style={{
              fontFamily: "'Oswald', sans-serif",
              fontSize: 22,
              fontWeight: 600,
              color: "#C9A84C",
            }}
          >
            {game.awayTeam.tricode}
          </div>
          <div style={{ fontSize: 12, color: "#C4956A" }}>{game.awayTeam.name}</div>
        </div>
      </div>

      {/* Links */}
      <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
        <Link
          to={`/game/${game.gameId}/boxscore`}
          style={{
            flex: 1,
            textAlign: "center",
            padding: "8px 12px",
            borderRadius: 4,
            fontSize: 13,
            fontWeight: 600,
            fontFamily: "'Oswald', sans-serif",
            textTransform: "uppercase",
            letterSpacing: 1,
            textDecoration: "none",
            color: "#F5F0E8",
            background: "linear-gradient(180deg, #00519A 0%, #003d75 100%)",
            border: "1px solid #006bcc",
          }}
        >
          Box Score
        </Link>
        <Link
          to={`/game/${game.gameId}/gameflow`}
          style={{
            flex: 1,
            textAlign: "center",
            padding: "8px 12px",
            borderRadius: 4,
            fontSize: 13,
            fontWeight: 600,
            fontFamily: "'Oswald', sans-serif",
            textTransform: "uppercase",
            letterSpacing: 1,
            textDecoration: "none",
            color: "#F5F0E8",
            background: "linear-gradient(180deg, #008348 0%, #005d33 100%)",
            border: "1px solid #00a85a",
          }}
        >
          Gameflow
        </Link>
      </div>
    </div>
  );
}
