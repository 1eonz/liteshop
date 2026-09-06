import test from 'node:test';
import assert from 'node:assert/strict';

import { clampSceneSpeed, createHero3DConfig, shouldUse3DFallback } from '../dist/index.js';

test('creates token-based scene defaults', () => {
  const config = createHero3DConfig({ preset: 'particle-network' });
  assert.equal(config.preset, 'particle-network');
  assert.match(config.primaryColor, /^var\(--/);
});

test('downgrades on constrained devices or reduced motion', () => {
  assert.equal(
    shouldUse3DFallback({
      isMobile: true,
      hardwareConcurrency: 8,
      deviceMemoryGb: 8,
      reducedMotion: false,
    }),
    true,
  );
  assert.equal(
    shouldUse3DFallback({
      isMobile: false,
      hardwareConcurrency: 8,
      deviceMemoryGb: 8,
      reducedMotion: true,
    }),
    true,
  );
  assert.equal(
    shouldUse3DFallback({
      isMobile: false,
      hardwareConcurrency: 8,
      deviceMemoryGb: 8,
      reducedMotion: false,
    }),
    false,
  );
});

test('clamps scene speed to a stable range', () => {
  assert.equal(clampSceneSpeed(-1), 0);
  assert.equal(clampSceneSpeed(4), 1.5);
  assert.equal(clampSceneSpeed(Number.NaN), 0.35);
});
