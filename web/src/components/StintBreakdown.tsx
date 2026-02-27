import type { StintData } from "@/types/api";

interface StintBreakdownProps {
  stints: StintData[];
}

/**
 * Formats minutes as M:SS from decimal minutes
 */
function formatMinutes(decimalMinutes: number): string {
  const minutes = Math.floor(decimalMinutes);
  const seconds = Math.round((decimalMinutes - minutes) * 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

const stintThStyle: React.CSSProperties = {
  padding: "3px 6px",
  textAlign: "center",
  fontFamily: "'Oswald', sans-serif",
  fontSize: 10,
  fontWeight: 600,
  color: "#8B6914",
  textTransform: "uppercase",
  borderBottom: "1px solid rgba(92, 58, 33, 0.4)",
};

const stintTdStyle: React.CSSProperties = {
  padding: "2px 6px",
  textAlign: "center",
  fontSize: 11,
  fontFamily: "'Roboto Condensed', Arial",
  color: "#C4956A",
  borderBottom: "1px solid rgba(92, 58, 33, 0.2)",
};

export function StintBreakdown({ stints }: StintBreakdownProps) {
  const headers = ["Period", "In", "Out", "Min", "FG", "3PT", "FT", "OREB", "REB", "AST", "BLK", "STL", "TO", "PF", "PTS", "+/-"];

  return (
    <div
      style={{
        background: "rgba(44, 24, 16, 0.5)",
        padding: "8px 0 8px 16px",
        borderLeft: "3px solid #C9A84C",
      }}
    >
      <table style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h} style={stintThStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {stints.map((stint, idx) => (
            <tr key={idx}>
              <td style={stintTdStyle}>{stint.period}</td>
              <td style={stintTdStyle}>{stint.inTime}</td>
              <td style={stintTdStyle}>{stint.outTime}</td>
              <td style={stintTdStyle}>{formatMinutes(stint.minutes)}</td>
              <td style={stintTdStyle}>{stint.fgm}-{stint.fga}</td>
              <td style={stintTdStyle}>{stint.fg3m}-{stint.fg3a}</td>
              <td style={stintTdStyle}>{stint.ftm}-{stint.fta}</td>
              <td style={stintTdStyle}>{stint.oreb}</td>
              <td style={stintTdStyle}>{stint.reb}</td>
              <td style={stintTdStyle}>{stint.ast}</td>
              <td style={stintTdStyle}>{stint.blk}</td>
              <td style={stintTdStyle}>{stint.stl}</td>
              <td style={stintTdStyle}>{stint.tov}</td>
              <td style={stintTdStyle}>{stint.pf}</td>
              <td style={{ ...stintTdStyle, fontWeight: 600, color: "#FF6B35" }}>{stint.pts}</td>
              <td
                style={{
                  ...stintTdStyle,
                  fontWeight: 600,
                  color: stint.plusMinus > 0 ? "#4ade80" : stint.plusMinus < 0 ? "#f87171" : "#C4956A",
                }}
              >
                {stint.plusMinus > 0 ? "+" : ""}{stint.plusMinus}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
