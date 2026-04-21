import { render, screen } from '../../../../__tests__/test-utils';
import CompletenessLeaderboard from '../CompletenessLeaderboard';
import type { LeaderboardData } from '@/lib/metadata-api';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

const mockLeaderboard: LeaderboardData = {
  top: [
    { apiId: 'api-1', apiName: 'Best API', score: 95, grade: 'A' },
    { apiId: 'api-2', apiName: 'Good API', score: 80, grade: 'B' },
  ],
  bottom: [
    { apiId: 'api-9', apiName: 'Needs Work API', score: 35, grade: 'F' },
    { apiId: 'api-10', apiName: 'Worst API', score: 20, grade: 'F' },
  ],
};

describe('CompletenessLeaderboard', () => {
  it('renders the leaderboard', () => {
    render(<CompletenessLeaderboard leaderboard={mockLeaderboard} />);
    expect(screen.getByTestId('completeness-leaderboard')).toBeInTheDocument();
  });

  it('renders top and bottom tables', () => {
    render(<CompletenessLeaderboard leaderboard={mockLeaderboard} />);
    expect(screen.getByTestId('leaderboard-top')).toBeInTheDocument();
    expect(screen.getByTestId('leaderboard-bottom')).toBeInTheDocument();
  });

  it('displays top API names', () => {
    render(<CompletenessLeaderboard leaderboard={mockLeaderboard} />);
    expect(screen.getByText('Best API')).toBeInTheDocument();
    expect(screen.getByText('Good API')).toBeInTheDocument();
  });

  it('displays bottom API names', () => {
    render(<CompletenessLeaderboard leaderboard={mockLeaderboard} />);
    expect(screen.getByText('Needs Work API')).toBeInTheDocument();
    expect(screen.getByText('Worst API')).toBeInTheDocument();
  });

  it('displays leaderboard row test IDs', () => {
    render(<CompletenessLeaderboard leaderboard={mockLeaderboard} />);
    expect(screen.getByTestId('leaderboard-row-api-1')).toBeInTheDocument();
    expect(screen.getByTestId('leaderboard-row-api-9')).toBeInTheDocument();
  });

  it('handles empty leaderboard', () => {
    render(<CompletenessLeaderboard leaderboard={{ top: [], bottom: [] }} />);
    expect(screen.getByTestId('completeness-leaderboard')).toBeInTheDocument();
    expect(screen.getAllByText('No data available')).toHaveLength(2);
  });
});
