import { render, screen } from '../../__tests__/test-utils';
import PortalCard from '../ui/PortalCard';

describe('PortalCard', () => {
  it('renders children content', () => {
    render(<PortalCard>Card content</PortalCard>);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('renders title and subheader', () => {
    render(<PortalCard title="API Name" subheader="v2.0">Body</PortalCard>);
    expect(screen.getByText('API Name')).toBeInTheDocument();
    expect(screen.getByText('v2.0')).toBeInTheDocument();
  });

  it('renders without header when no title/subheader', () => {
    const { container } = render(<PortalCard>Just content</PortalCard>);
    expect(container.querySelector('.MuiCardHeader-root')).not.toBeInTheDocument();
  });

  it('renders actions when provided', () => {
    render(
      <PortalCard title="Test" actions={<button>Action</button>}>
        Content
      </PortalCard>
    );
    expect(screen.getByRole('button', { name: /action/i })).toBeInTheDocument();
  });
});
