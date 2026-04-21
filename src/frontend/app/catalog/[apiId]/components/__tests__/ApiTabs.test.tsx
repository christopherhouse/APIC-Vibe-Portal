import { render, screen, fireEvent } from '../../../../../__tests__/test-utils';
import ApiTabs from '../ApiTabs';

describe('ApiTabs', () => {
  const mockOnChange = jest.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('renders all five tabs', () => {
    render(<ApiTabs value="overview" onChange={mockOnChange} />);
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Versions')).toBeInTheDocument();
    expect(screen.getByText('Specification')).toBeInTheDocument();
    expect(screen.getByText('Deployments')).toBeInTheDocument();
    expect(screen.getByText('Metadata Quality')).toBeInTheDocument();
  });

  it('has correct data-testid', () => {
    render(<ApiTabs value="overview" onChange={mockOnChange} />);
    expect(screen.getByTestId('api-tabs')).toBeInTheDocument();
  });

  it('calls onChange when tab is clicked', () => {
    render(<ApiTabs value="overview" onChange={mockOnChange} />);
    fireEvent.click(screen.getByText('Versions'));
    expect(mockOnChange).toHaveBeenCalledWith('versions');
  });

  it('highlights the selected tab', () => {
    render(<ApiTabs value="specification" onChange={mockOnChange} />);
    const specTab = screen.getByText('Specification');
    expect(specTab.closest('[role="tab"]')).toHaveAttribute('aria-selected', 'true');
  });

  it('calls onChange with each non-active tab value', () => {
    render(<ApiTabs value="overview" onChange={mockOnChange} />);

    // Overview is already selected, so clicking it won't trigger onChange
    fireEvent.click(screen.getByText('Versions'));
    fireEvent.click(screen.getByText('Specification'));
    fireEvent.click(screen.getByText('Deployments'));
    fireEvent.click(screen.getByText('Metadata Quality'));

    expect(mockOnChange).toHaveBeenCalledTimes(4);
    expect(mockOnChange).toHaveBeenCalledWith('versions');
    expect(mockOnChange).toHaveBeenCalledWith('specification');
    expect(mockOnChange).toHaveBeenCalledWith('deployments');
    expect(mockOnChange).toHaveBeenCalledWith('metadata-quality');
  });
});
