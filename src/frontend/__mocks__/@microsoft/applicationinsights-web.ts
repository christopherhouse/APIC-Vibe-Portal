/**
 * Jest mock for @microsoft/applicationinsights-web
 */

export const DistributedTracingModes = {
  AI: 0,
  AI_AND_W3C: 1,
  W3C: 2,
};

export const ApplicationInsights = jest.fn().mockImplementation(() => ({
  loadAppInsights: jest.fn(),
  trackPageView: jest.fn(),
  trackEvent: jest.fn(),
  trackException: jest.fn(),
  trackMetric: jest.fn(),
  trackTrace: jest.fn(),
}));
