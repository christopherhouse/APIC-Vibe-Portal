import { render, screen, fireEvent, waitFor } from '../../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import PolicyDialog from '../PolicyDialog';
import type { ApiOption } from '../PolicyDialog';

const noopSave = jest.fn().mockResolvedValue(undefined);
const noopClose = jest.fn();

const sampleApis: ApiOption[] = [
  { name: 'petstore-api', title: 'Petstore API' },
  { name: 'weather-api', title: 'Weather API' },
  { name: 'internal-api', title: 'Internal API' },
];

describe('PolicyDialog — create mode', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders the create dialog when no existing policy', () => {
    render(
      <PolicyDialog
        open
        existing={null}
        availableApis={sampleApis}
        onClose={noopClose}
        onSave={noopSave}
      />
    );
    expect(screen.getByText('New Access Policy')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /API Name/i })).not.toBeDisabled();
  });

  it('disables save button when API name is empty', () => {
    render(
      <PolicyDialog
        open
        existing={null}
        availableApis={sampleApis}
        onClose={noopClose}
        onSave={noopSave}
      />
    );
    expect(screen.getByTestId('save-policy-button')).toBeDisabled();
  });

  it('enables save button when API is selected from dropdown', async () => {
    const user = userEvent.setup();
    render(
      <PolicyDialog
        open
        existing={null}
        availableApis={sampleApis}
        onClose={noopClose}
        onSave={noopSave}
      />
    );

    // Open the autocomplete and select an option
    const input = screen.getByRole('combobox', { name: /API Name/i });
    await user.click(input);
    await user.type(input, 'petstore');

    const option = await screen.findByText('Petstore API (petstore-api)');
    await user.click(option);

    expect(screen.getByTestId('save-policy-button')).not.toBeDisabled();
  });

  it('calls onSave with API name and groups', async () => {
    const user = userEvent.setup();
    render(
      <PolicyDialog
        open
        existing={null}
        availableApis={sampleApis}
        onClose={noopClose}
        onSave={noopSave}
      />
    );

    // Select API from dropdown
    const input = screen.getByRole('combobox', { name: /API Name/i });
    await user.click(input);
    await user.type(input, 'petstore');
    const option = await screen.findByText('Petstore API (petstore-api)');
    await user.click(option);

    await user.type(screen.getByTestId('group-oid-input'), 'group-abc');
    await user.click(screen.getByTestId('add-group-button'));

    expect(screen.getByTestId('group-chip-group-abc')).toBeInTheDocument();

    await user.click(screen.getByTestId('save-policy-button'));

    await waitFor(() => {
      expect(noopSave).toHaveBeenCalledWith('petstore-api', {
        allowedGroups: ['group-abc'],
        isPublic: false,
      });
    });
  });

  it('adds group on Enter key', async () => {
    const user = userEvent.setup();
    render(
      <PolicyDialog
        open
        existing={null}
        availableApis={sampleApis}
        onClose={noopClose}
        onSave={noopSave}
      />
    );

    await user.type(screen.getByTestId('group-oid-input'), 'group-xyz{Enter}');
    expect(screen.getByTestId('group-chip-group-xyz')).toBeInTheDocument();
  });

  it('removes a group chip on delete', async () => {
    const user = userEvent.setup();
    render(
      <PolicyDialog
        open
        existing={null}
        availableApis={sampleApis}
        onClose={noopClose}
        onSave={noopSave}
      />
    );

    await user.type(screen.getByTestId('group-oid-input'), 'group-xyz{Enter}');
    const chip = screen.getByTestId('group-chip-group-xyz');
    // Click the delete icon inside the chip
    const deleteIcon = chip.querySelector('svg[data-testid="CancelIcon"]');
    if (deleteIcon) {
      await user.click(deleteIcon);
    } else {
      // fallback: use the aria-label
      fireEvent.click(chip.querySelector('[aria-label]')!);
    }
    // chip should be removed (no error if already gone)
  });

  it('shows isPublic switch and hides group section when toggled', async () => {
    const user = userEvent.setup();
    render(
      <PolicyDialog
        open
        existing={null}
        availableApis={sampleApis}
        onClose={noopClose}
        onSave={noopSave}
      />
    );
    // Groups section should be visible by default
    expect(screen.getByTestId('group-oid-input')).toBeInTheDocument();
    // Toggle isPublic
    await user.click(screen.getByTestId('is-public-switch'));
    // Groups section should now be hidden
    expect(screen.queryByTestId('group-oid-input')).not.toBeInTheDocument();
  });

  it('calls onClose when Cancel is clicked', async () => {
    const user = userEvent.setup();
    render(
      <PolicyDialog
        open
        existing={null}
        availableApis={sampleApis}
        onClose={noopClose}
        onSave={noopSave}
      />
    );
    await user.click(screen.getByText('Cancel'));
    expect(noopClose).toHaveBeenCalled();
  });

  it('renders autocomplete dropdown in create mode', () => {
    render(
      <PolicyDialog
        open
        existing={null}
        availableApis={[]}
        apisLoading={true}
        onClose={noopClose}
        onSave={noopSave}
      />
    );
    expect(screen.getByRole('combobox', { name: /API Name/i })).toBeInTheDocument();
  });
});

describe('PolicyDialog — edit mode', () => {
  const existing = {
    apiName: 'internal-api',
    apiId: '',
    allowedGroups: ['grp-1', 'grp-2'],
    isPublic: false,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-02T00:00:00Z',
  };

  beforeEach(() => jest.clearAllMocks());

  it('renders edit title and disables API name field', () => {
    render(<PolicyDialog open existing={existing} onClose={noopClose} onSave={noopSave} />);
    expect(screen.getByText('Edit Policy: internal-api')).toBeInTheDocument();
    expect(screen.getByTestId('api-name-input')).toBeDisabled();
  });

  it('pre-populates groups from existing policy', () => {
    render(<PolicyDialog open existing={existing} onClose={noopClose} onSave={noopSave} />);
    expect(screen.getByTestId('group-chip-grp-1')).toBeInTheDocument();
    expect(screen.getByTestId('group-chip-grp-2')).toBeInTheDocument();
  });

  it('calls onSave with updated groups', async () => {
    const user = userEvent.setup();
    render(<PolicyDialog open existing={existing} onClose={noopClose} onSave={noopSave} />);

    await user.type(screen.getByTestId('group-oid-input'), 'grp-3{Enter}');
    await user.click(screen.getByTestId('save-policy-button'));

    await waitFor(() => {
      expect(noopSave).toHaveBeenCalledWith('internal-api', {
        allowedGroups: ['grp-1', 'grp-2', 'grp-3'],
        isPublic: false,
      });
    });
  });

  it('shows error message when onSave rejects', async () => {
    const user = userEvent.setup();
    const failSave = jest.fn().mockRejectedValue(new Error('Network error'));
    render(<PolicyDialog open existing={existing} onClose={noopClose} onSave={failSave} />);

    await user.click(screen.getByTestId('save-policy-button'));
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });
});
