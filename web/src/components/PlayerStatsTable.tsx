import { Fragment, useState } from "react";
import { PlayerData, TeamTotals, PeriodTotals } from "@/types/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
 * Returns color class for +/- value
 */
function getPlusMinusColor(value: number): string {
  if (value > 0) return "text-green-600";
  if (value < 0) return "text-red-600";
  return "";
}

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

  return (
    <div className="mb-8">
      <div className="mb-4">
        <h2 className="text-xl font-bold">
          {teamName} ({teamTricode})
        </h2>
      </div>

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky left-0 z-10 bg-muted w-32">
                Player
              </TableHead>
              <TableHead>Min</TableHead>
              <TableHead>FG</TableHead>
              <TableHead>3PT</TableHead>
              <TableHead>FT</TableHead>
              <TableHead>OREB</TableHead>
              <TableHead>REB</TableHead>
              <TableHead>AST</TableHead>
              <TableHead>BLK</TableHead>
              <TableHead>STL</TableHead>
              <TableHead>TO</TableHead>
              <TableHead>PF</TableHead>
              <TableHead>PTS</TableHead>
              <TableHead>+/-</TableHead>
              <TableHead>HV</TableHead>
              <TableHead>PROD</TableHead>
              <TableHead>EFF</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {/* Player rows */}
            {players.map((player) => (
              <Fragment key={player.playerId}>
                <TableRow
                  onClick={() => togglePlayer(player.playerId)}
                  className="cursor-pointer hover:bg-muted/50"
                >
                  <TableCell className="sticky left-0 z-10 bg-white font-medium">
                    {player.name}
                  </TableCell>
                  <TableCell>{formatMinutes(player.totals.min)}</TableCell>
                  <TableCell>
                    {player.totals.fgm}-{player.totals.fga}
                  </TableCell>
                  <TableCell>
                    {player.totals.fg3m}-{player.totals.fg3a}
                  </TableCell>
                  <TableCell>
                    {player.totals.ftm}-{player.totals.fta}
                  </TableCell>
                  <TableCell>{player.totals.oreb}</TableCell>
                  <TableCell>{player.totals.reb}</TableCell>
                  <TableCell>{player.totals.ast}</TableCell>
                  <TableCell>{player.totals.blk}</TableCell>
                  <TableCell>{player.totals.stl}</TableCell>
                  <TableCell>{player.totals.tov}</TableCell>
                  <TableCell>{player.totals.pf}</TableCell>
                  <TableCell>{player.totals.pts}</TableCell>
                  <TableCell
                    className={getPlusMinusColor(player.totals.plusMinus)}
                    data-testid={`plus-minus-${player.playerId}`}
                  >
                    {player.totals.plusMinus}
                  </TableCell>
                  <TableCell>{player.totals.hv}</TableCell>
                  <TableCell>{player.totals.prod.toFixed(2)}</TableCell>
                  <TableCell>{player.totals.eff}</TableCell>
                </TableRow>
                {/* Stint breakdown - rendered as a full-width row */}
                {expandedPlayers.has(player.playerId) && (
                  <TableRow>
                    <TableCell colSpan={16} className="p-0">
                      <StintBreakdown stints={player.stints} />
                    </TableCell>
                  </TableRow>
                )}
              </Fragment>
            ))}

            {/* Team Totals Row */}
            <TableRow className="font-bold bg-muted/30">
              <TableCell className="sticky left-0 z-10 bg-muted/30 font-bold">
                Team Totals
              </TableCell>
              <TableCell>-</TableCell>
              <TableCell>
                {teamTotals.fgm}-{teamTotals.fga}
              </TableCell>
              <TableCell>
                {teamTotals.fg3m}-{teamTotals.fg3a}
              </TableCell>
              <TableCell>
                {teamTotals.ftm}-{teamTotals.fta}
              </TableCell>
              <TableCell>{teamTotals.oreb}</TableCell>
              <TableCell>{teamTotals.reb}</TableCell>
              <TableCell>{teamTotals.ast}</TableCell>
              <TableCell>{teamTotals.blk}</TableCell>
              <TableCell>{teamTotals.stl}</TableCell>
              <TableCell>{teamTotals.tov}</TableCell>
              <TableCell>{teamTotals.pf}</TableCell>
              <TableCell>{teamTotals.pts}</TableCell>
              <TableCell>-</TableCell>
              <TableCell>-</TableCell>
              <TableCell>-</TableCell>
              <TableCell>-</TableCell>
            </TableRow>

            {/* Period Breakdown Rows */}
            {periodTotals.map((period) => (
              <TableRow key={`period-${period.period}`} className="text-sm">
                <TableCell className="sticky left-0 z-10 bg-white italic">
                  Q{period.period}
                </TableCell>
                <TableCell>-</TableCell>
                <TableCell>
                  {period.fgm}-{period.fga}
                </TableCell>
                <TableCell>
                  {period.fg3m}-{period.fg3a}
                </TableCell>
                <TableCell>
                  {period.ftm}-{period.fta}
                </TableCell>
                <TableCell>-</TableCell>
                <TableCell>-</TableCell>
                <TableCell>-</TableCell>
                <TableCell>-</TableCell>
                <TableCell>-</TableCell>
                <TableCell>-</TableCell>
                <TableCell>-</TableCell>
                <TableCell>{period.pts}</TableCell>
                <TableCell>-</TableCell>
                <TableCell>-</TableCell>
                <TableCell>-</TableCell>
                <TableCell>-</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
