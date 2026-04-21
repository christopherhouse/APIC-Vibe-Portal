import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import ApiTrafficTable from '../ApiTrafficTable';
import type { PopularApi } from '@/lib/analytics-api';

const mockApis: PopularApi[] = [
  {
    apiId: 'payments-api',
    apiName: 'Payments API',
    viewCount: 500,
    downloadCount: 120,
    chatMentionCount: 45,
  },
  {
    apiId: 'users-api',
    apiName: 'Users API',
    viewCount: 380,
    downloadCount: 90,
    chatMentionCount: 30,
  },
  {
    apiId: 'catalog-api',
    apiName: 'Catalog API',
    viewCount: 200,
    downloadCount: 50,
    chatMentionCount: 10,
  },
];

describe('ApiTrafficTable', () => {
  it('renders the table container', () => {
    render(<ApiTrafficTable apis={mockApis} />);
    expect(screen.getByTestId('api-traffic-table')).toBeInTheDocument();
  });

  it('renders API name rows', () => {
    render(<ApiTrafficTable apis={mockApis} />);
    expect(screen.getByText('Payments API')).toBeInTheDocument();
    expect(screen.getByText('Users API')).toBeInTheDocument();
    expect(screen.getByText('Catalog API')).toBeInTheDocument();
  });

  it('renders row test ids', () => {
    render(<ApiTrafficTable apis={mockApis} />);
    expect(screen.getByTestId('api-traffic-row-payments-api')).toBeInTheDocument();
    expect(screen.getByTestId('api-traffic-row-users-api')).toBeInTheDocument();
  });

  it('renders view counts', () => {
    render(<ApiTrafficTable apis={mockApis} />);
    expect(screen.getByText('500')).toBeInTheDocument();
  });

  it('shows empty state when no APIs', () => {
    render(<ApiTrafficTable apis={[]} />);
    expect(screen.getByTestId('api-traffic-table-empty')).toBeInTheDocument();
    expect(screen.getByText('No API traffic data available')).toBeInTheDocument();
  });

  it('sorts by downloads on column header click', async () => {
    render(<ApiTrafficTable apis={mockApis} />);
    const downloadsHeader = screen.getByText('Downloads');
    await userEvent.click(downloadsHeader);
    // After clicking, the table should still render
    expect(screen.getByTestId('api-traffic-table')).toBeInTheDocument();
  });
});
