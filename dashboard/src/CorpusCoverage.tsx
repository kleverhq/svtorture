import type { CorpusCoverageMetric, CorpusRatio } from "./types";

export type CorpusCoverageKind = "requirements" | "cases";

interface CorpusCoverageProps {
  kind: CorpusCoverageKind;
  metric: CorpusCoverageMetric;
}

const INTEGER_FORMAT = new Intl.NumberFormat("en-US");
const PERCENT_FORMAT = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 2,
});
const DENSITY_FORMAT = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2,
});

function formatPercentage(ratio: CorpusRatio): string {
  if (ratio.denominator === 0) return "—";
  return PERCENT_FORMAT.format(ratio.numerator / ratio.denominator);
}

function formatDensity(ratio: CorpusRatio): string {
  if (ratio.denominator === 0) return "—";
  return DENSITY_FORMAT.format(ratio.numerator / ratio.denominator);
}

function formatOperands(ratio: CorpusRatio): string {
  return `${INTEGER_FORMAT.format(ratio.numerator)} / ${INTEGER_FORMAT.format(
    ratio.denominator,
  )}`;
}

function formulaCopy(
  kind: CorpusCoverageKind,
  metric: CorpusCoverageMetric,
): { coverage: string; density: string } {
  const coverageValue = formatPercentage(metric.coverage);
  const densityValue = formatDensity(metric.density);
  if (kind === "requirements") {
    return {
      coverage:
        "Coverage = unique referenced anchors / all standard anchors × 100. " +
        `${formatOperands(metric.coverage)} × 100 = ${coverageValue}.`,
      density:
        "Density = unique requirement–anchor links / unique referenced anchors. " +
        `${formatOperands(metric.density)} = ${densityValue} requirements per covered anchor.`,
    };
  }
  return {
    coverage:
      "Coverage = unique requirements linked from cases / all catalog requirements × 100. " +
      `${formatOperands(metric.coverage)} × 100 = ${coverageValue}.`,
    density:
      "Density = unique case–requirement links / unique covered requirements. " +
      `${formatOperands(metric.density)} = ${densityValue} cases per covered requirement.`,
  };
}

export function CorpusCoverage({ kind, metric }: CorpusCoverageProps) {
  const label = kind === "requirements" ? "Requirement" : "Case";
  const formulaId = `${kind}-corpus-coverage-formulas`;
  const formulas = formulaCopy(kind, metric);

  return (
    <section
      className="corpus-coverage"
      aria-label={`${label} corpus coverage`}
    >
      <details>
        <summary aria-describedby={formulaId}>
          <span
            className="corpus-coverage__metric"
            title={formulas.coverage}
          >
            <span>Coverage</span>
            <strong>{formatPercentage(metric.coverage)}</strong>
          </span>
          <span className="corpus-coverage__metric" title={formulas.density}>
            <span>Density</span>
            <strong>{formatDensity(metric.density)}</strong>
          </span>
          <span className="corpus-coverage__disclosure">
            Breakdown
            <span className="corpus-coverage__chevron" aria-hidden="true">
              ▾
            </span>
          </span>
        </summary>
        <span id={formulaId} className="visually-hidden">
          {formulas.coverage} {formulas.density}
        </span>
        <div className="corpus-coverage__table-wrap">
          <table className="corpus-coverage__table">
            <caption className="visually-hidden">
              {label} coverage and density by standard chapter and annex
            </caption>
            <thead>
              <tr>
                <th scope="col">Part</th>
                <th scope="col">Coverage</th>
                <th scope="col">Density</th>
              </tr>
            </thead>
            <tbody>
              {metric.breakdown.map((part) => (
                <tr key={`${part.kind}:${part.id}`}>
                  <th
                    scope="row"
                    aria-label={`${part.kind === "chapter" ? "Chapter" : "Annex"} ${part.id}: ${part.title}`}
                  >
                    <span className="corpus-coverage__part-id">
                      {part.kind === "chapter" ? "Chapter" : "Annex"} {part.id}
                    </span>
                    <span className="corpus-coverage__part-title">
                      {part.title}
                    </span>
                  </th>
                  <td>
                    <strong>{formatPercentage(part.coverage)}</strong>
                    <small>{formatOperands(part.coverage)}</small>
                  </td>
                  <td>
                    <strong>{formatDensity(part.density)}</strong>
                    <small>{formatOperands(part.density)}</small>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
