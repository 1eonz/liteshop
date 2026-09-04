---
name: fix
description: Automatically diagnose and repair formatting, lint, and TypeScript build errors in the current project.
---

# LiteShop Local Compatibility Skill

This is a local compatibility implementation because no public market source named `fix` was available during initialization.

## Workflow

1. Inspect the package scripts and identify the repository's formatter, linter, and type checker.
2. Run the narrowest checks first, then the repository-level checks.
3. Apply only deterministic fixes with the existing tools (for example `pnpm exec prettier --write`, `pnpm exec eslint --fix`, and `tsc --noEmit`).
4. Never suppress a diagnostic, weaken a rule, or change tests to hide a failure.
5. Re-run every check after edits and report remaining errors with file paths and line numbers.

## LiteShop constraints

- Preserve the territory rules in `AGENTS.md`.
- Do not introduce dependencies or change public contracts while fixing style/type errors.
- Keep CSS values in the project's design-token variables.
