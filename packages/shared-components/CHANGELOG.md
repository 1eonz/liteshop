# Changelog

## [0.2.0] - 2026-09-06

### Added

- ProductCard accepts either flat integer-cent props or a `ProductSummary` model.
- ProductCard accepts optional translated subtitle and sales label content.
- Exported `createDebouncedAction` for framework-independent action orchestration and testing.
- Exported the shared stylesheet at `@liteshop/shared-components/styles.css`.

### Changed

- ProductCard now formats prices through `@liteshop/shared-types` `formatPrice`.
- ProductCard and state components no longer embed Chinese display text; callers can provide localized content.
- `useDebounceAction` cancels pending cooldown timers when disposed and suppresses post-unmount state updates.
