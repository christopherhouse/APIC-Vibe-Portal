import { render, screen } from '../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import PortalTextField from '../ui/PortalTextField';

function renderWithUser(ui: React.ReactElement) {
  return { user: userEvent.setup(), ...render(ui) };
}

describe('PortalTextField', () => {
  it('renders with a label', () => {
    render(<PortalTextField label="Email" />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });

  it('renders with helper text', () => {
    render(<PortalTextField label="Name" helperText="Enter your full name" />);
    expect(screen.getByText(/enter your full name/i)).toBeInTheDocument();
  });

  it('renders in error state with error message', () => {
    render(<PortalTextField label="Email" error helperText="Invalid email" />);
    expect(screen.getByText(/invalid email/i)).toBeInTheDocument();
  });

  it('renders as full width by default', () => {
    render(<PortalTextField label="Search" />);
    const input = screen.getByLabelText(/search/i);
    expect(input.closest('.MuiFormControl-root')).toHaveClass('MuiFormControl-fullWidth');
  });

  it('accepts focus', async () => {
    const { user } = renderWithUser(<PortalTextField label="Name" />);
    const input = screen.getByLabelText(/name/i) as HTMLInputElement;
    await user.click(input);
    expect(input).toHaveFocus();
  });
});
