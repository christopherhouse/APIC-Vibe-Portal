import { render, screen, fireEvent } from '../../../../../__tests__/test-utils';
import ApiSpecViewer from '../ApiSpecViewer';

describe('ApiSpecViewer', () => {
  it('renders loading skeleton when isLoading', () => {
    render(<ApiSpecViewer specContent={null} isLoading />);
    expect(screen.getByTestId('spec-viewer-skeleton')).toBeInTheDocument();
  });

  it('renders error state with message', () => {
    render(<ApiSpecViewer specContent={null} error="Failed to load" />);
    expect(screen.getByTestId('spec-viewer-error')).toBeInTheDocument();
    expect(screen.getByText('Failed to load')).toBeInTheDocument();
  });

  it('renders retry button when onRetry is provided', () => {
    const mockRetry = jest.fn();
    render(<ApiSpecViewer specContent={null} error="Failed" onRetry={mockRetry} />);
    fireEvent.click(screen.getByText('Retry'));
    expect(mockRetry).toHaveBeenCalled();
  });

  it('renders empty state when no spec', () => {
    render(<ApiSpecViewer specContent={null} />);
    expect(screen.getByTestId('spec-viewer-empty')).toBeInTheDocument();
    expect(screen.getByText(/No specification available/)).toBeInTheDocument();
  });

  it('renders JSON spec content formatted', () => {
    const spec = JSON.stringify({ openapi: '3.0.0', info: { title: 'Test' } });
    render(<ApiSpecViewer specContent={spec} />);
    expect(screen.getByTestId('spec-viewer')).toBeInTheDocument();
    expect(screen.getByText(/"openapi": "3.0.0"/)).toBeInTheDocument();
  });

  it('renders non-JSON (YAML) spec content as-is', () => {
    const yamlSpec = 'openapi: 3.0.0\ninfo:\n  title: Test';
    render(<ApiSpecViewer specContent={yamlSpec} />);
    expect(screen.getByTestId('spec-viewer')).toBeInTheDocument();
    expect(screen.getByText(/openapi: 3.0.0/)).toBeInTheDocument();
  });
});
