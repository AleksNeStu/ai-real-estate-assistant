/* eslint-disable @typescript-eslint/no-require-imports */
const nextJest = require('next/jest');

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files in your test environment
  dir: './',
});

const nodeMajor = Number.parseInt(process.versions.node.split('.')[0] ?? '0', 10);

// Add any custom config to be passed to Jest
const config = {
  coverageProvider: 'v8',
  coverageReporters: ['json', 'json-summary', 'text', 'lcov', 'clover'],
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  modulePathIgnorePatterns: ['<rootDir>/.next/'],
  watchPathIgnorePatterns: ['<rootDir>/.next/'],
  ...(nodeMajor >= 22 ? { maxWorkers: 1 } : {}),
  moduleNameMapper: {
    // Handle module aliases (this will be automatically configured for you soon)
    '^@/(.*)$': '<rootDir>/src/$1',
    // Mock next-intl to avoid ESM issues
    '^next-intl$': '<rootDir>/__mocks__/next-intl.tsx',
    '^next-intl/navigation$': '<rootDir>/__mocks__/next-intl-navigation.tsx',
    // Mock next/navigation to avoid ESM issues
    '^next/navigation$': '<rootDir>/__mocks__/next-navigation.tsx',
  },
  // Transform ESM modules from node_modules
  transformIgnorePatterns: [
    'node_modules/(?!(next-intl|use-intl|@radix-ui|lucide-react|recharts|framer-motion)/)',
  ],
  collectCoverage: true,
  collectCoverageFrom: [
    // The library layers (utilities, API, streaming)
    'src/lib/**/*.{js,jsx,ts,tsx}',
    'src/lib/streaming/**/*.{js,jsx,ts,tsx}',
    // Include i18n config
    'src/i18n/**/*.{js,jsx,ts,tsx}',
    // Include contexts
    'src/contexts/**/*.{js,jsx,ts,tsx}',
    // Include hooks
    'src/hooks/**/*.{js,jsx,ts,tsx}',
    // The components and the pages: they are most of the product, and a
    // gate that cannot see them says nothing about the code the product is
    // made of. A component without a test now costs the gate something.
    'src/components/**/*.{js,jsx,ts,tsx}',
    'src/app/**/*.{js,jsx,ts,tsx}',
    // Exclude type definitions
    '!src/**/*.d.ts',
    '!src/lib/types.ts',
    // Exclude test files from coverage
    '!src/**/__tests__/**',
    '!src/**/*.test.{js,jsx,ts,tsx}',
    '!src/**/*.spec.{js,jsx,ts,tsx}',
  ],
  // The floors live in their own file: the gate's configuration is read by
  // the test that keeps the floors honest, and a JSON file can be read
  // without evaluating the whole Next.js wrapper.
  //
  // There is one floor per part of the frontend and no global one. The
  // aggregate over every file is a number that moves when a file that is
  // not covered by any test is added, and it says nothing about which part
  // moved. The parts say it: the library layers, the components, the pages,
  // the contexts, the hooks and the i18n catalogue each hold their own
  // floor, and together they cover the whole tree.
  coverageThreshold: require('./jest.coverage-thresholds.json'),
};

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(config);
