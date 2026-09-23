# AI Code Reviewer — Agent-Readable Engineering Specification

**Version:** 1.1 — includes multi-repository observability dashboard

**Project:** DriftWatch → AI Code Reviewer  
**Repository:** `https://github.com/ashwinruke/driftwatch`  
**Document type:** Engineering specification for coding agents such as Codex and Claude Code  
**Primary goal:** Extend the existing DriftWatch GitHub bot into an evidence-grounded AI code review system that analyzes pull requests, detects bugs/security/code-quality problems, validates findings using independent evidence, and posts useful inline PR comments plus a measurable review summary.

---

## 1. Executive Summary

Build an AI-powered GitHub Pull Request reviewer that operates directly inside GitHub.

For each eligible pull request, the system should:

1. Receive a GitHub webhook.
2. Fetch the PR metadata and diff.
3. Determine the changed files/functions/classes.
4. Run deterministic/static analysis tools.
5. Ask an LLM to reason about potential bugs, security problems, and code-quality issues.
6. Normalize all findings into a common schema.
7. Run every candidate finding through a **validation layer**.
8. Post only validated, actionable findings as inline PR comments.
9. Post a concise PR-level review summary.
10. Record structured evaluation/observability data for later measurement.

The core differentiator is **validated AI review**:

> The LLM is not allowed to be the final authority. A candidate finding must be supported by code evidence and/or independent analysis before it is posted.

The project is intended to be a recruiter-facing proof of work. The primary demo should therefore show:

- A real GitHub pull request.
- Inline AI review comments attached to exact lines.
- Evidence explaining why each comment was produced.
- A PR summary containing review statistics.
- A metrics/evaluation report demonstrating false-positive performance.

---

# 2. Existing Repository Baseline

The existing `driftwatch` repository already implements a GitHub documentation-drift workflow.

Current repository capabilities include:

- FastAPI webhook handling.
- GitHub App authentication.
- PR diff extraction.
- `tree-sitter` AST-based function/class extraction.
- Embedding-based matching.
- PostgreSQL + pgvector.
- LLM-based documentation-drift verification/drafting.
- PR commenting.
- Incremental documentation indexing.
- Retry handling.

The current repository structure includes modules such as:

```text
main.py
github_auth.py
diff_extractor.py
db.py
embeddings.py
doc_indexer.py
matcher.py
drafter.py
pr_commenter.py
retry.py
index_now.py
```

**Important implementation rule:** Do not blindly rewrite the existing project.

Before changing code, the coding agent MUST:

1. Inspect the current repository.
2. Run the existing tests.
3. Understand the current webhook flow.
4. Preserve working documentation-drift functionality unless a deliberate migration is required.
5. Refactor only when necessary to create clean reusable boundaries.

The final architecture should treat documentation drift as one review engine/plugin rather than as the entire application.

---

# 3. Product Definition

## 3.1 Product Name

Use:

**DriftWatch AI Code Reviewer**

Alternative internal package name:

`driftwatch-reviewer`

---

## 3.2 Problem

Traditional AI code review systems can produce plausible but incorrect comments.

Typical problems:

- hallucinated bugs,
- comments attached to irrelevant lines,
- duplicate findings,
- excessive low-value suggestions,
- security claims without evidence,
- lack of reproducible validation,
- no measurable false-positive evaluation.

This project addresses that by separating:

```text
Detection
    ↓
Evidence collection
    ↓
Validation
    ↓
Decision
    ↓
PR comment
```

---

# 4. Goals

## Primary goals

- GitHub-native PR review.
- Python-first support for MVP.
- Security issue detection.
- Bug detection.
- Code-quality detection.
- Existing documentation-drift detection retained as a review engine.
- Evidence-grounded findings.
- Independent static-analysis corroboration.
- Structured validation layer.
- Inline GitHub review comments.
- PR-level review summary.
- Quantitative evaluation.
- Observability through Langfuse.
- Clean architecture suitable for recruiter demonstration.

## Engineering goals

- Modular design.
- Testability.
- Deterministic behavior wherever possible.
- Clear separation of AI reasoning and validation.
- Provider-independent LLM interface.
- Configuration through environment variables/config files.
- Safe GitHub permissions.
- No secrets committed to the repository.

---

# 5. Non-Goals

Do NOT attempt these during the MVP:

- Supporting every programming language.
- Building a complete replacement for CodeQL/Semgrep.
- Fully autonomous code modification and merging.
- Automatically approving or merging pull requests.
- Building a large web dashboard.
- Training a custom LLM.
- Building a complex multi-agent framework.
- Supporting dozens of LLM providers.
- Perfect detection of every possible software vulnerability.
- Claiming a specific false-positive rate without evaluation evidence.

---

# 6. Target MVP

The MVP should support:

### Language

Primary:

- Python

Future:

- JavaScript/TypeScript
- Go
- C/C++

### Review categories

1. Security
2. Bugs
3. Code quality
4. Documentation drift

### Deterministic analysis

At minimum:

- `Semgrep`
- `Bandit` for Python
- AST analysis using `tree-sitter`

Optional later:

- `Gitleaks`
- `CodeQL`

### AI reasoning

Use an abstraction such as:

```python
class LLMProvider(Protocol):
    def analyze(self, request: ReviewRequest) -> list[CandidateFinding]:
        ...
```

The implementation may use Gemini, OpenAI-compatible APIs, Anthropic, or another supported provider.

Do not couple the core architecture directly to one model provider.

---

# 7. High-Level Architecture

```text
                         GitHub
                           │
                     Pull Request
                           │
                           ▼
                 ┌───────────────────┐
                 │ GitHub Webhook/API │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Review Orchestrator│
                 └─────────┬─────────┘
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
       Diff Analyzer   Static Tools   Context Builder
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                  ┌─────────────────┐
                  │ AI Review Engine │
                  └────────┬────────┘
                           │
                    Candidate Findings
                           │
                           ▼
                  ┌─────────────────┐
                  │ Validation Layer │
                  └────────┬────────┘
                           │
              ┌────────────┼─────────────┐
              │            │             │
              ▼            ▼             ▼
         AST Evidence  Static Check  Diff Evidence
              │            │             │
              └────────────┼─────────────┘
                           ▼
                  ┌─────────────────┐
                  │ Decision Engine  │
                  └────────┬────────┘
                           │
                 Validated Findings
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
        Inline PR Comments      PR Summary
                 │                   │
                 └─────────┬─────────┘
                           ▼
                    Metrics/Evaluation
                           │
                           ▼
                        Langfuse
```

---

# 8. Internal Module Structure

The exact directory structure can evolve after repository inspection, but the target logical structure is:

```text
src/
└── driftwatch/
    ├── app/
    │   ├── config.py
    │   ├── dependencies.py
    │   └── lifecycle.py
    │
    ├── github/
    │   ├── client.py
    │   ├── auth.py
    │   ├── webhooks.py
    │   ├── pull_requests.py
    │   └── comments.py
    │
    ├── review/
    │   ├── orchestrator.py
    │   ├── models.py
    │   ├── context.py
    │   ├── finding.py
    │   └── decision.py
    │
    ├── analyzers/
    │   ├── base.py
    │   ├── security.py
    │   ├── bugs.py
    │   ├── quality.py
    │   └── documentation.py
    │
    ├── static_analysis/
    │   ├── base.py
    │   ├── semgrep.py
    │   ├── bandit.py
    │   └── gitleaks.py
    │
    ├── ast/
    │   ├── parser.py
    │   ├── nodes.py
    │   └── evidence.py
    │
    ├── validation/
    │   ├── validator.py
    │   ├── evidence.py
    │   ├── rules.py
    │   ├── scoring.py
    │   └── deduplication.py
    │
    ├── llm/
    │   ├── base.py
    │   ├── provider.py
    │   ├── prompts.py
    │   └── structured_output.py
    │
    ├── reporting/
    │   ├── pr_summary.py
    │   ├── comment_formatter.py
    │   └── metrics.py
    │
    ├── observability/
    │   ├── langfuse.py
    │   └── tracing.py
    │
    ├── persistence/
    │   ├── models.py
    │   ├── repository.py
    │   └── migrations/
    │
    └── cli/
        └── evaluate.py

tests/
├── unit/
├── integration/
├── fixtures/
└── evaluation/

docs/
├── architecture.md
├── validation.md
├── evaluation.md
└── local-development.md
```

This is a target architecture, not a requirement to create every directory immediately.

Create modules incrementally as functionality is implemented.

---

# 9. Core Domain Models

All review findings must use a structured schema.

Example:

```python
class Finding:
    id: str
    category: Literal["security", "bug", "quality", "documentation"]
    severity: Literal["critical", "high", "medium", "low", "info"]

    title: str
    description: str

    repository: str
    pull_request: int

    file_path: str
    start_line: int
    end_line: int

    changed_code: str
    evidence: list[Evidence]

    llm_confidence: float | None
    validation_score: float | None

    static_matches: list[StaticMatch]
    validation_status: Literal[
        "accepted",
        "rejected",
        "needs_review"
    ]

    suggested_fix: str | None
```

Evidence should be structured:

```python
class Evidence:
    source: Literal[
        "diff",
        "ast",
        "semgrep",
        "bandit",
        "gitleaks",
        "llm"
    ]

    description: str
    file_path: str
    start_line: int | None
    end_line: int | None
    rule_id: str | None
```

A finding must never rely only on free-form text.

---

# 10. PR Review Lifecycle

## Step 1 — Receive webhook

Supported initial events:

- `pull_request.opened`
- `pull_request.synchronize`
- `pull_request.reopened`

Optionally support:

- `pull_request.ready_for_review`

Do not review draft PRs unless explicitly configured.

The webhook handler must:

1. Verify GitHub signature.
2. Validate event type/action.
3. Extract repository and PR identifiers.
4. Queue/start review processing.
5. Return quickly enough to avoid webhook timeout.

---

# 11. Review Orchestration

The orchestrator should coordinate the pipeline but should not contain domain-specific review logic.

Preferred flow:

```python
async def review_pull_request(event):
    pr = github.get_pull_request(...)
    diff = github.get_diff(pr)

    changed_files = diff_analyzer.analyze(diff)

    static_results = static_analyzer.run(changed_files)

    context = context_builder.build(
        pull_request=pr,
        diff=diff,
        static_results=static_results,
    )

    candidates = review_engine.analyze(context)

    validated = validation_engine.validate(
        candidates=candidates,
        context=context,
        static_results=static_results,
    )

    reporter.publish(validated)
```

---

# 12. Diff Analysis

The system must analyze the actual PR diff rather than the entire repository whenever possible.

For each changed file capture:

```text
path
language
status
added_lines
deleted_lines
hunks
changed_functions/classes
base_version
head_version
```

Use `tree-sitter` for syntax-aware extraction.

The system should preferentially comment on changed lines.

Do not generate inline comments against unrelated unchanged code unless explicitly supported and justified.

---

# 13. Context Builder

The LLM should receive focused context.

For each candidate area include:

- repository name
- PR title
- PR description
- file path
- changed lines
- surrounding code
- enclosing function/class
- relevant imports
- relevant static-analysis findings
- relevant configuration
- relevant documentation where applicable

Do not send the complete repository to the LLM by default.

Use a bounded context window.

---

# 14. Review Engines

Review engines must follow a common interface.

```python
class ReviewEngine(Protocol):
    name: str

    def analyze(
        self,
        context: ReviewContext
    ) -> list[CandidateFinding]:
        ...
```

## 14.1 Security Engine

Initial detection targets:

- hard-coded secrets/credentials
- unsafe command execution
- SQL injection patterns
- unsafe deserialization
- path traversal patterns
- weak cryptographic usage
- insecure subprocess usage
- dangerous dynamic evaluation

Use deterministic tooling where available.

The LLM should explain the issue, not invent security evidence.

---

## 14.2 Bug Engine

Initial bug categories:

- unreachable code
- obvious incorrect conditions
- incorrect exception handling
- null/None misuse
- resource handling problems
- incorrect API usage
- suspicious type/shape mismatches
- logic inconsistencies visible from local context

The bug engine should be conservative.

A speculative issue should not automatically become an inline comment.

---

## 14.3 Code Quality Engine

Initial categories:

- unnecessary complexity
- duplicated logic
- poor error handling
- dead code
- unclear variable/function naming
- maintainability problems
- overly large functions
- obvious performance anti-patterns

Low-value style preferences should normally be omitted.

---

## 14.4 Documentation Drift Engine

Preserve and refactor the existing DriftWatch documentation-drift capability into this engine.

Existing behavior should remain available:

```text
changed code
    ↓
documentation matching
    ↓
LLM verification
    ↓
suggested documentation update
    ↓
PR comment
```

---

# 15. Static Analysis Layer

Static analysis is separate from the LLM.

### Required initial tools

#### Semgrep

Use for rule-based multi-language security/bug patterns.

The adapter should:

- execute Semgrep,
- capture JSON output,
- normalize results,
- map findings to repository file/line locations.

#### Bandit

Use for Python security-specific checks.

The adapter should:

- execute Bandit,
- capture structured output,
- normalize findings.

### Optional future tools

- Gitleaks
- CodeQL
- Ruff
- mypy
- ESLint
- Pylint

Do not add tools solely for resume keyword count. Every tool must provide a useful independent signal.

---

# 16. Validation Layer

This is the most important component of the project.

## Principle

The LLM produces **candidate findings**.

The validation layer decides whether a finding is trustworthy enough to become a PR comment.

Never treat:

```text
LLM confidence = truth
```

Instead require independent evidence.

---

## 16.1 Validation stages

### Stage A — Location validation

Check:

- file exists,
- line exists,
- line belongs to the PR diff where inline commenting is intended,
- reported location corresponds to the supplied code context.

Reject if location is invalid.

---

### Stage B — Diff relevance

Determine whether the finding is actually related to the changed code.

Possible checks:

- finding line intersects changed lines,
- finding AST node intersects changed node,
- finding's referenced symbol was changed,
- finding is downstream of the changed code.

Reject or downgrade unrelated findings.

---

### Stage C — AST evidence

Use `tree-sitter` to determine:

- enclosing function/class,
- node type,
- source span,
- relevant syntax relationships.

Examples:

If the LLM says:

> "This code invokes a shell command using untrusted input."

The validator should verify that:

1. the relevant call exists,
2. the reported location contains the call,
3. user-controlled data flows into the relevant argument if deterministic analysis can establish it.

The system must not claim data-flow proof when it only has syntactic evidence.

---

### Stage D — Static-analysis corroboration

Compare the candidate finding with:

- Semgrep,
- Bandit,
- Gitleaks,
- future CodeQL results.

Corroboration examples:

```text
LLM: possible hard-coded password
Gitleaks/Bandit/Semgrep: same file + same location
→ strong evidence
```

or:

```text
LLM: SQL injection
Semgrep: matching SQL injection rule at same region
→ strong evidence
```

No matching tool finding does NOT automatically mean that the LLM finding is false.

It means confidence should be lower unless other evidence exists.

---

### Stage E — Claim/evidence consistency

The validator must ensure that the comment's claims are supported by the collected evidence.

Reject claims such as:

> "This will always cause a remote code execution vulnerability."

when the system has only established:

> "User-controlled input reaches a shell execution call."

The generated wording must not overstate certainty.

---

### Stage F — Deduplication

Multiple analyzers may identify the same problem.

Deduplicate based on:

- file,
- overlapping lines,
- category,
- normalized issue fingerprint,
- semantic similarity when necessary.

One underlying issue should normally produce one PR comment.

---

# 17. Validation Decision

The validation engine produces:

```python
ValidationResult(
    status="accepted" | "rejected" | "needs_review",
    score=0.0-1.0,
    reasons=[...],
    evidence=[...],
)
```

Use configurable scoring.

A possible initial weighting:

```text
35% direct code/diff evidence
30% static-analysis corroboration
20% location/AST consistency
15% LLM confidence
```

These weights are initial engineering defaults, not scientifically proven constants.

They must be configurable and later tuned using the evaluation dataset.

Do not allow LLM confidence alone to exceed the acceptance threshold.

---

# 18. Validation Policies

Recommended initial policy:

### Security

Post automatically when:

- location is valid,
- issue is relevant to changed code,
- deterministic evidence exists OR multiple strong evidence signals agree,
- wording does not overstate certainty.

### Bugs

Require:

- strong code evidence,
- valid location,
- sufficiently specific explanation.

### Code quality

Be conservative.

Only post comments that are:

- actionable,
- clearly tied to changed code,
- materially useful.

### Documentation

Use the existing DriftWatch matching + verification workflow, then pass the result through the common validation/reporting pipeline.

---

# 19. Acceptance Threshold

Make thresholds configurable:

```env
VALIDATION_ACCEPT_THRESHOLD=0.75
VALIDATION_REVIEW_THRESHOLD=0.50
```

Interpretation:

```text
score >= accept threshold
    → publish

review threshold <= score < accept threshold
    → store but do not publish automatically

score < review threshold
    → reject
```

Thresholds must be tuned using evaluation data.

---

# 20. False-Positive Target

Project target:

> Achieve a single-digit false-positive rate on the defined evaluation set.

A practical target is:

```text
False Positive Rate < 10%
```

For project reporting, use a precisely defined metric.

Recommended definition:

```text
False Positive Rate =
invalid/non-actionable posted findings
---------------------------------------
all posted findings
```

Also report:

```text
Precision
Recall
F1
Validation acceptance rate
Rejected finding rate
Static-tool agreement rate
Average findings per PR
Median review latency
LLM/token cost per PR
```

Do NOT claim "<10% false positives" unless evaluation evidence supports it.

---

# 21. Evaluation Dataset

Create a reproducible benchmark.

Recommended structure:

```text
evaluation/
├── repositories/
├── prs/
├── fixtures/
├── expected_findings.jsonl
├── annotations.jsonl
└── run_evaluation.py
```

Each test example should contain:

```json
{
  "repository": "example/repo",
  "pull_request": 123,
  "file": "app.py",
  "line": 42,
  "category": "security",
  "expected": true,
  "expected_issue": "unsafe shell execution"
}
```

Also include negative examples where code is valid and should not produce a comment.

The evaluation set should intentionally contain:

- true positives,
- false-positive traps,
- irrelevant code changes,
- benign patterns that resemble vulnerabilities,
- duplicate detector findings,
- documentation-only changes,
- formatting-only changes.

---

# 22. PR Output

## 22.1 Inline Comment Format

Use a concise format:

```markdown
### 🔐 Security: Shell execution with external input

**Issue**

User-controlled input reaches `subprocess.run(..., shell=True)`,
which can allow command injection.

**Evidence**

- `app/commands.py:42`
- Semgrep rule: `python.lang.security.audit.subprocess-shell-true`
- AST confirms the changed call site.

**Suggested fix**

Avoid `shell=True` and pass arguments as a list after validating
the allowed command/input.

**Validation**

Evidence: strong  
Static analysis: corroborated  
Validation score: 0.91
```

Do not expose internal chain-of-thought.

Only expose concise evidence and conclusions.

---

# 23. PR Summary

Every completed review should produce a summary similar to:

```markdown
## 🤖 DriftWatch AI Code Review

### Summary

- Files analyzed: 8
- Candidate findings: 17
- Validated findings: 4
- Rejected findings: 10
- Needs review: 3

### Findings

| Category | Count |
|---|---:|
| Security | 2 |
| Bugs | 1 |
| Code Quality | 1 |
| Documentation | 0 |

### Validation

- Evidence-backed findings: 4/4
- Static-analysis corroboration: 3/4
- Duplicate findings removed: 2

> Findings are suggestions generated by automated analysis.
> Reviewers should verify them before making changes.
```

---

# 24. Metrics Report

Provide a machine-readable report and a human-readable Markdown report.

Example:

```text
evaluation/results/
├── latest.json
├── latest.md
└── runs/
    └── <timestamp>.json
```

Include:

```text
total_candidates
accepted_findings
rejected_findings
needs_review
precision
recall
f1
false_positive_rate
average_validation_score
static_analysis_agreement
average_pr_latency
average_llm_cost
```

The metrics report is a primary recruiter-facing artifact.

---

# 25. Observability

Use **Langfuse** for LLM observability.

Track:

- review run ID,
- repository,
- PR number,
- model,
- prompt version,
- latency,
- token usage where available,
- candidate count,
- accepted/rejected count,
- validation score,
- tool usage,
- errors.

Do NOT send secrets or unnecessary repository data to observability systems.

Use redaction where appropriate.

---

# 26. LangChain Policy

LangChain is allowed but not mandatory.

Use LangChain only if it provides a real benefit such as:

- structured LLM pipelines,
- prompt templates,
- provider abstraction,
- output parsing,
- tracing integration.

Do not introduce LangChain merely because the project is an AI application.

The domain logic must remain framework-independent.

Preferred layering:

```text
Review Engine
    ↓
LLM interface
    ↓
LangChain adapter (optional)
    ↓
LLM provider
```

The validation layer must never depend on LangChain.

---

# 27. Optional AI/Developer Tooling

Potential tools:

| Tool | Purpose |
|---|---|
| Langfuse | LLM observability |
| LangChain | LLM orchestration where useful |
| Pydantic | Typed domain models |
| tree-sitter | AST parsing |
| Semgrep | Static analysis |
| Bandit | Python security analysis |
| Gitleaks | Secret detection |
| CodeQL | Advanced code security |
| PostgreSQL | Persistent storage |
| pgvector | Existing vector/document capabilities |
| Docker | Reproducible local environment |
| GitHub Actions | CI |
| FastAPI | Webhook/API service |

Do not integrate all of these in the first milestone.

---

# 28. Database Model

Retain the existing PostgreSQL/pgvector setup where useful.

Add relational entities approximately equivalent to:

```text
repositories
review_runs
changed_files
findings
evidence
static_results
validation_results
comments
evaluation_runs
```

Important relationships:

```text
repository
   └── review_run
          ├── changed_files
          └── findings
                 ├── evidence
                 ├── validation_result
                 └── comment
```

Use migrations rather than destructive schema recreation.

---

# 29. Configuration

Use environment variables.

Example:

```env
APP_ENV=development

GITHUB_APP_ID=
GITHUB_WEBHOOK_SECRET=
GITHUB_PRIVATE_KEY=
GITHUB_INSTALLATION_ID=

DATABASE_URL=

LLM_PROVIDER=
LLM_API_KEY=
LLM_MODEL=

LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=

VALIDATION_ACCEPT_THRESHOLD=0.75
VALIDATION_REVIEW_THRESHOLD=0.50

MAX_COMMENTS_PER_PR=10
MAX_CONTEXT_TOKENS=
```

No credentials may be hard-coded.

---

# 30. Security Requirements

The system itself handles source code, credentials, and GitHub permissions.

Therefore:

- Verify webhook signatures.
- Use least-privilege GitHub App permissions.
- Never log private keys.
- Never commit `.env`.
- Sanitize logs.
- Avoid persisting unnecessary source code.
- Protect database credentials.
- Add timeout controls around subprocess tools.
- Restrict shell execution arguments.
- Validate external API responses.
- Handle malicious PR content as untrusted input.

Treat repository code and PR descriptions as potentially adversarial input.

---

# 31. Reliability Requirements

The service must handle:

- duplicate webhook deliveries,
- GitHub API retries,
- transient LLM failures,
- static tool failures,
- malformed LLM output,
- timeouts,
- large PRs,
- unsupported languages,
- missing files,
- renamed/deleted files.

Use idempotency keys such as:

```text
repository_id + pull_request_number + head_sha
```

A repeated webhook for the same head SHA should not create duplicate comments.

---

# 32. LLM Output Requirements

The LLM must produce structured output.

Preferred schema:

```json
{
  "findings": [
    {
      "category": "security",
      "severity": "high",
      "file_path": "app.py",
      "start_line": 42,
      "end_line": 42,
      "title": "Unsafe shell execution",
      "description": "External input reaches shell execution.",
      "reasoning_summary": "Concise evidence-based explanation.",
      "suggested_fix": "Avoid shell=True and pass arguments explicitly.",
      "confidence": 0.88
    }
  ]
}
```

Never parse arbitrary prose when structured output is available.

The field `reasoning_summary` must contain a short explanation, not private chain-of-thought.

---

# 33. Prompt Requirements

Prompts must instruct the model to:

- review only supplied repository context,
- distinguish certainty from speculation,
- identify exact evidence,
- avoid comments unrelated to changed code,
- avoid style nitpicks,
- produce structured output,
- avoid duplicate findings,
- never invent files/functions/lines,
- never claim a vulnerability without evidence,
- use conservative severity.

Prompts should be versioned.

Example:

```text
prompts/
├── security/v1.txt
├── bugs/v1.txt
├── quality/v1.txt
└── documentation/v1.txt
```

---

# 34. Testing Strategy

## Unit tests

Test:

- diff parsing,
- AST extraction,
- static-tool adapters,
- finding normalization,
- evidence matching,
- validation scoring,
- deduplication,
- GitHub comment formatting,
- configuration.

## Integration tests

Test:

```text
GitHub event
    → diff
    → analyzers
    → validator
    → reporter
```

Use mocked GitHub and LLM services where practical.

## End-to-end tests

Use a dedicated test repository to validate:

- webhook reception,
- PR analysis,
- inline comment creation,
- summary creation,
- idempotency.

---

# 35. Golden Evaluation Tests

Create known cases such as:

### Case A — SQL injection

Input:

```python
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(query)
```

Expected:

- security finding,
- valid location,
- high evidence score.

### Case B — Safe parameterized SQL

Input:

```python
cursor.execute(
    "SELECT * FROM users WHERE id = ?",
    (user_id,)
)
```

Expected:

- no SQL injection comment.

### Case C — shell command

Unsafe:

```python
subprocess.run(user_input, shell=True)
```

Expected:

- security finding.

Safe:

```python
subprocess.run(["tool", "--name", user_input], check=True)
```

Expected:

- no shell-injection finding solely because `subprocess.run` exists.

### Case D — harmless refactor

Expected:

- no low-value AI comments.

These examples are starting fixtures, not the entire benchmark.

---

# 36. Development Phases

## Phase 0 — Repository Assessment and Refactor

### Goal

Understand and prepare the existing DriftWatch repository.

Tasks:

- inspect current codebase,
- run existing tests,
- document current architecture,
- identify reusable components,
- separate generic GitHub functionality from documentation drift,
- introduce clean package boundaries,
- add/update typing and tests.

### Exit criteria

- Existing documentation-drift flow still works.
- Existing tests pass.
- New architecture is documented.
- No unnecessary rewrite.

---

## Phase 1 — GitHub PR Review MVP

### Goal

Generate basic AI findings on pull requests.

Implement:

- PR webhooks,
- changed-file extraction,
- Python diff/context processing,
- LLM provider interface,
- structured candidate findings,
- inline PR comments,
- PR summary.

Initial category:

- security

Then add:

- bugs
- code quality

### Exit criteria

A test PR produces at least one accurate inline finding from a known seeded vulnerability.

---

## Phase 2 — Validation Layer

### Goal

Make findings evidence-grounded.

Implement:

- AST validation,
- location validation,
- diff relevance,
- Semgrep adapter,
- Bandit adapter,
- evidence collection,
- validation scoring,
- acceptance/rejection logic,
- deduplication.

### Exit criteria

The same evaluation set can be executed with:

```text
validation disabled
validation enabled
```

and the system reports the difference.

---

## Phase 3 — Evaluation and Metrics

### Goal

Quantitatively measure the reviewer.

Implement:

- evaluation fixtures,
- labeled dataset,
- precision/recall/F1,
- false-positive rate,
- validation acceptance rate,
- latency metrics,
- cost metrics,
- automated evaluation runner.

### Exit criteria

A reproducible command such as:

```bash
python -m driftwatch.cli.evaluate
```

produces:

```text
evaluation/results/latest.md
evaluation/results/latest.json
```

---

## Phase 4 — Documentation Drift Integration

### Goal

Promote the current DriftWatch feature into a first-class review engine.

Implement:

- common `ReviewEngine` interface,
- documentation engine adapter,
- shared finding model,
- shared validation,
- shared reporting.

### Exit criteria

Security, bug, quality, and documentation findings share the same reporting/validation pipeline.

---

## Phase 5 — Observability, CI/CD, and Recruiter Demo

### Goal

Make the project polished and demonstrable.

Implement:

- Langfuse tracing,
- Dockerized local setup,
- GitHub Actions,
- static checks,
- test coverage reporting,
- architecture documentation,
- demo repository,
- seeded vulnerable PR examples,
- metrics report.

### Exit criteria

A recruiter can open the repository and quickly understand:

1. what the system does,
2. why validation is needed,
3. how the architecture works,
4. what tools are used,
5. what the evaluation results are,
6. how to reproduce the demo.

---

# 37. CI Requirements

GitHub Actions should run:

```text
format/lint
type checking
unit tests
integration tests
security checks
evaluation smoke tests
```

Suggested tooling:

- Ruff
- pytest
- mypy or pyright
- Semgrep
- Bandit

Use whatever tools are actually adopted by the project; do not duplicate checks unnecessarily.

---

# 38. Local Development

Target:

```bash
docker compose up
```

for the core dependencies where practical.

Expected local components:

```text
FastAPI service
PostgreSQL/pgvector
optional Langfuse
static analysis executables
```

Provide a simple setup:

```bash
cp .env.example .env
docker compose up
pytest
```

---

# 39. Deployment

The project should remain deployable on a low-cost/free-tier-friendly platform for demonstration.

Requirements:

- containerized service,
- environment-variable configuration,
- PostgreSQL-compatible database,
- HTTPS webhook endpoint,
- persistent database,
- GitHub App integration.

Do not make expensive cloud infrastructure a requirement.

---

# 40. Recruiter Demo Scenario

Create a dedicated demo repository or branch containing intentionally vulnerable changes.

Example PR:

```text
PR #42 — Add user search endpoint
```

Seed:

1. SQL injection.
2. unsafe shell execution.
3. hard-coded credential.
4. harmless refactor.
5. documentation drift example.

The ideal demo shows:

```text
5 candidate issues
      ↓
validation
      ↓
3 actionable findings
      ↓
2 rejected false positives
```

The exact counts must come from actual evaluation.

Do not fabricate performance numbers.

---

# 41. Recruiter-Facing README

The final README should contain:

## What it is

One paragraph.

## Why it is different

Focus on:

- evidence-based validation,
- independent static analysis,
- AST-aware checks,
- measurable evaluation.

## Architecture

Include one architecture diagram.

## Example PR

Show actual inline comments.

## Validation

Show the validation process.

## Metrics

Show real measured results.

## Tech stack

Keep it concise.

## Run locally

Provide exact commands.

## Limitations

Explicitly state:

- supported languages,
- known blind spots,
- model limitations,
- evaluation dataset limitations.

---

# 42. Engineering Rules for Coding Agents

These rules are mandatory.

## Rule 1 — Inspect before modifying

Before implementing a feature:

```text
inspect repository
→ identify existing implementation
→ identify tests
→ identify integration points
→ make smallest coherent change
```

Do not assume the repository structure described in this document exactly matches the current branch.

---

## Rule 2 — Preserve working functionality

Do not remove current documentation-drift functionality unless the replacement is demonstrably equivalent or better tested.

---

## Rule 3 — No giant files

Avoid adding all logic to `main.py`.

Keep:

- webhook handling,
- orchestration,
- analysis,
- validation,
- persistence,
- reporting

separate.

---

## Rule 4 — Domain logic must be testable

The validation engine must be usable without GitHub.

Example:

```python
result = validator.validate(
    finding,
    evidence
)
```

This should be unit-testable without network access.

---

## Rule 5 — Deterministic logic stays deterministic

Do not use an LLM for:

- line validation,
- JSON parsing,
- duplicate elimination,
- threshold comparisons,
- basic AST checks,
- evidence existence.

---

## Rule 6 — Do not hide uncertainty

Use:

```text
unknown
needs_review
insufficient_evidence
```

when appropriate.

Do not convert uncertainty into a confident security claim.

---

## Rule 7 — No private chain-of-thought storage

Store concise evidence and conclusions, not hidden reasoning traces.

---

## Rule 8 — No hard-coded credentials

All secrets come from configuration/environment or secure secret management.

---

## Rule 9 — Avoid unnecessary dependencies

Every dependency must have a documented purpose.

---

## Rule 10 — Every feature needs tests

A feature is not complete when the code works once.

It is complete when:

- implementation exists,
- tests exist,
- failure behavior is handled,
- documentation is updated.

---

# 43. Definition of Done

A task is complete only when:

```text
[ ] Implementation complete
[ ] Unit tests added
[ ] Integration behavior verified where applicable
[ ] Error cases handled
[ ] Logging added where useful
[ ] No secrets committed
[ ] Existing functionality preserved
[ ] Documentation updated
[ ] Acceptance criteria satisfied
```

---

# 44. Recommended First Agent Task

When a coding agent first receives this specification, it should NOT immediately implement all phases.

It should execute this sequence:

### Step 1

Inspect repository.

### Step 2

Run existing tests.

### Step 3

Summarize current architecture.

### Step 4

Identify differences between current architecture and this specification.

### Step 5

Propose the minimum Phase 0 refactor.

### Step 6

Implement only Phase 0.

### Step 7

Run tests again.

### Step 8

Provide a concise implementation report.

Only then proceed to Phase 1.

---

# 45. Recommended Development Order

Implement in this order:

```text
Repository assessment
        ↓
Architecture refactor
        ↓
Finding schema
        ↓
PR review orchestrator
        ↓
Python diff/context analyzer
        ↓
LLM provider abstraction
        ↓
Security engine
        ↓
Semgrep adapter
        ↓
Bandit adapter
        ↓
Validation engine
        ↓
Inline comments
        ↓
PR summary
        ↓
Bug engine
        ↓
Quality engine
        ↓
Documentation engine integration
        ↓
Evaluation framework
        ↓
Langfuse
        ↓
Deployment + CI
        ↓
Recruiter demo
```

Do not implement all review categories simultaneously.

---

# 46. Success Criteria

The project is considered successful when all of the following are true:

### Functional

- GitHub PR triggers the service.
- Changed Python code is analyzed.
- Security findings can be generated.
- Bug findings can be generated.
- Code-quality findings can be generated.
- Documentation drift remains supported.
- Findings are validated.
- Validated findings appear as inline PR comments.
- PR summary is generated.

### Validation

- Every posted finding has structured evidence.
- Invalid locations are rejected.
- Findings unrelated to the diff are rejected or downgraded.
- Duplicate findings are removed.
- Static analysis can corroborate AI findings.
- Validation can suppress weak AI-only findings.

### Evaluation

- Reproducible benchmark exists.
- Precision is reported.
- Recall is reported.
- F1 is reported.
- False-positive rate is reported.
- The project measures whether the single-digit false-positive target is achieved rather than assuming it.

### Engineering

- Tests run in CI.
- Service is deployable.
- Secrets are externalized.
- Architecture is documented.
- Existing DriftWatch behavior remains functional.

---

# 47. Final Product Concept

The final system should communicate this simple idea:

```text
AI finds possible problems.
        ↓
Static analysis provides independent signals.
        ↓
AST/diff analysis verifies the location and context.
        ↓
Validation decides whether the evidence is strong enough.
        ↓
Only validated findings reach the developer.
```

The key project claim should therefore be:

> **An evidence-grounded AI GitHub code reviewer that combines LLM reasoning with deterministic code analysis and a dedicated validation layer to reduce false-positive review comments.**

This statement describes the intended architecture and engineering goal. It is not a claim of achieved performance until the evaluation phase produces supporting results.

---



# 50. Web Dashboard / Observability UI

The project should include a dedicated web dashboard.

The dashboard is **not** the primary review interface; GitHub remains the primary developer-facing interface for inline review comments. The dashboard provides cross-repository history, analytics, observability, and evaluation results.

## 50.1 UI Goals

The dashboard must allow a user to:

- connect/view multiple repositories,
- see historical review runs,
- inspect individual pull requests,
- inspect findings and their validation evidence,
- monitor validation performance,
- inspect LLM/analysis latency and cost,
- compare repositories,
- inspect trends over time,
- view evaluation metrics,
- identify false-positive patterns,
- inspect failed review runs.

The UI should be read-heavy and operationally simple. Do not build a complex SaaS-style admin panel in the first version.

---

## 50.2 Recommended Frontend Stack

Recommended:

```text
Next.js
React
TypeScript
Tailwind CSS
Recharts
```

Backend:

```text
FastAPI
PostgreSQL
```

Do not introduce a second backend framework.

The existing FastAPI service should expose the dashboard API.

Alternative for a rapid prototype:

```text
Streamlit
```

However, the preferred recruiter-facing implementation is Next.js/React because it demonstrates a more conventional production web-application architecture.

---

## 50.3 Dashboard Architecture

```text
                         Browser
                            │
                            ▼
                  ┌───────────────────┐
                  │ Next.js Dashboard  │
                  │ React + TypeScript │
                  └─────────┬─────────┘
                            │ REST/JSON
                            ▼
                  ┌───────────────────┐
                  │ FastAPI API Layer  │
                  └─────────┬─────────┘
                            │
             ┌──────────────┼───────────────┐
             ▼              ▼               ▼
        PostgreSQL      GitHub API       Langfuse
             │
             ▼
       Review History
       Findings
       Evidence
       Metrics
       Evaluation
```

The browser must not directly access PostgreSQL.

---

# 51. Dashboard Pages

## 51.1 Overview Dashboard

Route:

```text
/
```

Show:

```text
Total repositories
Total review runs
Total PRs reviewed
Total findings
Validated findings
Rejected findings
Needs-review findings
```

Key KPI cards:

```text
Precision
False-positive rate
Validation acceptance rate
Average review latency
Average LLM cost
```

Charts:

- reviews over time,
- findings by category,
- findings by severity,
- accepted vs rejected findings,
- validation score distribution.

---

## 51.2 Repository List

Route:

```text
/repositories
```

Show all tracked repositories.

Columns:

```text
Repository
Default branch
Reviews
Open PRs reviewed
Last review
Findings
Validation rate
Status
```

Filters:

```text
organization/user
language
active/inactive
date range
```

Selecting a repository opens its detail page.

---

## 51.3 Repository Detail

Route:

```text
/repositories/:repository_id
```

Show:

### Repository summary

```text
Repository name
Default branch
Primary languages
Total PRs reviewed
Total findings
Last review
```

### Historical metrics

Charts for:

- findings per PR,
- security findings,
- bug findings,
- quality findings,
- documentation findings,
- validation acceptance,
- false positives,
- review latency.

### Recent review runs

Example:

```text
PR #142
PR #141
PR #139
PR #138
```

Each row should link to the review detail page.

---

# 52. Pull Request Review Page

Route:

```text
/repositories/:repository_id/reviews/:review_id
```

This is one of the most important pages.

Show:

```text
PR title
PR number
author
branch
commit SHA
review timestamp
review duration
```

### Review statistics

```text
Files analyzed
Candidate findings
Accepted
Rejected
Needs review
Comments posted
```

### Findings table

Columns:

```text
Severity
Category
File
Line
Validation score
Status
Static corroboration
```

Example:

```text
HIGH | Security | app.py:42 | 0.91 | Accepted | Semgrep ✓
MEDIUM | Bug | parser.py:18 | 0.77 | Accepted | AST ✓
LOW | Quality | utils.py:81 | 0.42 | Rejected | None
```

Clicking a finding opens its detailed evidence.

---

# 53. Finding Detail Page / Panel

Show:

```text
Finding
Category
Severity
File
Line
Description
Suggested fix
```

Then show evidence separately:

```text
Evidence
────────────────────────────────

Diff evidence          ✓
AST evidence           ✓
Semgrep                ✓
Bandit                 -
LLM candidate          ✓
```

Show validation breakdown:

```text
Code/diff evidence          0.95
Static analysis             1.00
AST/location consistency    1.00
LLM confidence              0.88

Final validation score     0.91
```

Do not expose hidden chain-of-thought.

Show only concise evidence and machine-generated explanations.

---

# 54. Review History

Route:

```text
/reviews
```

Allow filtering by:

```text
repository
date
category
severity
validation status
review result
```

Support sorting by:

```text
newest
oldest
latency
number of findings
validation score
```

Provide pagination.

---

# 55. Observability Page

Route:

```text
/observability
```

Show operational metrics such as:

```text
Webhook processing latency
GitHub API latency
LLM latency
Static-analysis latency
Validation latency
Total review duration
LLM token usage
LLM cost
Error rate
Retry rate
```

Include time-series charts.

Break down latency:

```text
GitHub       320 ms
Diff         110 ms
Semgrep      850 ms
Bandit       190 ms
LLM         4200 ms
Validation   220 ms
Reporting    300 ms
────────────────────
Total       ~6.2 s
```

Values above are illustrative only.

---

# 56. Evaluation Page

Route:

```text
/evaluation
```

Show actual benchmark results.

Metrics:

```text
Precision
Recall
F1
False-positive rate
False-negative rate
Validation acceptance rate
Static-analysis agreement
```

Allow selecting:

```text
evaluation run
model
prompt version
threshold
repository
category
```

### Before vs after validation

This should be a key visualization:

```text
                 Without Validation    With Validation

Precision              68%                    94%
False Positives        32%                     6%
Accepted Findings      ...                     ...
```

The dashboard must calculate these numbers from stored evaluation results.

Never hard-code illustrative values into production UI.

---

# 57. Model / Prompt Analytics

Route:

```text
/analytics
```

Show aggregated LLM performance:

```text
Model
Prompt version
Reviews
Average latency
Average token usage
Average confidence
Accepted findings
Rejected findings
```

This supports experimentation without modifying the core review pipeline.

---

# 58. Review Run State Model

A review run should have explicit states:

```text
queued
running
completed
completed_with_warnings
failed
cancelled
```

The UI should represent these states clearly.

For example:

```text
● Running
✓ Completed
⚠ Completed with warnings
✕ Failed
```

---

# 59. Dashboard API

FastAPI should expose versioned read APIs.

Example:

```text
GET /api/v1/dashboard/overview
GET /api/v1/repositories
GET /api/v1/repositories/{id}
GET /api/v1/repositories/{id}/reviews
GET /api/v1/reviews/{id}
GET /api/v1/findings/{id}
GET /api/v1/metrics
GET /api/v1/observability
GET /api/v1/evaluation/runs
GET /api/v1/evaluation/runs/{id}
```

Use Pydantic response models.

Do not expose internal database models directly.

---

# 60. UI Data Requirements

The backend must persist enough information to reconstruct historical views.

At minimum retain:

```text
repository
pull_request
head_sha
review_run
start_time
end_time
status
changed_files
candidate_findings
validated_findings
rejected_findings
evidence
validation_results
static_analysis_results
comments
model
prompt_version
token/cost data where available
errors
```

---

# 61. Multi-Repository Support

The dashboard must treat repositories as first-class entities.

The same installation can review:

```text
repo-A
repo-B
repo-C
```

Review history must remain separated by repository.

The overview dashboard can aggregate across repositories.

Repository-specific pages must show only that repository's data.

Use stable GitHub repository identifiers rather than relying only on repository names.

---

# 62. UI Authentication

For the initial recruiter demo, keep authentication simple.

Acceptable initial options:

1. Single-user/private deployment using an application-level login.
2. GitHub OAuth.
3. Deployment behind an authentication proxy.

Do not build a complete enterprise identity-management system in the MVP.

The review service and dashboard must still enforce authorization for repository data.

---

# 63. UI/UX Principles

Keep the UI:

- clean,
- data-oriented,
- responsive,
- fast,
- easy to understand during a 2–5 minute recruiter demo.

Prioritize:

```text
Overview
→ Repository
→ PR review
→ Finding evidence
→ Metrics
```

Avoid:

- unnecessary animations,
- excessive configuration screens,
- large forms,
- decorative dashboards with little information.

The dashboard exists to make the engineering system observable, not to become the main product itself.

---

# 64. Updated Development Phases

The project now has six phases.

## Phase 0 — Repository Assessment and Refactor

Existing DriftWatch cleanup and modularization.

## Phase 1 — GitHub PR Review MVP

Basic security, bug, and quality review.

## Phase 2 — Validation Layer

AST + Semgrep + Bandit + evidence-based decisioning.

## Phase 3 — Evaluation and Metrics

Benchmark dataset and measurable performance.

## Phase 4 — Documentation Drift Integration

Move the existing DriftWatch functionality into the common review-engine architecture.

## Phase 5 — Observability, CI/CD, and Recruiter Demo

Langfuse, deployment, automated CI, seeded demo PRs, documentation.

## Phase 6 — Web Dashboard

Build:

- overview dashboard,
- multi-repository history,
- repository pages,
- PR review pages,
- finding evidence views,
- observability page,
- evaluation page,
- analytics.

### Phase 6 exit criteria

A user can:

1. Open the dashboard.
2. See all tracked repositories.
3. Open a repository.
4. See historical PR reviews.
5. Open a review.
6. Inspect every finding.
7. See evidence and validation decisions.
8. View review latency/cost.
9. View evaluation metrics.
10. Compare validation performance over time.

---

# 65. Final User Experience

The completed product should provide two complementary interfaces.

## Interface A — GitHub

Used by developers.

```text
Pull Request
    ↓
AI Review
    ↓
Inline comments
    ↓
PR summary
```

## Interface B — DriftWatch Dashboard

Used for engineering visibility, debugging, evaluation, and demonstrations.

```text
Dashboard
    ↓
Repositories
    ↓
Review history
    ↓
PR details
    ↓
Finding evidence
    ↓
Validation metrics
    ↓
Observability
    ↓
Evaluation
```

Together they demonstrate both:

- **developer-facing functionality**, and
- **production-oriented engineering/observability**.

# 48. Agent Handoff Prompt

The following prompt can be given directly to an AI coding agent after this specification:

```text
You are implementing the DriftWatch AI Code Reviewer described in this specification.

First inspect the existing repository thoroughly.

Do NOT immediately implement the entire system.

Your first task is Phase 0:
1. Understand the current DriftWatch architecture.
2. Run the existing tests.
3. Identify reusable components.
4. Identify architectural conflicts with the specification.
5. Propose a minimal refactor plan.
6. Implement the minimal refactor.
7. Preserve all currently working documentation-drift behavior.
8. Add tests for refactored behavior.
9. Run the full test suite.
10. Report exactly what changed, what remains, and any risks.

Do not fabricate evaluation metrics.

Do not claim the false-positive target has been achieved until an evaluation dataset has produced the measurement.

After Phase 0 is complete, stop and wait for the next implementation instruction.
```

---

# 49. Reference Repository

Current baseline repository:

`https://github.com/ashwinruke/driftwatch`

The existing project already provides the GitHub webhook, AST-based diff extraction, pgvector-backed document matching, LLM verification, and PR commenting foundations that this project should build upon.

