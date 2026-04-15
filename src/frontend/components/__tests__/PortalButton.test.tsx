import { render, screen } from '../../__tests__/test-utils';
import PortalButton from '../ui/PortalButton';

describe('PortalButton', () => {
  it('renders with text content', () => {
    render(<PortalButton>Click me</PortalButton>);
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  it('renders as contained variant by default when specified', () => {
    render(<PortalButton variant="contained">Save</PortalButton>);
    const button = screen.getByRole('button', { name: /save/i });
    expect(button).toHaveClass('MuiButton-contained');
  });

  it('renders as outlined variant', () => {
    render(<PortalButton variant="outlined">Cancel</PortalButton>);
    const button = screen.getByRole('button', { name: /cancel/i });
    expect(button).toHaveClass('MuiButton-outlined');
  });

  it('renders a loading button when loading prop is provided', () => {
    render(<PortalButton loading>Submitting</PortalButton>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('passes disabled prop correctly', () => {
    render(<PortalButton disabled>Disabled</PortalButton>);
    expect(screen.getByRole('button', { name: /disabled/i })).toBeDisabled();
  });

  it('calls onClick handler', () => {
    const handleClick = jest.fn();
    render(<PortalButton onClick={handleClick}>Click</PortalButton>);
    screen.getByRole('button', { name: /click/i }).click();
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
