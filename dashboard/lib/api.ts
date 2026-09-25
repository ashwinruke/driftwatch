// Types mirror driftwatch/dashboard/schemas.py exactly -- keep them in
// sync by hand (no shared codegen for this MVP pass, see docs/roadmap.md's
// Phase 6 report).

export type OverviewResponse = {
  total_repositories: number;
  total_review_runs: number;
  total_prs_reviewed: number;
  total_findings: number;
  accepted_findings: number;
  rejected_findings: number;
  needs_review_findings: number;
  validation_acceptance_rate: number | null;
  average_review_latency_seconds: number | null;
  findings_by_category: Record<string, number>;
  findings_by_severity: Record<string, number>;
};

export type RepositorySummary = {
  id: number;
  full_name: string;
  default_branch: string | null;
  review_count: number;
  findings_count: number;
  validation_acceptance_rate: number | null;
  last_review: string | null;
};

export type ReviewRunSummary = {
  id: number;
  pr_number: number;
  pr_title: string | null;
  pr_author: string | null;
  run_type: string;
  status: string;
  started_at: string;
  completed_at: string | null;
};

export type RepositoryDetail = {
  id: number;
  full_name: string;
  default_branch: string | null;
  total_reviews: number;
  total_findings: number;
  last_review: string | null;
  recent_reviews: ReviewRunSummary[];
};

export type FindingSummary = {
  id: string;
  category: string;
  severity: string;
  file_path: string;
  start_line: number;
  end_line: number;
  title: string;
  validation_status: string;
  validation_score: number | null;
  static_corroborated: boolean;
};

export type ReviewStats = {
  files_analyzed: number;
  candidate_findings: number;
  accepted: number;
  rejected: number;
  needs_review: number;
  comments_posted: number;
};

export type ReviewDetail = {
  id: number;
  repository_id: number;
  repository_full_name: string;
  pr_number: number;
  pr_title: string | null;
  pr_author: string | null;
  head_sha: string | null;
  run_type: string;
  status: string;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  stats: ReviewStats;
  findings: FindingSummary[];
};

export type EvidenceItem = {
  source: string;
  description: string;
  file_path: string | null;
  start_line: number | null;
  end_line: number | null;
  rule_id: string | null;
};

export type ValidationBreakdown = {
  diff_evidence: number | null;
  static_corroboration: number | null;
  ast_consistency: number | null;
  llm_confidence: number | null;
  final_score: number;
};

export type CommentRef = {
  comment_type: string;
  github_comment_id: number | null;
  github_url: string | null;
  posted_at: string;
};

export type FindingDetail = {
  id: string;
  review_run_id: number;
  repository_id: number;
  category: string;
  severity: string;
  file_path: string;
  start_line: number;
  end_line: number;
  title: string;
  description: string;
  suggested_fix: string | null;
  validation_status: string;
  validation_score: number | null;
  llm_confidence: number | null;
  validation_reasons: string[];
  evidence: EvidenceItem[];
  validation_breakdown: ValidationBreakdown | null;
  comment: CommentRef | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function getOverview(): Promise<OverviewResponse> {
  return apiGet<OverviewResponse>("/dashboard/overview");
}

export async function listRepositories(): Promise<RepositorySummary[]> {
  return apiGet<RepositorySummary[]>("/repositories");
}

export async function getRepositoryDetail(id: string): Promise<RepositoryDetail | null> {
  try {
    return await apiGet<RepositoryDetail>(`/repositories/${id}`);
  } catch {
    return null;
  }
}

export async function getReviewDetail(id: string): Promise<ReviewDetail | null> {
  try {
    return await apiGet<ReviewDetail>(`/reviews/${id}`);
  } catch {
    return null;
  }
}

export async function getFindingDetail(id: string): Promise<FindingDetail | null> {
  try {
    return await apiGet<FindingDetail>(`/findings/${id}`);
  } catch {
    return null;
  }
}
