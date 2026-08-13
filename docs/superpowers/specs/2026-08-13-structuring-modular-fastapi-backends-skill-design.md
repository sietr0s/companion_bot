# Structuring Modular FastAPI Backends Skill Design

## Purpose

Create a personal Codex skill based on the backend organization principles demonstrated by
this repository. The skill guides new FastAPI projects, new business modules, focused
refactoring, and architecture reviews.

The skill captures the intended architecture, not every current implementation detail. Existing
boundary violations in the source project are evidence for review checks, not patterns to copy.

## Scope

The skill targets Python 3.11+ backends built with FastAPI, Pydantic, SQLAlchemy, and pytest. It
does not prescribe the React/Vite frontend structure and does not generate a complete project
template.

It applies to:

- structuring a new modular FastAPI backend;
- adding a business capability or module;
- refactoring code toward explicit module and layer boundaries;
- reviewing architecture, imports, persistence ownership, contracts, and tests.

## Installation

Install the skill as a personal Codex skill at:

`C:\Users\astonuser\.codex\skills\structuring-modular-fastapi-backends`

The project repository remains unchanged apart from this design specification.

## Skill Package

```text
structuring-modular-fastapi-backends/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── architecture.md
    └── module-blueprint.md
```

`SKILL.md` contains the concise decision workflow and completion checklist.

`references/architecture.md` describes the reusable architectural rules: project areas, module
ownership, permitted dependency directions, persistence ownership, asynchronous contracts,
synchronous clients, composition root, and test organization.

`references/module-blueprint.md` provides one concrete Python example and explains the roles of
models, repositories, services, dependencies, handlers, routers, schemas, and matching tests.

No scripts or assets are required. Code generation would reduce adaptability and duplicate
work that Codex can perform from the blueprint.

## Core Architectural Model

Organize shared backend code into the following areas when the host project does not already
have equivalent conventions:

- `base`: stable shared primitives such as generic ORM, repository, and service types;
- `bus`: transport-independent producer and consumer interfaces plus implementations;
- `contracts`: stable serialized payloads shared between modules;
- `core`: application infrastructure, configuration, database setup, security, clients,
  exceptions, and composition;
- `modules/<module>`: one cohesive business capability with its own logic and tables.

Within a module, use the responsibility flow `router -> service -> repository -> model`:

- routers translate HTTP and authentication context and remain thin;
- services own use cases, authorization rules, orchestration, and business decisions;
- repositories own SQLAlchemy queries and persistence operations;
- models belong to exactly one module;
- module-local dependency factories assemble repositories, services, and adapters;
- handlers translate bus messages into service calls;
- schemas are separated by public HTTP, internal HTTP, and integration concerns when those
  distinctions exist.

The structure is responsibility-driven rather than file-count-driven. A small module may use a
single `service.py`; a larger module may use `services/`. Components that have no current use are
omitted.

## Module Boundaries

Each business module owns its models, tables, repositories, services, local schemas, and rules.
A module must not import another module's models, repositories, services, dependency providers,
routers, or local schemas.

Cross-module communication uses one of two explicit mechanisms:

- asynchronous commands or events through a transport-independent bus and stable contracts;
- synchronous interfaces or clients owned outside both module implementations.

Shared integration contracts must remain serializable and independent of a module's internal
implementation. Topic names have one source of truth. Consumers validate the same contract that
producers publish.

Tables from different modules do not use ORM relationships or foreign keys to each other.
References to another module's entity are stored as external identifiers. Foreign keys within a
single module remain valid.

## Skill Workflow

For each request, the skill instructs Codex to:

1. Read repository instructions, architecture documents, configuration, and representative
   neighboring code before proposing a structure.
2. Identify the business capability that owns the behavior and data.
3. Map responsibilities to the smallest necessary set of layers and files.
4. Select an explicit cross-module interaction mechanism when another module is involved.
5. Implement or review the change while preserving local conventions that do not violate the
   core boundaries.
6. Add tests in a structure that mirrors the production module, including contract or event-flow
   tests where integration behavior changes.
7. Review imports, table ownership, foreign keys, topic names, contracts, router thickness,
   persistence placement, typed exceptions, configuration, migrations, and documentation.

For existing repositories, the skill limits refactoring to the affected capability. It reports
pre-existing boundary violations separately and does not expand scope without user approval.

## Errors and Infrastructure

Use shared typed application exceptions at the service boundary and translate them centrally to
HTTP responses. Do not couple business services to HTTP response types.

Infrastructure details belong behind interfaces or adapters. Services may depend on abstractions
for a message producer, file storage, external APIs, or similar systems. Application startup is a
composition root that connects routers, handlers, concrete adapters, and lifecycle operations;
it does not own business rules.

## Testing Strategy

Develop the skill with RED-GREEN-REFACTOR:

1. Run baseline scenarios without the new skill.
2. Record incorrect responsibility placement, hidden coupling, unnecessary structure, or missed
   review findings.
3. Write the smallest guidance that corrects observed failures.
4. Run equivalent scenarios with the skill.
5. Refine only where new gaps appear.

Use at least these application scenarios:

- add a billing-like module with public endpoints and persistence;
- integrate two modules without importing private implementation details;
- review code containing a fat router, direct SQL in a service, a cross-module model import, and
  a cross-module foreign key;
- decide that a small read-only capability does not need unused handlers or bus contracts.

Success means the agent assigns ownership correctly, preserves module boundaries, selects only
necessary components, places business logic and queries in the intended layers, mirrors tests,
and distinguishes new changes from unrelated existing debt.

Validate the finished package using the `skill-creator` validation script and confirm that
`agents/openai.yaml` accurately represents `SKILL.md`.

## Non-Goals

- Reproducing every file in this repository.
- Encoding project-specific Telegram, classifier, notification, or job-matching behavior.
- Prescribing microservices or requiring that modules eventually become microservices.
- Generating Alembic revisions or project boilerplate automatically.
- Refactoring unrelated architecture during a focused change.
- Covering frontend organization.

## Acceptance Criteria

- The personal skill is discoverable under the agreed name.
- Its trigger covers new projects, module additions, architecture refactoring, and reviews for
  Python/FastAPI modular backends.
- `SKILL.md` stays concise and delegates details to the two direct reference files.
- The reference material contains one strong, internally consistent Python example.
- Guidance distinguishes mandatory boundaries from optional module components.
- Baseline and forward scenarios demonstrate a measurable improvement.
- Structural validation passes and the UI metadata matches the skill.
