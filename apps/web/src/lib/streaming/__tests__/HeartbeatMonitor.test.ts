/**
 * Tests for HeartbeatMonitor.
 *
 * Task #74: Response Streaming Improvements
 */

import { HeartbeatMonitor, createHeartbeatMonitor } from '../HeartbeatMonitor';

describe('HeartbeatMonitor', () => {
  let monitor: HeartbeatMonitor;
  let onTimeout: jest.Mock;
  let onHeartbeat: jest.Mock;

  beforeEach(() => {
    onTimeout = jest.fn();
    onHeartbeat = jest.fn();
    monitor = new HeartbeatMonitor({
      timeoutMs: 1000,
      onTimeout,
      onHeartbeat,
    });
  });

  describe('recordActivity', () => {
    it('should update lastActivity timestamp', () => {
      const before = monitor.getElapsedMs();
      monitor.recordActivity();
      const after = monitor.getElapsedMs();
      expect(after).toBeLessThan(before + 50);
    });

    it('should reset timedOut flag', () => {
      monitor['timedOut'] = true;
      monitor.recordActivity();
      expect(monitor.isTimedOut()).toBe(false);
    });
  });

  describe('check', () => {
    it('should return false when not timed out', () => {
      expect(monitor.check()).toBe(false);
    });

    it('should return true after timeout', () => {
      // Simulate time passing
      monitor['lastActivity'] = Date.now() - 1100;
      expect(monitor.check()).toBe(true);
      expect(onTimeout).toHaveBeenCalled();
    });

    it('should return true once already timed out', () => {
      monitor['timedOut'] = true;
      expect(monitor.check()).toBe(true);
    });
  });

  describe('handleHeartbeat', () => {
    it('should record activity', () => {
      monitor.handleHeartbeat();
      expect(monitor.getElapsedMs()).toBeLessThan(50);
    });

    it('should call onHeartbeat callback', () => {
      monitor.handleHeartbeat();
      expect(onHeartbeat).toHaveBeenCalled();
    });
  });

  describe('reset', () => {
    it('should reset all state', () => {
      monitor['timedOut'] = true;
      monitor['lastActivity'] = Date.now() - 5000;

      monitor.reset();

      expect(monitor.isTimedOut()).toBe(false);
      expect(monitor.getElapsedMs()).toBeLessThan(50);
    });
  });

  describe('createHeartbeatMonitor', () => {
    it('should create monitor with seconds', () => {
      const timeoutFn = jest.fn();
      const m = createHeartbeatMonitor(30, timeoutFn);
      expect(m).toBeInstanceOf(HeartbeatMonitor);
      expect(m['timeoutMs']).toBe(30000);
    });
  });
});
