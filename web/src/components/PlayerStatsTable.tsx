import { Fragment, useState } from "react";
import type { PlayerData, TeamTotals, PeriodTotals } from "@/types/api";
import { StintBreakdown } from "@/components/StintBreakdown";

interface PlayerStatsTableProps {
  players: PlayerData[];
  teamTotals: TeamTotals;
  periodTotals: PeriodTotals[];
  teamName: string;
  teamTricode: string;
}

/**
 * Formats minutes as M:SS from decimal minutes
 */
function formatMinutes(decimalMinutes: number): string {
  const minutes = Math.floor(decimalMinutes);
  const seconds = Math.round((decimalMinutes - minutes) * 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

/**
 * Returns color for +/- value
 */
function getPlusMinusColor(value: number): string {
  if (value > 0) return "#4ade80";
  if (value < 0) return "#f87171";
  return "#E8D5B7";
}

const thStyle: React.CSSProperties = {
  padding: "6px 8px",
  textAlign: "center",
  fontFamily: "'Oswald', sans-serif",
  fontSize: 12,
  fontWeight: 600,
  color: "#C9A84C",
  textTransform: "uppercase",
  letterSpacing: 0.5,
  borderBottom: "2px solid #5C3A21",
  background: "#2C1810",
  whiteSpace: "nowrap",
};

const tdStyle: React.CSSProperties = {
  padding: "4px 8px",
  textAlign: "center",
  fontSize: 13,
  fontFamily: "'Roboto Condensed', Arial",
  color: "#E8D5B7",
  borderBottom: "1px solid rgba(92, 58, 33, 0.3)",
  whiteSpace: "nowrap",
};

export function PlayerStatsTable({
  players,
  teamTotals,
  periodTotals,
  teamName,
  teamTricode,
}: PlayerStatsTableProps) {
  const [expandedPlayers, setExpandedPlayers] = useState<Set<string>>(
    new Set()
  );

  const togglePlayer = (playerId: string) => {
    const newSet = new Set(expandedPlayers);
    if (newSet.has(playerId)) {
      newSet.delete(playerId);
    } else {
      newSet.add(playerId);
    }
    setExpandedPlayers(newSet);
  };

  const headers = ["Player", "Min", "FG", "3PT", "FT", "OREB", "REB", "AST", "BLK", "STL", "TO", "PF", "PTS", "+/-", "HV", "PROD", "EFF"];

  return (
    <div style={{ marginBottom: 32 }}>
      <div style={{ marginBottom: 12 }}>
        <h2
          style={{
            fontFamily: "'Oswald', sans-serif",
            fontSize: 20,
            fontWeight: 700,
            color: "#C9A84C",
            textTransform: "uppercase",
          }}
        >
          {teamName} ({teamTricode})
        </h2>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            border: "1px solid #5C3A21",
            borderRadius: 4,
            overflow: "hidden",
          }}
        >
          <thead>
            <tr>
              {headers.map((h, i) => (
                <th
                  key={h}
                  style={{
                    ...thStyle,
                    textAlign: i === 0 ? "left" : "center",
                    position: i === 0 ? "sticky" : undefined,
                    left: i === 0 ? 0 : undefined,
                    zIndex: i === 0 ? 10 : undefined,
                    minWidth: i === 0 ? 130 : undefined,
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* Player rows */}
            {players.map((player) => (
              <Fragment key={player.playerId}>
                <tr
                  onClick={() => togglePlayer(player.playerId)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      togglePlayer(player.playerId);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  style={{
                    cursor: "pointer",
                    background: expandedPlayers.has(player.playerId)
                      ? "rgba(92, 58, 33, 0.3)"
                      : "transparent",
                  }}
                >
                  <td
                    style={{
                      ...tdStyle,
                      textAlign: "left",
                      fontWeight: 500,
                      position: "sticky",
                      left: 0,
                      zIndex: 10,
                      background: expandedPlayers.has(player.playerId)
                        ? "#3D2415"
                        : "#2C1810",
                      color: "#F5F0E8",
                    }}
                  >
                    {player.name}
                  </td>
                  <td style={tdStyle}>{formatMinutes(player.totals.min)}</td>
                  <td style={tdStyle}>{player.totals.fgm}-{player.totals.fga}</td>
                  <td style={tdStyle}>{player.totals.fg3m}-{player.totals.fg3a}</td>
                  <td style={tdStyle}>{player.totals.ftm}-{player.totals.fta}</td>
                  <td style={tdStyle}>{player.totals.oreb}</td>
                  <td style={tdStyle}>{player.totals.reb}</td>
                  <td style={tdStyle}>{player.totals.ast}</td>
                  <td style={tdStyle}>{player.totals.blk}</td>
                  <td style={tdStyle}>{player.totals.stl}</td>
                  <td style={tdStyle}>{player.totals.tov}</td>
                  <td style={tdStyle}>{player.totals.pf}</td>
                  <td style={{ ...tdStyle, fontWeight: 700, color: "#FF6B35" }}>{player.totals.pts}</td>
                  <td
                    style={{
                      ...tdStyle,
                      color: getPlusMinusColor(player.totals.plusMinus),
                      fontWeight: 600,
                    }}
                    data-testid={`plus-minus-${player.playerId}`}
                  >
                    {player.totals.plusMinus > 0 ? "+" : ""}{player.totals.plusMinus}
                  </td>
                  <td style={tdStyle}>{player.totals.hv}</td>
                  <td style={tdStyle}>{player.totals.prod.toFixed(2)}</td>
                  <td style={tdStyle}>{player.totals.eff}</td>
                </tr>
                {/* Stint breakdown - rendered as a full-width row */}
                {expandedPlayers.has(player.playerId) && (
                  <tr>
                    <td colSpan={17} style={{ padding: 0 }}>
                      <StintBreakdown stints={player.stints} />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}

            {/* Team Totals Row */}
            <tr
              style={{
                background: "rgba(201, 168, 76, 0.1)",
                borderTop: "2px solid #5C3A21",
              }}
            >
              <td
                style={{
                  ...tdStyle,
                  textAlign: "left",
                  fontWeight: 700,
                  position: "sticky",
                  left: 0,
                  zIndex: 10,
                  background: "#3D2415",
                  color: "#C9A84C",
                  borderBottom: "none",
                }}
              >
                Team Totals
              </td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>-</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>{teamTotals.fgm}-{teamTotals.fga}</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>{teamTotals.fg3m}-{teamTotals.fg3a}</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>{teamTotals.ftm}-{teamTotals.fta}</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>{teamTotals.oreb}</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>{teamTotals.reb}</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>{teamTotals.ast}</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>{teamTotals.blk}</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>{teamTotals.stl}</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>{teamTotals.tov}</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>{teamTotals.pf}</td>
              <td style={{ ...tdStyle, fontWeight: 700, color: "#FF6B35", borderBottom: "none" }}>{teamTotals.pts}</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>-</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>-</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>-</td>
              <td style={{ ...tdStyle, fontWeight: 700, borderBottom: "none" }}>-</td>
            </tr>

            {/* Period Breakdown Rows */}
            {periodTotals.map((period) => (
              <tr key={`period-${period.period}`}>
                <td
                  style={{
                    ...tdStyle,
                    textAlign: "left",
                    fontStyle: "italic",
                    position: "sticky",
                    left: 0,
                    zIndex: 10,
                    background: "#2C1810",
                    color: "#8B6914",
                    fontSize: 12,
                  }}
                >
                  Q{period.period}
                </td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>-</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>{period.fgm}-{period.fga}</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>{period.fg3m}-{period.fg3a}</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>{period.ftm}-{period.fta}</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>-</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>-</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>-</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>-</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>-</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>-</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>-</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>{period.pts}</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>-</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>-</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>-</td>
                <td style={{ ...tdStyle, fontSize: 12, color: "#8B6914" }}>-</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
