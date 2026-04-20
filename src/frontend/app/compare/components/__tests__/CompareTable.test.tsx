import { render, screen } from '../../../../__tests__/test-utils';
import CompareTable from '../CompareTable';
import type { CompareResponse } from '@/lib/compare-api';

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
  aspects: [
    {
      aspect: 'metadata.kind',
      label: 'API Kind',
      values: [
        { value: 'rest', display: 'rest', isBest: false },
        { value: 'graphql', display: 'graphql', isBest: false },
      ],
      allEqual: false,
    },
    {
      aspect: 'versions.count',
      label: 'Version Count',
      values: [
        { value: '2', display: '2 versions', isBest: true },
        { value: '1', display: '1 version', isBest: false },
      ],
      allEqual: false,
    },
  ],
  similarityScore: 0.3,
  aiAnalysis: null,
};

describe('CompareTable', () => {
  it('renders the table container', () => {
    render(<CompareTable result={mockResult} />);
    expect(screen.getByTestId('compare-table')).toBeInTheDocument();
  });

  it('renders API titles as column headers', () => {
    render(<CompareTable result={mockResult} />);
    expect(screen.getByText('API One')).toBeInTheDocument();
    expect(screen.getByText('API Two')).toBeInTheDocument();
  });

  it('renders aspect row labels', () => {
    render(<CompareTable result={mockResult} />);
    expect(screen.getByText('API Kind')).toBeInTheDocument();
    expect(screen.getByText('Version Count')).toBeInTheDocument();
  });

  it('shows similarity score', () => {
    render(<CompareTable result={mockResult} />);
    expect(screen.getByText('30%')).toBeInTheDocument();
  });

  it('renders category sub-headers', () => {
    render(<CompareTable result={mockResult} />);
    // "metadata" and "versions" categories
    expect(screen.getByText('metadata')).toBeInTheDocument();
    expect(screen.getByText('versions')).toBeInTheDocument();
  });
});
