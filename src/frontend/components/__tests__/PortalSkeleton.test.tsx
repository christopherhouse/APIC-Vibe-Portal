import { render } from '../../__tests__/test-utils';
import PortalSkeleton from '../ui/PortalSkeleton';

describe('PortalSkeleton', () => {
  it('renders a single skeleton by default', () => {
    const { container } = render(<PortalSkeleton />);
    const skeletons = container.querySelectorAll('.MuiSkeleton-root');
    expect(skeletons).toHaveLength(1);
  });

  it('renders multiple skeleton lines', () => {
    const { container } = render(<PortalSkeleton lines={3} />);
    const skeletons = container.querySelectorAll('.MuiSkeleton-root');
    expect(skeletons).toHaveLength(3);
  });

  it('renders with text variant by default', () => {
    const { container } = render(<PortalSkeleton />);
    expect(container.querySelector('.MuiSkeleton-text')).toBeInTheDocument();
  });

  it('renders with rectangular variant when specified', () => {
    const { container } = render(<PortalSkeleton variant="rectangular" height={120} />);
    expect(container.querySelector('.MuiSkeleton-rectangular')).toBeInTheDocument();
  });

  it('renders with circular variant when specified', () => {
    const { container } = render(<PortalSkeleton variant="circular" width={40} height={40} />);
    expect(container.querySelector('.MuiSkeleton-circular')).toBeInTheDocument();
  });
});
