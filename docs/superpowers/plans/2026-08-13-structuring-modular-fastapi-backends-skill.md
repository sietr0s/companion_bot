# Structuring Modular FastAPI Backends Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create, test, validate, and install a personal Codex skill that applies this repository's intended modular FastAPI backend architecture to new projects, module additions, focused refactoring, and architecture reviews.

**Architecture:** Build the skill in a disposable staging directory inside the writable repository, with a concise `SKILL.md`, two directly linked reference documents, and generated UI metadata. Establish baseline behavior with fresh-context application scenarios before authoring the skill, then rerun equivalent scenarios with the staged skill and install only the verified package into the personal Codex skills directory.

**Tech Stack:** Codex Agent Skills, Markdown, YAML, Python 3.11+, FastAPI, Pydantic, SQLAlchemy, pytest, PowerShell.

**Spec:** `docs/superpowers/specs/2026-08-13-structuring-modular-fastapi-backends-skill-design.md`

## Global Constraints

- Target Python 3.11+ FastAPI backends using Pydantic, SQLAlchemy, and pytest.
- Cover new projects, module additions, focused architecture refactoring, and reviews.
- Exclude frontend conventions, project generators, and project-specific Telegram/job behavior.
- Preserve the responsibility flow `router -> service -> repository -> model`.
- Forbid imports of another module's private models, repositories, services, dependencies, routers, and local schemas.
- Use shared serialized contracts for asynchronous integration and external interfaces or clients for synchronous integration.
- Forbid cross-module ORM relationships and foreign keys; store external identifiers instead.
- Treat handlers, internal APIs, events, and multi-file service packages as optional components selected by current behavior.
- Keep unrelated pre-existing architecture debt outside the requested change and report it separately.
- Install the completed skill at `C:\Users\astonuser\.codex\skills\structuring-modular-fastapi-backends`.
- Do not include evaluation logs, setup guides, changelogs, or generated project boilerplate in the installed package.

## File Map

- Create temporarily: `.tmp/structuring-modular-fastapi-backends/SKILL.md` — trigger metadata, core workflow, reference routing, quick checks, and common mistakes.
- Create temporarily: `.tmp/structuring-modular-fastapi-backends/references/architecture.md` — project areas, ownership, dependency rules, communication choices, composition root, errors, and test boundaries.
- Create temporarily: `.tmp/structuring-modular-fastapi-backends/references/module-blueprint.md` — one coherent module example showing optional file selection and layer responsibilities.
- Generate temporarily: `.tmp/structuring-modular-fastapi-backends/agents/openai.yaml` — Codex UI metadata derived from the finished skill.
- Install: `C:\Users\astonuser\.codex\skills\structuring-modular-fastapi-backends/**` — exact verified copy of the temporary package.
- Remove after installation: `.tmp/structuring-modular-fastapi-backends/` — ensure no skill build artifacts remain in the repository.

---

### Task 1: Establish Failing Baseline Scenarios

**Files:**

- Read: `docs/superpowers/specs/2026-08-13-structuring-modular-fastapi-backends-skill-design.md`
- Read: `docs/architecture.md`
- Read: `docs/isolation-rules.md`
- Create: none

**Interfaces:**

- Consumes: approved design requirements and raw hypothetical FastAPI task artifacts.
- Produces: exact observed baseline failures grouped as ownership, layering, coupling, over-scaffolding, and review omissions.

- [ ] **Step 1: Define four fresh-context application scenarios**

Use these prompts without exposing the design specification or the future skill:

```text
Scenario A — new capability
Design the backend file structure and responsibility split for a FastAPI billing capability.
It creates invoices, lists them through a public API, and stores them with SQLAlchemy. Show the
minimum files needed and state where validation, business rules, and database queries live.

Scenario B — cross-capability interaction
A checkout capability needs a customer email from users while creating an order, and must notify
analytics after success. Describe imports, interfaces/contracts, data ownership, and persistence
links. The response must be implementable in a modular monolith.

Scenario C — architecture review
Review this FastAPI design: an orders router calculates discounts and calls session.execute();
OrderService imports UserRepository; Order has a ForeignKey to users.id; an event topic is a
string literal; tests cover only the HTTP 200 response. Report actionable findings in priority
order and identify the responsible layer for each fix.

Scenario D — avoid unused structure
Add a read-only health policy capability that reads configuration and exposes one authenticated
endpoint. Decide the minimum module files. Explain whether it needs an ORM model, repository,
bus handler, event contract, internal router, and migration.
```

- [ ] **Step 2: Run every scenario without the new skill**

Dispatch each prompt to a fresh-context agent. State that it is a standalone hypothetical task
and that the host repository's conventions are not part of the task. Do not mention the intended
architecture or expected failures.

- [ ] **Step 3: Verify the RED condition**

Score each response against this observable contract:

```text
A: owner named; thin router; rules in service; SQL in repository; optional files omitted.
B: no private cross-module imports; sync client/interface for email; event contract for analytics;
   no cross-module ORM foreign key.
C: all five defects found; each mapped to router/service/repository/model/contracts/tests.
D: no model, repository, handler, event, internal router, or migration without stated behavior.
```

Expected: at least one response violates or omits one contract item. Quote the exact problematic
sentence and record why it would lead to the wrong architecture. If every response meets the
contract, stop skill authoring and report that the no-guidance control does not demonstrate a
failure.

- [ ] **Step 4: Classify the baseline failures**

Assign every observed failure to one of these forms so the skill uses the correct correction:

```text
wrong output shape -> positive responsibility recipe
missing review item -> explicit review checklist slot
wrong conditional choice -> observable if/then rule
boundary violation under pressure -> prohibition plus concrete counter-example
```

- [ ] **Step 5: Checkpoint the RED evidence**

Summarize the exact failures in the task transcript. Do not create an evaluation file in the
skill package or repository.

---

### Task 2: Build the Minimal Skill Package

**Files:**

- Create: `.tmp/structuring-modular-fastapi-backends/SKILL.md`
- Create: `.tmp/structuring-modular-fastapi-backends/references/architecture.md`
- Create: `.tmp/structuring-modular-fastapi-backends/references/module-blueprint.md`
- Generate: `.tmp/structuring-modular-fastapi-backends/agents/openai.yaml`

**Interfaces:**

- Consumes: baseline failure categories from Task 1 and the approved design.
- Produces: a staged skill named `structuring-modular-fastapi-backends` with two direct references and valid Codex UI metadata.

- [ ] **Step 1: Initialize the skill from the official scaffold**

Run:

```powershell
python C:\Users\astonuser\.codex\skills\.system\skill-creator\scripts\init_skill.py `
  structuring-modular-fastapi-backends `
  --path .tmp `
  --resources references `
  --interface "display_name=Structuring Modular FastAPI Backends" `
  --interface "short_description=Keep FastAPI modules isolated and layered" `
  --interface "default_prompt=Use $structuring-modular-fastapi-backends to structure or review this modular FastAPI backend change."
```

Expected: the staging package contains `SKILL.md`, `references/`, and `agents/openai.yaml`.

- [ ] **Step 2: Write the architecture reference**

Write `references/architecture.md` with these exact sections and contracts:

```markdown
# Modular FastAPI Architecture

## Project Areas
- Keep stable shared primitives in `base`, transport abstractions in `bus`, serialized integration
  payloads in `contracts`, application infrastructure in `core`, and business capabilities in
  `modules/<module>`.
- In an established repository, preserve equivalent existing areas; do not rename folders merely
  to match this vocabulary.

## Ownership and Dependencies
- Assign every business rule and table to one module.
- Allow a module to import its own code, shared primitives, infrastructure abstractions, and
  stable integration contracts.
- Forbid imports of another module's models, repositories, services, dependencies, routers, and
  local schemas.

## Cross-Module Communication
- If the caller requires an immediate answer to continue, depend on a synchronous client or
  interface outside both private module implementations.
- If work can occur later, crosses a transaction boundary, or has multiple consumers, publish a
  command or event through a transport-independent bus using a stable serialized contract.

## Layers and Composition
- Routers translate HTTP input, authentication context, and output.
- Services implement use cases, authorization, orchestration, and business decisions.
- Repositories implement SQLAlchemy reads and writes.
- Models map tables owned by the module.
- Module-local dependency factories assemble services and adapters.
- Handlers translate bus payloads into service calls.
- The composition root registers routers, handlers, concrete adapters, and lifecycle resources.

## Errors and Persistence
- Raise typed application exceptions from services and translate them to HTTP centrally.
- Keep SQLAlchemy statements and session persistence operations in repositories.
- Do not create foreign keys or ORM relationships between tables owned by different modules;
  store the external identifier instead.

## Testing Boundaries
- Mirror production modules under `tests/modules/<module>`.
- Test services as business behavior, repositories as database behavior, routers as transport,
  and producer/consumer agreement against the same integration contract.

## Architecture Review Checklist
- Check ownership, import direction, tables and foreign keys, router thickness, service rules,
  repository queries, contracts, topic constants, exception translation, test boundaries,
  migrations, configuration, documentation, and unrelated pre-existing debt.
```

Expand these statements only with corrections justified by Task 1. Keep every mandatory rule
from the approved specification and avoid framework tutorials.

- [ ] **Step 3: Write one internally consistent module blueprint**

Write `references/module-blueprint.md` around a `billing` capability and include:

```text
src/modules/billing/
  models.py
  repository.py
  service.py
  dependencies.py
  routers/public.py
  schemas/public/invoice.py
tests/modules/billing/
  test_repository.py
  test_service.py
  test_public_router.py
```

The example must show:

```python
class InvoiceRepository:
    async def list_for_account(
        self, session: AsyncSession, account_id: UUID
    ) -> Sequence[Invoice]: ...

class InvoiceService:
    async def create_invoice(
        self, session: AsyncSession, account_id: UUID, data: InvoiceCreate
    ) -> Invoice: ...
```

Keep HTTP parsing and status codes in the router, invoice rules in `InvoiceService`, and
SQLAlchemy statements in `InvoiceRepository`. Explain that events, handlers, internal routers,
service packages, and migrations are added only when the behavior requires them. Include one
cross-module event example whose payload lives in `contracts`, and one synchronous lookup example
through a client interface without a foreign key.

- [ ] **Step 4: Write the minimal SKILL.md**

Use exactly this frontmatter contract:

```yaml
---
name: structuring-modular-fastapi-backends
description: Use when creating, extending, refactoring, or reviewing Python FastAPI backends that need modular-monolith boundaries, service-repository layering, SQLAlchemy ownership, Pydantic integration contracts, or cross-module communication decisions.
---
```

Keep the body under 500 words. Include these sections:

```markdown
# Structuring Modular FastAPI Backends
## Core Principle
## Workflow
## Cross-Module Decision
## Completion Check
## Common Mistakes
```

In `Workflow`, require context inspection, owner selection, minimal component selection,
responsibility mapping, interaction selection, mirrored tests, and focused review. Link directly
to both references and state when each must be read. Shape the wording according to the baseline
failure forms from Task 1.

- [ ] **Step 5: Regenerate UI metadata from the finished skill**

Run:

```powershell
python C:\Users\astonuser\.codex\skills\.system\skill-creator\scripts\generate_openai_yaml.py `
  .tmp\structuring-modular-fastapi-backends `
  --interface "display_name=Structuring Modular FastAPI Backends" `
  --interface "short_description=Keep FastAPI modules isolated and layered" `
  --interface "default_prompt=Use $structuring-modular-fastapi-backends to structure or review this modular FastAPI backend change."
```

Expected: `agents/openai.yaml` contains only supported UI fields and references the literal skill
name in `default_prompt`.

- [ ] **Step 6: Run structural validation**

Run:

```powershell
python C:\Users\astonuser\.codex\skills\.system\skill-creator\scripts\quick_validate.py `
  .tmp\structuring-modular-fastapi-backends
```

Expected: validation succeeds with no frontmatter or naming errors.

---

### Task 3: Forward-Test and Refine the Skill

**Files:**

- Modify if tests expose a gap: `.tmp/structuring-modular-fastapi-backends/SKILL.md`
- Modify if tests expose a gap: `.tmp/structuring-modular-fastapi-backends/references/architecture.md`
- Modify if tests expose a gap: `.tmp/structuring-modular-fastapi-backends/references/module-blueprint.md`
- Regenerate after a metadata change: `.tmp/structuring-modular-fastapi-backends/agents/openai.yaml`

**Interfaces:**

- Consumes: the four Task 1 scenarios and the staged `$structuring-modular-fastapi-backends` skill.
- Produces: application responses satisfying every observable contract item without unnecessary structure.

- [ ] **Step 1: Run equivalent scenarios with the skill**

Dispatch four fresh-context agents, one per scenario, using this wrapper:

```text
Use $structuring-modular-fastapi-backends at
.tmp/structuring-modular-fastapi-backends to solve the following standalone task.
Read only the skill references that its workflow requires.
```

Append exactly one of the following complete tasks to each dispatch:

```text
Design the backend file structure and responsibility split for a FastAPI billing capability.
It creates invoices, lists them through a public API, and stores them with SQLAlchemy. Show the
minimum files needed and state where validation, business rules, and database queries live.
```

```text
A checkout capability needs a customer email from users while creating an order, and must notify
analytics after success. Describe imports, interfaces/contracts, data ownership, and persistence
links. The response must be implementable in a modular monolith.
```

```text
Review this FastAPI design: an orders router calculates discounts and calls session.execute();
OrderService imports UserRepository; Order has a ForeignKey to users.id; an event topic is a
string literal; tests cover only the HTTP 200 response. Report actionable findings in priority
order and identify the responsible layer for each fix.
```

```text
Add a read-only health policy capability that reads configuration and exposes one authenticated
endpoint. Decide the minimum module files. Explain whether it needs an ORM model, repository,
bus handler, event contract, internal router, and migration.
```

- [ ] **Step 2: Score every response against the unchanged contract**

Expected: all A-D contract items pass. Read each response manually; do not count keyword matches
as proof of correct architecture.

- [ ] **Step 3: Refine only demonstrated gaps**

For each failure, update the file that owns the missing guidance:

```text
trigger missed -> SKILL.md description
workflow order or completion omission -> SKILL.md
architecture decision or boundary gap -> references/architecture.md
layer/example ambiguity -> references/module-blueprint.md
```

Use a positive recipe for output-shape failures, a structural checklist slot for omissions, an
observable conditional for decisions, and a direct prohibition only for demonstrated boundary
rationalizations.

- [ ] **Step 4: Rerun failed scenarios**

Expected: the corrected scenario passes every original contract item and introduces no extra
layers or optional components.

- [ ] **Step 5: Revalidate after refinement**

Run `quick_validate.py` again with the command from Task 2. If `SKILL.md` metadata changed,
regenerate `agents/openai.yaml` before validation.

---

### Task 4: Verify and Install the Personal Skill

**Files:**

- Read: `.tmp/structuring-modular-fastapi-backends/**`
- Create: `C:\Users\astonuser\.codex\skills\structuring-modular-fastapi-backends/**`
- Remove: `.tmp/structuring-modular-fastapi-backends/**`

**Interfaces:**

- Consumes: the validated staged package from Task 3.
- Produces: one discoverable personal Codex skill whose installed bytes match the verified stage.

- [ ] **Step 1: Perform final static checks**

Run:

```powershell
$patterns = @('T' + 'BD', 'T' + 'ODO', 'FIX' + 'ME', 'PLACE' + 'HOLDER')
rg -n ($patterns -join '|') .tmp\structuring-modular-fastapi-backends
(Get-Content .tmp\structuring-modular-fastapi-backends\SKILL.md -Raw | Measure-Object -Word).Words
```

Expected: no placeholder matches and the `SKILL.md` body plus frontmatter remains under 500 words.

- [ ] **Step 2: Validate the exact installation target**

Resolve `C:\Users\astonuser\.codex\skills\structuring-modular-fastapi-backends`. If the target
already exists, stop and request permission before replacing any file. If it does not exist,
create it and copy only `SKILL.md`, `agents/`, and `references/` from the staged package.

- [ ] **Step 3: Compare staged and installed files**

Run:

```powershell
$stage = Get-ChildItem .tmp\structuring-modular-fastapi-backends -Recurse -File
$installed = Get-ChildItem C:\Users\astonuser\.codex\skills\structuring-modular-fastapi-backends -Recurse -File
$stage | ForEach-Object { Get-FileHash -Algorithm SHA256 $_.FullName }
$installed | ForEach-Object { Get-FileHash -Algorithm SHA256 $_.FullName }
```

Expected: the two file sets have the same relative paths and SHA-256 values.

- [ ] **Step 4: Validate the installed package**

Run:

```powershell
python C:\Users\astonuser\.codex\skills\.system\skill-creator\scripts\quick_validate.py `
  C:\Users\astonuser\.codex\skills\structuring-modular-fastapi-backends
```

Expected: validation succeeds from the final location.

- [ ] **Step 5: Remove the staging package**

Delete only the resolved directory
`C:\Users\astonuser\PycharmProjects\micromonolit\.tmp\structuring-modular-fastapi-backends`
after verifying it is inside the repository and the installed copy passes validation. Remove the
empty `.tmp` directory only if it was created by this plan and contains no other entries.

- [ ] **Step 6: Verify repository scope**

Run:

```powershell
git status --short
```

Expected: no staged skill package remains. Existing unrelated user changes are untouched; only
the approved design and implementation-plan documents belong to this workflow.

- [ ] **Step 7: Report completion evidence**

Report the installed path, package files, baseline failures, forward-test outcomes, validator
result, and whether Codex requires a new task before the newly installed skill appears in skill
discovery.
