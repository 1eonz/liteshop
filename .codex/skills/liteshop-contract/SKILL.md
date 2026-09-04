---
name: liteshop-contract
description: Audit LiteShop API and shared-type changes against the versioned OpenAPI contracts and enum conventions.
---

# LiteShop Contract Review

Use this skill when reviewing or changing API payloads, routes, error codes, enums, or shared types.

- Read the relevant file under `docs/api-contracts/v1/` before inspecting implementation.
- Verify request/response names, nullability, units, ISO-8601 timestamps, pagination, and error envelopes.
- Ensure frontend types come from `@liteshop/shared-types` and backend DTOs use the required Pydantic suffixes.
- Check that route paths use kebab-case plural nouns and that enum values remain uppercase snake case.
- Flag breaking changes; do not silently update consumers across another territory.

Return a finding list with severity and exact file locations, followed by a contract compatibility conclusion.
