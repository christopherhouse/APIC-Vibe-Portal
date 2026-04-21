import { render, screen, fireEvent, waitFor } from '../../../../__tests__/test-utils';
import ExportButton from '../ExportButton';

// Mock URL.createObjectURL and related APIs
beforeAll(() => {
  global.URL.createObjectURL = jest.fn().mockReturnValue('blob:mock-url');
  global.URL.revokeObjectURL = jest.fn();
});

describe('ExportButton', () => {
  it('renders the export button', () => {
    render(<ExportButton getData={() => []} />);
    expect(screen.getByTestId('export-csv-button')).toBeInTheDocument();
  });

  it('shows the default label', () => {
    render(<ExportButton getData={() => []} />);
    expect(screen.getByText('Export CSV')).toBeInTheDocument();
  });

  it('shows a custom label', () => {
    render(<ExportButton getData={() => []} label="Download Data" />);
    expect(screen.getByText('Download Data')).toBeInTheDocument();
  });

  it('triggers getData on click', async () => {
    const getData = jest.fn().mockResolvedValue([{ name: 'Test API', views: 100 }]);
    render(<ExportButton getData={getData} filename="test.csv" />);

    fireEvent.click(screen.getByTestId('export-csv-button'));

    await waitFor(() => expect(getData).toHaveBeenCalled());
  });

  it('is not disabled initially', () => {
    render(<ExportButton getData={() => []} />);
    expect(screen.getByTestId('export-csv-button')).not.toBeDisabled();
  });
});
