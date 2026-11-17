import fs from 'node:fs';
import path from 'node:path';

import thresholds from '../../jest.coverage-thresholds.json';

/**
 * The coverage gate, and the numbers it holds the product to.
 *
 * The gate collected from the library layers only, so a component without a
 * test cost it nothing - and the product is mostly components and pages.
 * The scope is widened now, and the floors are a ratchet: the numbers below
 * are what the widened scope measured, and the floor may not be raised above
 * them without measuring again.
 *
 * The test reads the gate's own configuration, so the gate cannot quietly
 * lose a path, lose a floor, or be raised past what was measured.
 */

type CoverageFloors = {
  statements: number;
  branches: number;
  functions: number;
  lines: number;
};

// What the widened scope measured on 2026-11-17 (Jest 1.65, the whole
// frontend suite, 1690 tests). The floors sit below these numbers.
const MEASURED: Record<string, CoverageFloors> = {
  './src/lib/': { statements: 87.03, branches: 87.08, functions: 88.16, lines: 87.03 },
  './src/components/': {
    statements: 54.46,
    branches: 73.66,
    functions: 62.89,
    lines: 54.46,
  },
  './src/app/': { statements: 59.76, branches: 69.21, functions: 46.53, lines: 59.76 },
  './src/contexts/': {
    statements: 68.23,
    branches: 74.07,
    functions: 25.0,
    lines: 68.23,
  },
  './src/hooks/': {
    statements: 85.65,
    branches: 84.44,
    functions: 63.63,
    lines: 85.65,
  },
  './src/i18n/': { statements: 62.98, branches: 85.71, functions: 58.33, lines: 62.98 },
};

const jestConfigSource = fs.readFileSync(
  path.join(process.cwd(), 'jest.config.js'),
  'utf-8'
);

describe('the coverage gate', () => {
  it('measures the components and the pages, not only the library layers', () => {
    expect(jestConfigSource).toContain('src/components/**');
    expect(jestConfigSource).toContain('src/app/**');
    expect(jestConfigSource).toContain('src/lib/**');
  });

  it('holds a floor for every part of the frontend', () => {
    for (const scope of Object.keys(MEASURED)) {
      const floors = (thresholds as Record<string, CoverageFloors>)[scope];

      expect(floors).toBeDefined();
      expect(floors.statements).toBeGreaterThan(0);
      expect(floors.branches).toBeGreaterThan(0);
      expect(floors.functions).toBeGreaterThan(0);
      expect(floors.lines).toBeGreaterThan(0);
    }
  });

  it('keeps every floor below the number that was measured', () => {
    const floorsAboveTheMeasurement: string[] = [];

    for (const [scope, floors] of Object.entries(thresholds)) {
      const measured = MEASURED[scope];
      if (!measured) continue;

      for (const metric of ['statements', 'branches', 'functions', 'lines'] as const) {
        if (floors[metric as keyof CoverageFloors] > measured[metric]) {
          floorsAboveTheMeasurement.push(`${scope}.${metric}`);
        }
      }
    }

    expect(floorsAboveTheMeasurement).toEqual([]);
  });

  it('covers every scope the gate measures', () => {
    // A scope in the configuration with no measured number would let the
    // floor float free.
    expect(Object.keys(thresholds).sort()).toEqual(Object.keys(MEASURED).sort());
  });
});
