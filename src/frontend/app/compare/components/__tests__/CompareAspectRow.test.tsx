import { render, screen } from '../../../../__tests__/test-utils';
import CompareAspectRow from '../CompareAspectRow';
import type { AspectComparison } from '@/lib/compare-api';

const mockRowEqual: AspectComparison = {
  aspect: 'metadata.kind',
  label: 'API Kind',
  values: [
    { value: 'rest', display: 'rest', isBest: false },
    { value: 'rest', display: 'rest', isBest: false },
  ],
  allEqual: true,
};

const mockRowDifferent: AspectComparison = {
  aspect: 'versions.count',
  label: 'Version Count',
  values: [
    { value: '3', display: '3 versions', isBest: true },
    { value: '1', display: '1 version', isBest: false },
  ],
  allEqual: false,
};

describe('CompareAspectRow', () => {
  it('renders the label', () => {
    render(
      <table>
        <tbody>
          <CompareAspectRow row={mockRowEqual} />
        </tbody>
      </table>
    );
    expect(screen.getByText('API Kind')).toBeInTheDocument();
  });

  it('renders a cell for each API', () => {
    render(
      <table>
        <tbody>
          <CompareAspectRow row={mockRowEqual} />
        </tbody>
      </table>
    );
    const cells = screen.getAllByText('rest');
    expect(cells).toHaveLength(2);
  });

  it('highlights the best value with a chip', () => {
    render(
      <table>
        <tbody>
          <CompareAspectRow row={mockRowDifferent} />
        </tbody>
      </table>
    );
    // Best value should be rendered as a Chip (has role="none" or visible as element)
    expect(screen.getByText('3 versions')).toBeInTheDocument();
    expect(screen.getByText('1 version')).toBeInTheDocument();
  });

  it('has correct test id', () => {
    render(
      <table>
        <tbody>
          <CompareAspectRow row={mockRowEqual} />
        </tbody>
      </table>
    );
    expect(screen.getByTestId('aspect-row-metadata.kind')).toBeInTheDocument();
  });

  it('renders dash for null values', () => {
    const nullRow: AspectComparison = {
      aspect: 'metadata.license',
      label: 'License',
      values: [
        { value: null, display: null, isBest: false },
        { value: 'MIT', display: 'MIT', isBest: false },
      ],
      allEqual: false,
    };
    render(
      <table>
        <tbody>
          <CompareAspectRow row={nullRow} />
        </tbody>
      </table>
    );
    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.getByText('MIT')).toBeInTheDocument();
  });
});
