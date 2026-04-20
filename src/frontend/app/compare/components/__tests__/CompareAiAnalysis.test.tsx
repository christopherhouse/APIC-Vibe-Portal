import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import CompareAiAnalysis from '../CompareAiAnalysis';
import type { CompareResponse } from '@/lib/compare-api';

jest.mock('@/lib/compare-api', () => ({
  compareApisWithAi: jest.fn(),
}));

import { compareApisWithAi } from '@/lib/compare-api';

jest.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(),
}));

const mockResult: CompareResponse = {
  apis: [
    {
      id: '/apis/api-1',
      name: 'api-1',
      title: 'API One',
      description: 'First',
      kind: 'rest',
      lifecycleStage: 'production',
    },
    {
      id: '/apis/api-2',
      name: 'api-2',
      title: 'API Two',
      description: 'Second',
      kind: 'graphql',
      lifecycleStage: 'development',
    },
  ],
  aspects: [],
  similarityScore: 0.5,
  aiAnalysis: null,
};

describe('CompareAiAnalysis', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the component', () => {
    render(<CompareAiAnalysis result={mockResult} onAnalysisLoaded={jest.fn()} />);
    expect(screen.getByTestId('compare-ai-analysis')).toBeInTheDocument();
  });

  it('shows "Generate AI Analysis" button when no analysis available', () => {
    render(<CompareAiAnalysis result={mockResult} onAnalysisLoaded={jest.fn()} />);
    expect(screen.getByTestId('request-ai-analysis-button')).toBeInTheDocument();
  });

  it('shows the analysis text when available', () => {
    const resultWithAnalysis = { ...mockResult, aiAnalysis: 'This is a great API.' };
    render(<CompareAiAnalysis result={resultWithAnalysis} onAnalysisLoaded={jest.fn()} />);
    expect(screen.getByText(/This is a great API/)).toBeInTheDocument();
    expect(screen.queryByTestId('request-ai-analysis-button')).not.toBeInTheDocument();
  });

  it('calls compareApisWithAi on button click', async () => {
    const user = userEvent.setup();
    const onAnalysisLoaded = jest.fn();
    (compareApisWithAi as jest.Mock).mockResolvedValue({
      ...mockResult,
      aiAnalysis: 'AI says yes',
    });

    render(<CompareAiAnalysis result={mockResult} onAnalysisLoaded={onAnalysisLoaded} />);

    await user.click(screen.getByTestId('request-ai-analysis-button'));

    expect(compareApisWithAi).toHaveBeenCalledWith({ apiIds: ['api-1', 'api-2'] });
    expect(onAnalysisLoaded).toHaveBeenCalled();
  });

  it('shows error message when analysis fails', async () => {
    const user = userEvent.setup();
    (compareApisWithAi as jest.Mock).mockRejectedValue(new Error('Service unavailable'));

    render(<CompareAiAnalysis result={mockResult} onAnalysisLoaded={jest.fn()} />);

    await user.click(screen.getByTestId('request-ai-analysis-button'));

    expect(await screen.findByText('Service unavailable')).toBeInTheDocument();
  });
});
