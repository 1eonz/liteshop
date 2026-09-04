---
name: liteshop-territory
description: Check LiteShop changes against AGENTS.md ownership boundaries and detect cross-territory edits.
---

# LiteShop Territory Check

Use this skill before accepting a sub-agent change.

1. Read the territory table in `AGENTS.md`.
2. Compare `git status --short` and `git diff --name-only` with the agent's assigned territory.
3. Flag edits outside that territory, including generated files and unrelated deletes.
4. Check that shared types are imported rather than redefined and that API calls use existing wrappers.
5. Report `PASS`, `REJECT`, or `BLOCKED` with the offending paths and the smallest required handoff.

Do not revert user changes or modify another agent's territory while performing the check.
