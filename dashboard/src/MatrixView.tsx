import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useMemo, useRef, useState } from "react";

import { aggregateStatus, profileKeys, resultsByKey } from "./model";
import { StatusBadge } from "./StatusBadge";
import type {
  Campaign,
  CaseDefinition,
  Requirement,
  Result,
} from "./types";

interface MatrixProps {
  requirements: Requirement[];
  cases: CaseDefinition[];
  campaign?: Campaign | undefined;
  toolFilter: string;
}

const helper = createColumnHelper<Requirement>();

export function MatrixView({
  requirements,
  cases,
  campaign,
  toolFilter,
}: MatrixProps) {
  const parentRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const resultMap = useMemo(() => resultsByKey(campaign), [campaign]);
  const profiles = profileKeys(campaign).filter(
    (profile) => !toolFilter || profile === toolFilter,
  );
  const casesByRequirement = useMemo(() => {
    const result = new Map<string, CaseDefinition[]>();
    for (const testCase of cases) {
      const values = result.get(testCase.primary_requirement) ?? [];
      values.push(testCase);
      result.set(testCase.primary_requirement, values);
    }
    return result;
  }, [cases]);
  const columns = useMemo(
    () => [
      helper.accessor("clause", {
        header: "Clause",
        cell: (context) => (
          <button
            type="button"
            className="matrix__expand"
            aria-expanded={expanded.has(context.row.original.id)}
            onClick={() =>
              setExpanded((current) => {
                const next = new Set(current);
                if (next.has(context.row.original.id)) next.delete(context.row.original.id);
                else next.add(context.row.original.id);
                return next;
              })
            }
          >
            <span aria-hidden="true">
              {expanded.has(context.row.original.id) ? "▾" : "▸"}
            </span>
            <span>
              Ch. {context.row.original.chapter} · {context.getValue()}
            </span>
          </button>
        ),
      }),
      helper.accessor("summary", {
        header: "Normative requirement",
        cell: (context) => (
          <div>
            <strong className="matrix__requirement-id">{context.row.original.id}</strong>
            <span>{context.getValue()}</span>
          </div>
        ),
      }),
      ...profiles.map((profileKey) =>
        helper.display({
          id: profileKey,
          header: profileKey,
          cell: (context) => {
            const [toolId = "", profileId = ""] = profileKey.split("/");
            const supporting = casesByRequirement.get(context.row.original.id) ?? [];
            const results = supporting.map((testCase) =>
              resultMap.get(`${testCase.id}:${toolId}:${profileId}`),
            );
            const status = aggregateStatus(results);
            const reasons = results
              .filter((result): result is Result => Boolean(result))
              .map((result) => result.reason)
              .join(", ");
            return <StatusBadge status={status} reason={reasons} />;
          },
        }),
      ),
    ],
    [casesByRequirement, expanded, profiles, resultMap],
  );
  const table = useReactTable({
    data: requirements,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });
  const rows = table.getRowModel().rows;
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: (index) => (expanded.has(rows[index]?.original.id ?? "") ? 255 : 78),
    overscan: 8,
  });
  const template = `150px minmax(340px, 1fr) repeat(${profiles.length}, minmax(150px, 190px))`;

  return (
    <section className="panel matrix" aria-labelledby="matrix-title">
      <div className="panel__heading">
        <div>
          <span className="eyebrow">Primary view</span>
          <h2 id="matrix-title">Requirements matrix</h2>
        </div>
        <p>
          {requirements.length} requirements · {cases.length} supporting cases. A
          requirement passes only when every mandatory variant passes.
        </p>
      </div>
      <div className="matrix__scroll" ref={parentRef}>
        <div className="matrix__header" style={{ gridTemplateColumns: template }}>
          {table.getHeaderGroups()[0]?.headers.map((header) => (
            <div key={header.id}>
              {flexRender(header.column.columnDef.header, header.getContext())}
            </div>
          ))}
        </div>
        <div
          className="matrix__body"
          style={{ height: `${virtualizer.getTotalSize()}px` }}
        >
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const row = rows[virtualRow.index];
            if (!row) return null;
            const supporting = casesByRequirement.get(row.original.id) ?? [];
            return (
              <div
                key={row.id}
                ref={virtualizer.measureElement}
                data-index={virtualRow.index}
                className="matrix__row"
                style={{
                  transform: `translateY(${virtualRow.start}px)`,
                  gridTemplateColumns: template,
                }}
              >
                {row.getVisibleCells().map((cell) => (
                  <div className="matrix__cell" key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </div>
                ))}
                {expanded.has(row.original.id) && (
                  <div className="matrix__support" style={{ gridColumn: "1 / -1" }}>
                    <div>
                      <strong>Standard anchors</strong>
                      <ul>
                        {row.original.anchors.map((anchor) => (
                          <li key={anchor}>{anchor}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="matrix__cases">
                      {supporting.length ? (
                        supporting.map((testCase) => (
                          <article key={testCase.id}>
                            <div>
                              <span className="phase">{testCase.target_phase}</span>
                              <span className="phase">{testCase.expectation}</span>
                            </div>
                            <strong>{testCase.id}</strong>
                            <span>{testCase.title}</span>
                          </article>
                        ))
                      ) : (
                        <p>No case currently maps to this requirement.</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
