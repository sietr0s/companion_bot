# Project skills

Use the repository skills in `.agents/skills` when the task matches:

- `python-design-patterns`: backend architecture and refactoring; keep responsibilities
  separate and use constructor injection. Existing ADRs take precedence over generic layouts.
- `python-testing-patterns`: pytest, async/database boundaries and failure cases.
- `javascript-testing-patterns`: frontend tests with our existing Vitest/Testing Library.
- `vercel-react-best-practices`: React rendering, data fetching and bundle performance.
  This project uses Vite, React 18 and React Query: use React.lazy/Suspense, preserve
  React Query, and skip Next.js, RSC, React 19 and SWR-specific instructions.
- `web-design-guidelines`: accessibility and UI reviews. Fetch current guidelines when
  possible; an explicitly dated offline snapshot is included for offline development.

Read the matching SKILL.md and relevant references before applying it. Do not install
new libraries just because an example uses them, mass-reformat code, lower CI floors,
update quality baselines automatically, or change public contracts without a task reason.
Test observable behavior and failures; avoid tests that merely mirror implementation.

Upstream sources and pinned commits are recorded in `.agents/skills/sources.json`.
These skills guide agent work; Ruff, mypy, tests and CI remain the enforcement tools.
