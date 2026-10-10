---
name: development-workflow
description: "按需求、架构、任务卡、测试和人工审核闭环执行软件开发任务，适用于新功能、重构、Bug 修复和项目初始化。"
---

# Development Workflow

Use this skill for coding work that should follow the user's software-development pipeline. Preserve the user's approval boundaries: do not commit, push, merge, deploy, or make unrelated edits unless explicitly requested.

## Operating principles

- Before acting, read the applicable project rules, directory structure, task card, relevant module documentation, existing implementation, tests, and recent changes.
- Keep dependencies flowing from foundation to business logic to presentation/tooling; do not introduce cross-layer calls.
- Use English identifiers and Chinese comments/docstrings when adding Python code. Add type hints and Google-style docstrings to public Python functions.
- Follow TDD: write or update concrete tests before implementation when the task changes behavior.
- Report only what was verified. Include raw test output or clearly mark items as 未验证.
- Keep the change set surgical. Do not rename, clean up, upgrade dependencies, or redesign unrelated code.

## Workflow

### 0. Clarify scope

For a new project or ambiguous feature, resolve: core feature boundary, multi-agent needs, retrieval/knowledge-base strategy, automation level, and deployment/cost constraints. Record explicit non-goals and acceptance criteria before architecture work.

### 1. Plan architecture

For non-trivial work, produce or update an architecture plan before coding. Cover project positioning, feature inputs/processing/outputs, agent responsibilities, retrieval strategy, technology alternatives and rejection reasons, layered architecture, upgrade path, automation, modules and dependencies, data model, API contract, deployment/cost, and optional paper structure.

Use the available tools deliberately:

- Use Context7 for version-sensitive framework or library APIs.
- Use GitHub for repository, issue, PR, CI, and code-history context.
- Use `visualize` or Mermaid for architecture, data-flow, dependency, sequence, and state diagrams.
- Use Figma for design-system or design-to-code context.

Pause for user architecture approval before implementation when the project follows an approval-gated workflow.

### 2. Split modules and task cards

After architecture approval, create short module documents. Each module document states responsibility, non-responsibility, upstream/downstream interfaces, data contracts, failure diagnosis, and test scenarios.

Each task card must state:

- objective and concrete file/function scope;
- Given/When/Then acceptance examples, including normal, boundary, and exception paths;
- specific tests to write first;
- prohibited behavior;
- input documents and output format;
- dependencies and priority;
- a closure checklist: scope boundary, failing-test-first, minimal implementation, no unrelated files, conclusion written back, and no sensitive data.

### 3. Implement and verify

The worker reads rules → module docs → task card → relevant code, then writes failing tests, implements the smallest change, and verifies it.

Apply test strength by layer:

- foundation/database/core engine: unit coverage target ≥90%, integration, boundary, and exception tests;
- business/API logic: unit coverage target ≥80%, integration and main boundary tests;
- presentation/CLI/tools: unit coverage target ≥60% and smoke tests.

Run the project's actual test, lint, type-check, and build commands. For browser-facing work, use Playwright for real interaction, console, network, screenshot, and responsive checks.

### 4. Review and close

Before declaring completion, inspect the diff, verify every acceptance criterion, review security/performance risks, and check that only in-scope files changed. Save a concise output record with changed files, raw verification output, and unverified items when the project defines `_Outputs/待审核/`. Wait for user approval before merge or archival.

### Bug mode

For a bug, record reproduction steps, impact, severity, and evidence first. For complex or cross-module bugs, produce one or two root-cause/remediation options and wait for the user's choice when the fix has material architectural impact. Implement the selected fix through a task card and add a regression test.

### Tool routing

`Context7` for current library docs; `Playwright` for real browser behavior; `GitHub` for repository/PR/CI context; `Figma` for design context; `visualize`/Mermaid for architecture; local test/lint/build commands for verification; Semgrep or CodeQL only when actually configured and available.
