import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { createDebouncedAction } from '../dist/useDebounceAction.js';

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

describe('createDebouncedAction', () => {
  it('blocks concurrent calls and enforces the cooldown period', async () => {
    let calls = 0;
    let resolveAction;
    const action = createDebouncedAction(
      async () => {
        calls += 1;
        await new Promise((resolve) => {
          resolveAction = resolve;
        });
      },
      { getDelay: () => 20 },
    );

    const first = action.run();
    const second = action.run();
    assert.equal(calls, 1);
    assert.equal(action.isRunning(), true);

    resolveAction();
    await wait(0);
    assert.equal(action.isRunning(), true);
    const cooldownCall = action.run();
    await cooldownCall;
    await first;
    assert.equal(calls, 1);

    assert.equal(action.isRunning(), false);
    const third = action.run();
    assert.equal(calls, 2);
    resolveAction();
    await third;
    await second;
  });

  it('releases after an exception while preserving the original error', async () => {
    const expected = new Error('request failed');
    let calls = 0;
    const action = createDebouncedAction(
      async () => {
        calls += 1;
        throw expected;
      },
      { getDelay: () => 10 },
    );

    const pending = action.run();
    await wait(1);
    assert.equal(action.isRunning(), true);
    await assert.rejects(pending, (error) => error === expected);
    assert.equal(action.isRunning(), false);

    await assert.rejects(action.run(), (error) => error === expected);
    assert.equal(calls, 2);
  });

  it('cancels cooldown and suppresses notifications after disposal', async () => {
    const states = [];
    const action = createDebouncedAction(() => undefined, {
      getDelay: () => 100,
      onStateChange: (running) => states.push(running),
    });

    const pending = action.run();
    action.dispose();
    await pending;

    assert.equal(action.isRunning(), false);
    assert.deepEqual(states, [true]);
    await action.run();
    assert.deepEqual(states, [true]);
  });
});
