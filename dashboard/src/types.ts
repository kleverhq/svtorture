export type Status =
  | "conforming"
  | "nonconforming"
  | "inconclusive"
  | "unsupported-capability"
  | "unsupported-revision"
  | "not-applicable"
  | "skipped-unavailable"
  | "harness-error"
  | "not-run";

export interface RevisionRule {
  status: string;
  clause?: string | null;
  note?: string | null;
}

export interface StandardSection {
  clause: string;
  title: string;
}

export interface Requirement {
  id: string;
  standard_revision: string;
  part: string;
  clause: string;
  anchors: string[];
  summary: string;
  related_clauses: string[];
  tags: string[];
  revision_applicability: Record<string, RevisionRule>;
}

export interface Oracle {
  kind: string;
  marker?: string | null;
  anchor?: string | null;
}

export interface CaseDefinition {
  id: string;
  title: string;
  description: string;
  primary_requirement: string;
  related_requirements: string[];
  standard_revision: string;
  revision_applicability: Record<string, string>;
  target_phase: string;
  expectation: string;
  evidence: string;
  sources: string[];
  source_links?: Record<string, string>;
  top?: string | null;
  defines: string[];
  include_dirs: string[];
  runtime_args: string[];
  oracle: Oracle;
  tags: string[];
  content_sha256: string;
  definition_sha256?: string;
}

export interface CapturedStream {
  excerpt: string;
  size_bytes: number;
  sha256: string;
  truncated: boolean;
}

export interface Diagnostic {
  severity: string;
  message: string;
  source?: string | null;
  line?: number | null;
  column?: number | null;
  code?: string | null;
  target_case_id?: string | null;
}

export interface Observation {
  stage_id: string;
  kind: "compile" | "run";
  attempted_through_phase: string;
  outcome: string;
  exit_code?: number | null;
  signal?: number | null;
  duration_seconds: number;
  stdout: CapturedStream;
  stderr: CapturedStream;
  diagnostics: Diagnostic[];
  internal_error: boolean;
  artifact_present?: boolean | null;
  portable_argv: string[];
}

export interface Result {
  case_id: string;
  requirement_id: string;
  tool_id: string;
  profile_id: string;
  target_phase: string;
  evidence_mode: "direct" | "cumulative" | "not-observed";
  status: Status;
  reason: string;
  summary: string;
  evidence: string;
  observations: Observation[];
  known_issue?: string | null;
  reproduction_command?: string | null;
}

export interface ToolProfile {
  id: string;
  phase_ceiling: string;
  direct_phases: string[];
  headline: boolean;
  standard_revision: string;
  effective_language: string;
}

export interface ToolDefinition {
  id: string;
  display_name: string;
  distribution: string;
  execution: string;
  ci: boolean;
  publish: boolean;
  profiles: ToolProfile[];
}

export interface ToolSelection {
  requested_ref: string;
  resolved_sha: string;
  resolved_at: string;
  exact_tags: string[];
  nearest_tag?: string | null;
  default_branch?: string | null;
}

export interface ImageIdentity {
  reference: string;
  image_id?: string | null;
  digest?: string | null;
  recipe_sha256: string;
  base_image: string;
  base_image_digest?: string | null;
  platform: string;
}

export interface CorpusRatio {
  numerator: number;
  denominator: number;
}

export interface CorpusPartMetric {
  kind: "chapter" | "annex";
  id: string;
  title: string;
  coverage: CorpusRatio;
  density: CorpusRatio;
  waived: number;
}

export interface CorpusMetricSummary {
  coverage: CorpusRatio;
  density: CorpusRatio;
  breakdown: CorpusPartMetric[];
}

export interface CorpusMetrics {
  requirements: CorpusMetricSummary;
  cases: CorpusMetricSummary;
}

export interface CampaignTool {
  definition: ToolDefinition;
  selection?: ToolSelection | null;
  image?: ImageIdentity | null;
  reported_version?: string | null;
  profile_ids: string[];
  preparation_error?: string | null;
}

export interface Campaign {
  schema_version: 5;
  id: string;
  started_at: string;
  finished_at: string;
  repository: { commit: string; dirty: boolean };
  platform: string;
  selection_name: string;
  case_ids: string[];
  tools: CampaignTool[];
  expected_tool_ids: string[];
  missing_tool_ids: string[];
  hashes: { requirements: string; cases: string; selection: string };
  corpus_metrics: CorpusMetrics;
  results: Result[];
  complete: boolean;
  trust: {
    source: string;
    repository?: string | null;
    workflow_run_id?: string | null;
    checkout_sha?: string | null;
  };
}

export interface MetricPoint {
  label: string;
  revision: string;
  tool_id: string;
  profile_id: string;
  numerator: number;
  denominator: number;
  corpus_sha: string;
  complete: boolean;
  valid: boolean;
  corpus_coverage: number;
  execution_coverage: number;
  conforming: number;
  nonconforming: number;
  inconclusive: number;
  unsupported: number;
  infrastructure_state: string;
  campaign_id: string;
  timestamp: string;
  tool_sha?: string | null;
  exact_tags: string[];
  nearest_tag?: string | null;
  reported_version?: string | null;
  image_digest?: string | null;
  repository_commit: string;
}

export type CorpusCoverage = CorpusMetrics;

export interface Dataset {
  schema_version: 5;
  generated_from: string[];
  visibility: "local" | "public";
  corpus_coverage: CorpusCoverage;
  standard_sections: StandardSection[];
  requirements: Requirement[];
  cases: CaseDefinition[];
  campaigns: Campaign[];
  metrics: MetricPoint[];
}

export interface ResourceReference {
  href: string;
  sha256: string;
  bytes: number;
}

export interface CountedResourceReference extends ResourceReference {
  case_count: number;
  result_count: number;
}

export type DashboardMetric = Omit<
  MetricPoint,
  "campaign_id" | "timestamp" | "repository_commit"
>;

export interface CampaignManifest {
  schema_version: 6;
  kind: "campaign-manifest";
  id: string;
  started_at: string;
  finished_at: string;
  repository: { commit: string; dirty: boolean };
  platform: string;
  selection_name: string;
  cases: Array<{
    id: string;
    content_sha256: string;
    definition_sha256: string;
  }>;
  tools: CampaignTool[];
  expected_tool_ids: string[];
  missing_tool_ids: string[];
  hashes: Campaign["hashes"];
  corpus_metrics: CorpusMetrics;
  metrics: DashboardMetric[];
  complete: boolean;
  trust: Campaign["trust"];
  resources: {
    catalog: ResourceReference;
    verdicts: CountedResourceReference;
    evidence: CountedResourceReference[];
  };
}

export interface CampaignCatalog {
  schema_version: 6;
  kind: "campaign-catalog";
  campaign_id: string;
  requirements: Requirement[];
  cases: CaseDefinition[];
  corpus_metrics: CorpusMetrics;
  standard_sections?: StandardSection[];
}

export interface CampaignVerdict {
  tool_id: string;
  profile_id: string;
  status: Status;
  reason: string;
  evidence_mode: Result["evidence_mode"];
  summary: string;
  known_issue?: string | null;
}

export interface CampaignVerdicts {
  schema_version: 6;
  kind: "campaign-verdicts";
  campaign_id: string;
  case_count: number;
  result_count: number;
  cases: Array<{
    case_id: string;
    evidence_href: string;
    results: CampaignVerdict[];
  }>;
}

export interface CampaignEvidence {
  schema_version: 6;
  kind: "campaign-evidence";
  campaign_id: string;
  case_ids: string[];
  results: Result[];
}

export interface ArchiveMetadata {
  release_tag: string;
  release_url: string;
  asset_name: string;
  download_url: string;
  sha256: string;
  bytes: number;
}

export interface CampaignSummary {
  schema_version: 6;
  kind: "campaign-summary";
  id: string;
  started_at: string;
  finished_at: string;
  complete: boolean;
  repository: { commit: string };
  trust: Campaign["trust"];
  hashes: Campaign["hashes"];
  corpus_metrics: CorpusMetrics;
  tool_metrics: DashboardMetric[];
  archive?: ArchiveMetadata;
}

export interface CampaignTrends {
  schema_version: 6;
  kind: "campaign-trends";
  campaigns: CampaignSummary[];
}

export interface DashboardIndex {
  schema_version: 6;
  kind: "dashboard-index";
  default_campaign_id: string;
  campaigns: Array<{ id: string; manifest: string }>;
  trends: string;
  schemas: {
    summary: string;
    trends: string;
    campaign: string;
    catalog: string;
    verdicts: string;
    evidence: string;
  };
}
