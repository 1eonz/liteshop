import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { formatPrice } from '../dist/utils.js';

describe('formatPrice', () => {
  it('formats integer cents with two decimal places', () => {
    assert.equal(formatPrice(1999), '¥19.99');
    assert.equal(formatPrice(0), '¥0.00');
    assert.equal(formatPrice(-125), '¥-1.25');
  });

  it('supports a custom currency symbol', () => {
    assert.equal(formatPrice(2500, '$'), '$25.00');
    assert.equal(formatPrice(2500, ''), '25.00');
  });

  it('returns a placeholder for non-finite amounts', () => {
    assert.equal(formatPrice(Number.NaN), '-');
    assert.equal(formatPrice(Number.POSITIVE_INFINITY), '-');
    assert.equal(formatPrice(Number.NEGATIVE_INFINITY), '-');
  });
});
