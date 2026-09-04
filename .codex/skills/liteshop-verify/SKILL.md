---
name: liteshop-verify
description: Run LiteShop's five-plus-one acceptance checks for scope, tests, dependencies, implementation, types, and duplication.
---

# LiteShop 5+1 Acceptance

Run these checks in order and preserve real command output:

1. Scope: inspect `git status` and changed paths against the assigned territory.
2. Verification: rerun the contributor's documented lint, type, test, and build commands.
3. Dependencies: inspect imports and compare them with package manifests and Python requirements.
4. Implementation: read one or two representative files and reject TODO-only or placeholder code.
5. Types/build: run the applicable TypeScript, Python, and package build checks.
6. Duplication: compare new names, routes, enums, and CSS values with `.codex/project-context.md` and existing exports.

Do not mark a check complete when a command was skipped. Summarize failures with evidence and a clear accept/reject decision.
