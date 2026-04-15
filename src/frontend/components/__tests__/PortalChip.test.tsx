import { render, screen } from '../../__tests__/test-utils';
import PortalChip from '../ui/PortalChip';

describe('PortalChip', () => {
  it('renders with a label', () => {
    render(<PortalChip label="Active" />);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('renders with status=active (green/success)', () => {
    render(<PortalChip label="Active" status="active" />);
    const chip = screen.getByText('Active').closest('.MuiChip-root');
    expect(chip).toHaveClass('MuiChip-colorSuccess');
  });

  it('renders with status=deprecated (warning)', () => {
    render(<PortalChip label="Deprecated" status="deprecated" />);
    const chip = screen.getByText('Deprecated').closest('.MuiChip-root');
    expect(chip).toHaveClass('MuiChip-colorWarning');
  });

  it('renders with status=preview (info)', () => {
    render(<PortalChip label="Preview" status="preview" />);
    const chip = screen.getByText('Preview').closest('.MuiChip-root');
    expect(chip).toHaveClass('MuiChip-colorInfo');
  });

  it('renders with status=retired (error)', () => {
    render(<PortalChip label="Retired" status="retired" />);
    const chip = screen.getByText('Retired').closest('.MuiChip-root');
    expect(chip).toHaveClass('MuiChip-colorError');
  });

  it('renders with custom color when no status', () => {
    render(<PortalChip label="Custom" color="primary" />);
    const chip = screen.getByText('Custom').closest('.MuiChip-root');
    expect(chip).toHaveClass('MuiChip-colorPrimary');
  });
});
