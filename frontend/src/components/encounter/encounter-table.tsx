import * as React from "react";
import { useNavigate } from "react-router-dom";
import { Search, ChevronRight, Inbox } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge, urgencyBadgeVariant } from "@/components/ui/badge";
import { StatusBadge } from "@/components/encounter/status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { formatDateTime, titleCase } from "@/lib/utils";
import type { EncounterRow } from "@/types/domain";

interface EncounterQueueTableProps {
  encounters: EncounterRow[];
  searchable?: boolean;
  emptyMessage?: string;
  /** Optional extra column renderer, e.g. billing amount or follow-up due date */
  extraColumn?: {
    header: string;
    render: (encounter: EncounterRow) => React.ReactNode;
  };
}

export function EncounterQueueTable({
  encounters,
  searchable = true,
  emptyMessage = "No encounters match this view yet.",
  extraColumn,
}: EncounterQueueTableProps) {
  const [query, setQuery] = React.useState("");
  const navigate = useNavigate();

  const filtered = React.useMemo(() => {
    if (!query.trim()) return encounters;
    const q = query.trim().toLowerCase();
    return encounters.filter((e) => {
      return (
        e.patient.full_name.toLowerCase().includes(q) ||
        (e.patient.phone ?? "").toLowerCase().includes(q) ||
        (e.pathway ?? "").toLowerCase().includes(q) ||
        (e.urgency ?? "").toLowerCase().includes(q)
      );
    });
  }, [encounters, query]);

  return (
    <div className="space-y-3">
      {searchable && (
        <div className="relative max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by patient, phone, pathway, urgency…"
            className="pl-9"
            aria-label="Search encounters"
          />
        </div>
      )}

      {filtered.length === 0 ? (
        <EmptyState
          icon={<Inbox className="size-6" />}
          title="Nothing here right now"
          description={emptyMessage}
        />
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Patient</TableHead>
                <TableHead>Age</TableHead>
                <TableHead>Urgency</TableHead>
                <TableHead>Care pathway</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                {extraColumn && <TableHead>{extraColumn.header}</TableHead>}
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((encounter) => (
                <TableRow
                  key={encounter.id}
                  tabIndex={0}
                  className="cursor-pointer focus-visible:bg-muted/50"
                  onClick={() => navigate(`/dashboard/encounters/${encounter.id}`)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") navigate(`/dashboard/encounters/${encounter.id}`);
                  }}
                >
                  <TableCell className="font-medium text-foreground">
                    {encounter.patient.full_name}
                  </TableCell>
                  <TableCell className="tabular-nums text-muted-foreground">
                    {encounter.age ?? "—"}
                  </TableCell>
                  <TableCell>
                    <Badge variant={urgencyBadgeVariant(encounter.urgency)} dot>
                      {encounter.urgency ? titleCase(encounter.urgency) : "Pending"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {encounter.pathway ? titleCase(encounter.pathway) : "—"}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={encounter.status} />
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {formatDateTime(encounter.created_at)}
                  </TableCell>
                  {extraColumn && <TableCell>{extraColumn.render(encounter)}</TableCell>}
                  <TableCell className="text-right">
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/dashboard/encounters/${encounter.id}`);
                      }}
                    >
                      View
                      <ChevronRight className="size-3.5" />
                    </button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
