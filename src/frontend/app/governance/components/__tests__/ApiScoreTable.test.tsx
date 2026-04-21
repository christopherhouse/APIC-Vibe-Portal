import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import ApiScoreTable from '../ApiScoreTable';
import type { ApiGovernanceScore } from '@/lib/governance-api';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockScores: ApiGovernanceScore[] = [
  {
    apiId: 'payments-api',
    apiName: 'Payments API',
    score: 92.0,
    category: 'Excellent',
    criticalFailures: 0,
    lastChecked: '2026-04-20T18:00:00Z',
  },
  {
    apiId: 'users-api',
    apiName: 'Users API',
    score: 64.0,
    category: 'Needs Improvement',
    criticalFailures: 1,
    lastChecked: '2026-04-20T18:00:00Z',
  },
  {
    apiId: 'orders-api',
    apiName: 'Orders API',
    score: 82.0,
    category: 'Good',
    criticalFailures: 0,
    lastChecked: '2026-04-20T18:00:00Z',
  },
];

describe('ApiScoreTable', () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it('renders empty state when no scores', () => {
    render(<ApiScoreTable scores={[]} />);
    expect(screen.getByTestId('api-score-table-empty')).toBeInTheDocument();
    expect(screen.getByText('No API governance scores available')).toBeInTheDocument();
  });

  it('renders table with scores', () => {
    render(<ApiScoreTable scores={mockScores} />);
    expect(screen.getByTestId('api-score-table')).toBeInTheDocument();
  });

  it('renders a row for each score', () => {
    render(<ApiScoreTable scores={mockScores} />);
    expect(screen.getByTestId('api-score-row-payments-api')).toBeInTheDocument();
    expect(screen.getByTestId('api-score-row-users-api')).toBeInTheDocument();
    expect(screen.getByTestId('api-score-row-orders-api')).toBeInTheDocument();
  });

  it('renders filter input', () => {
    render(<ApiScoreTable scores={mockScores} />);
    expect(screen.getByTestId('api-score-table-filter')).toBeInTheDocument();
  });

  it('filters rows by API name', async () => {
    const user = userEvent.setup();
    render(<ApiScoreTable scores={mockScores} />);

    const filterInput = screen.getByTestId('api-score-table-filter') as HTMLInputElement;
    await user.type(filterInput, 'payments');

    expect(screen.getByTestId('api-score-row-payments-api')).toBeInTheDocument();
    expect(screen.queryByTestId('api-score-row-users-api')).not.toBeInTheDocument();
  });

  it('shows no-match message when filter has no results', async () => {
    const user = userEvent.setup();
    render(<ApiScoreTable scores={mockScores} />);

    const filterInput = screen.getByTestId('api-score-table-filter') as HTMLInputElement;
    await user.type(filterInput, 'zzznomatch');

    expect(screen.getByText('No APIs match your filter')).toBeInTheDocument();
  });

  it('navigates to compliance detail on row click', async () => {
    const user = userEvent.setup();
    render(<ApiScoreTable scores={mockScores} />);

    await user.click(screen.getByTestId('api-score-row-payments-api'));
    expect(mockPush).toHaveBeenCalledWith('/governance/payments-api');
  });

  it('sorts by score descending by default (highest score first)', () => {
    render(<ApiScoreTable scores={mockScores} />);
    const rows = screen.getAllByRole('row').slice(1); // skip header row
    const firstRowText = rows[0].textContent ?? '';
    // Default sort is score desc — Payments API (92.0) should be first
    expect(firstRowText).toContain('Payments API');
  });

  it('displays score values', () => {
    render(<ApiScoreTable scores={mockScores} />);
    expect(screen.getByText('92.0')).toBeInTheDocument();
    expect(screen.getByText('64.0')).toBeInTheDocument();
    expect(screen.getByText('82.0')).toBeInTheDocument();
  });

  it('displays category chips', () => {
    render(<ApiScoreTable scores={mockScores} />);
    expect(screen.getByText('Excellent')).toBeInTheDocument();
    expect(screen.getByText('Needs Improvement')).toBeInTheDocument();
    expect(screen.getByText('Good')).toBeInTheDocument();
  });

  it('sorts by API name when name header is clicked twice (asc)', async () => {
    const user = userEvent.setup();
    render(<ApiScoreTable scores={mockScores} />);

    // Click API Name header once → sorts desc (Z to A)
    await user.click(screen.getByText('API Name'));
    // Click again → sorts asc (A to Z)
    await user.click(screen.getByText('API Name'));
    const rows = screen.getAllByRole('row').slice(1);
    const firstRowText = rows[0].textContent ?? '';
    // After ascending name sort, 'Orders API' (O) comes before 'Payments' and 'Users'
    expect(firstRowText).toContain('Orders API');
  });
});
