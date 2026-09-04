---
name: liteshop-style
description: Check LiteShop UI code against docs/设计规范.md, design tokens, responsive rules, and the project's accessibility expectations.
---

# LiteShop Design Rules

- Read `docs/设计规范.md` before judging visual code.
- Reject hard-coded colors, font sizes, spacing, radii, and shadows when a project CSS variable exists.
- Check typography hierarchy, contrast, focus states, responsive layout, loading/empty states, and motion preferences.
- Keep buttons and controls semantic; use familiar icons with accessible names where appropriate.
- Check for nested cards, oversized dashboard headings, unstable dimensions, text overflow, and overlapping content.
- Report exact selectors/components and suggest token-based corrections. Do not rewrite unrelated UI.
