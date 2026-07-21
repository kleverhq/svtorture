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
import type { Campaign, CaseDefinition, Requirement, Result } from "./types";

interface MatrixProps {
  requirements: Requirement[];
  cases: CaseDefinition[];
  campaign?: Campaign | undefined;
  toolFilter: string;
  onInspectCase: (caseId: string) => void;
}

const helper = createColumnHelper<Requirement>();

export function MatrixView({
  requirements,
  cases,
  campaign,
  toolFilter,
  onInspectCase,
}: MatrixProps) {
  const parentRef = useRef<HTMLDivElement>(null);
  const [selectedRequirementId, setSelectedRequirementId] = useState("");
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
          <span className="matrix__clause">{context.getValue()}</span>
        ),
      }),
      helper.accessor("summary", {
        header: "Requirement",
        cell: (context) => (
          <button
            type="button"
            className="matrix__requirement"
            aria-pressed={selectedRequirementId === context.row.original.id}
            title={context.getValue()}
            onClick={() => setSelectedRequirementId(context.row.original.id)}
          >
            <strong>{context.row.original.id}</strong>
            <span>{context.getValue()}</span>
          </button>
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
            return <StatusBadge status={status} reason={reasons} grouped />;
          },
        }),
      ),
    ],
    [casesByRequirement, profiles, resultMap, selectedRequirementId],
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
    estimateSize: () => 54,
    overscan: 10,
  });
  const template = [
    "112px",
    "minmax(320px, 1fr)",
    ...profiles.map(() => "minmax(128px, 148px)"),
  ].join(" ");
  const selectedRequirement = requirements.find(
    (requirement) => requirement.id === selectedRequirementId,
  );
  const supporting = selectedRequirement
    ? (casesByRequirement.get(selectedRequirement.id) ?? [])
    : [];

  return (
    <section className="panel matrix" aria-labelledby="matrix-title">
      <div className="panel__heading panel__heading--compact">
        <div>
          <h2 id="matrix-title">Requirements matrix</h2>
          <span>
            {requirements.length} requirements · {cases.length} cases · {profiles.length}{" "}
            profiles
          </span>
        </div>
      </div>
      <div className={`matrix__workspace ${selectedRequirement ? "has-inspector" : ""}`}>
        <div className="matrix__scroll" ref={parentRef}>
          <div className="matrix__header" style={{ gridTemplateColumns: template }}>
            {table.getHeaderGroups()[0]?.headers.map((header) => (
              <div key={header.id}>
                {flexRender(header.column.columnDef.header, header.getContext())}
              </div>
            ))}
          </div>
          {rows.length ? (
            <div
              className="matrix__body"
              style={{ height: `${virtualizer.getTotalSize()}px` }}
            >
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const row = rows[virtualRow.index];
                if (!row) return null;
                return (
                  <div
                    key={row.id}
                    className={`matrix__row ${
                      row.original.id === selectedRequirementId ? "is-selected" : ""
                    }`}
                    style={{
                      height: `${virtualRow.size}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                      gridTemplateColumns: template,
                    }}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <div className="matrix__cell" key={cell.id}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">No requirements match the current filters.</div>
          )}
        </div>

        {selectedRequirement && (
          <aside className="matrix-inspector" aria-label="Requirement inspector">
            <header>
              <div>
                <span>Clause {selectedRequirement.clause}</span>
                <strong>{selectedRequirement.id}</strong>
              </div>
              <button
                type="button"
                className="icon-button"
                aria-label="Close requirement inspector"
                onClick={() => setSelectedRequirementId("")}
              >
                ×
              </button>
            </header>
            <p>{selectedRequirement.summary}</p>
            <section>
              <h3>Standard anchors</h3>
              <ul className="anchor-list">
                {selectedRequirement.anchors.map((anchor) => (
                  <li key={anchor}>
                    <code>{anchor}</code>
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <h3>Supporting cases</h3>
              <div className="inspector-cases">
                {supporting.length ? (
                  supporting.map((testCase) => (
                    <button
                      type="button"
                      key={testCase.id}
                      onClick={() => onInspectCase(testCase.id)}
                    >
                      <span>
                        {testCase.target_phase} · {testCase.expectation}
                      </span>
                      <strong>{testCase.title}</strong>
                      <code>{testCase.id}</code>
                    </button>
                  ))
                ) : (
                  <p>No case currently maps to this requirement.</p>
                )}
              </div>
            </section>
          </aside>
        )}
      </div>
    </section>
  );
}
