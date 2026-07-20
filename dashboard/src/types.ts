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

export interface Requirement {
  id: string;
  standard_revision: string;
  chapter: number;
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
  phase: string;
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
  phases: string[];
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

export interface CampaignTool {
  definition: ToolDefinition;
  selection?: ToolSelection | null;
  image?: ImageIdentity | null;
  reported_version?: string | null;
  profile_ids: string[];
  preparation_error?: string | null;
}

export interface Campaign {
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

export interface Dataset {
  schema_version: number;
  generated_from: string[];
  visibility: "local" | "public";
  requirements: Requirement[];
  cases: CaseDefinition[];
  campaigns: Campaign[];
  metrics: MetricPoint[];
}
