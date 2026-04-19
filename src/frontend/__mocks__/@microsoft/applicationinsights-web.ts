/**
 * Jest mock for @microsoft/applicationinsights-web
 */

export const ApplicationInsights = jest.fn().mockImplementation(() => ({
  loadAppInsights: jest.fn(),
  trackPageView: jest.fn(),
  trackEvent: jest.fn(),
  trackException: jest.fn(),
  trackMetric: jest.fn(),
  trackTrace: jest.fn(),
}));
