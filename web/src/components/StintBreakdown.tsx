import type { StintData } from "@/types/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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

export function StintBreakdown({ stints }: StintBreakdownProps) {
  return (
    <div className="bg-muted/30 p-3 ml-4">
      <Table className="text-xs">
        <TableHeader>
          <TableRow>
            <TableHead className="px-2 py-1">Period</TableHead>
            <TableHead className="px-2 py-1">In</TableHead>
            <TableHead className="px-2 py-1">Out</TableHead>
            <TableHead className="px-2 py-1">Min</TableHead>
            <TableHead className="px-2 py-1">FG</TableHead>
            <TableHead className="px-2 py-1">3PT</TableHead>
            <TableHead className="px-2 py-1">FT</TableHead>
            <TableHead className="px-2 py-1">OREB</TableHead>
            <TableHead className="px-2 py-1">REB</TableHead>
            <TableHead className="px-2 py-1">AST</TableHead>
            <TableHead className="px-2 py-1">BLK</TableHead>
            <TableHead className="px-2 py-1">STL</TableHead>
            <TableHead className="px-2 py-1">TO</TableHead>
            <TableHead className="px-2 py-1">PF</TableHead>
            <TableHead className="px-2 py-1">PTS</TableHead>
            <TableHead className="px-2 py-1">+/-</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {stints.map((stint, idx) => (
            <TableRow key={idx} className="text-xs">
              <TableCell className="px-2 py-1">{stint.period}</TableCell>
              <TableCell className="px-2 py-1">{stint.inTime}</TableCell>
              <TableCell className="px-2 py-1">{stint.outTime}</TableCell>
              <TableCell className="px-2 py-1">
                {formatMinutes(stint.minutes)}
              </TableCell>
              <TableCell className="px-2 py-1">
                {stint.fgm}-{stint.fga}
              </TableCell>
              <TableCell className="px-2 py-1">
                {stint.fg3m}-{stint.fg3a}
              </TableCell>
              <TableCell className="px-2 py-1">
                {stint.ftm}-{stint.fta}
              </TableCell>
              <TableCell className="px-2 py-1">{stint.oreb}</TableCell>
              <TableCell className="px-2 py-1">{stint.reb}</TableCell>
              <TableCell className="px-2 py-1">{stint.ast}</TableCell>
              <TableCell className="px-2 py-1">{stint.blk}</TableCell>
              <TableCell className="px-2 py-1">{stint.stl}</TableCell>
              <TableCell className="px-2 py-1">{stint.tov}</TableCell>
              <TableCell className="px-2 py-1">{stint.pf}</TableCell>
              <TableCell className="px-2 py-1">{stint.pts}</TableCell>
              <TableCell className="px-2 py-1">{stint.plusMinus}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
