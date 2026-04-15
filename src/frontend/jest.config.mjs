import nextJest from 'next/jest.js';

const createJestConfig = nextJest({
  dir: './',
});

/** @type {import('jest').Config} */
const config = {
  displayName: '@apic-vibe-portal/frontend',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/__tests__/setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  modulePathIgnorePatterns: ['<rootDir>/.next/'],
  testMatch: [
    '<rootDir>/**/__tests__/**/*.test.{ts,tsx}',
    '<rootDir>/**/*.test.{ts,tsx}',
  ],
  collectCoverageFrom: [
    'components/**/*.{ts,tsx}',
    'lib/**/*.{ts,tsx}',
    'hooks/**/*.{ts,tsx}',
    '!**/*.d.ts',
    '!**/index.ts',
  ],
};

export default createJestConfig(config);
