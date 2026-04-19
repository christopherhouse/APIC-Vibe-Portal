/**
 * Tests for GET /api/config/telemetry
 *
 * Verifies that the route handler returns the Application Insights
 * connection string from the server-side environment variable, and
 * gracefully returns an empty string when the env var is not set.
 */

import { NextResponse } from 'next/server';
import { GET, type TelemetryConfig } from '../route';

// Mock NextResponse.json so we can inspect what was returned
jest.mock('next/server', () => ({
  NextResponse: {
    json: jest.fn((body: unknown) => ({ body })),
  },
}));

const mockedJsonFn = NextResponse.json as jest.MockedFunction<typeof NextResponse.json>;

describe('GET /api/config/telemetry', () => {
  const ORIGINAL_ENV = process.env;

  beforeEach(() => {
    jest.resetAllMocks();
    process.env = { ...ORIGINAL_ENV };
  });

  afterAll(() => {
    process.env = ORIGINAL_ENV;
  });

  it('returns the connection string when APPLICATIONINSIGHTS_CONNECTION_STRING is set', async () => {
    const testConnectionString =
      'InstrumentationKey=abc123;IngestionEndpoint=https://eastus.in.applicationinsights.azure.com/';
    process.env.APPLICATIONINSIGHTS_CONNECTION_STRING = testConnectionString;

    await GET();

    expect(mockedJsonFn).toHaveBeenCalledWith({
      connectionString: testConnectionString,
    } satisfies TelemetryConfig);
  });

  it('returns an empty connection string when APPLICATIONINSIGHTS_CONNECTION_STRING is not set', async () => {
    delete process.env.APPLICATIONINSIGHTS_CONNECTION_STRING;

    await GET();

    expect(mockedJsonFn).toHaveBeenCalledWith({
      connectionString: '',
    } satisfies TelemetryConfig);
  });
});
