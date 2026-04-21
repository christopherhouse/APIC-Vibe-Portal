import React from 'react';
import { render, screen, fireEvent, waitFor } from '../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import SearchBar from '../layout/SearchBar';
import { ApiKind } from '@apic-vibe-portal/shared';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock the autocomplete hook
const mockUseAutocomplete = jest.fn();
jest.mock('@/hooks/use-autocomplete', () => ({
  useAutocomplete: (opts: unknown) => mockUseAutocomplete(opts),
}));

describe('SearchBar', () => {
  beforeEach(() => {
    mockPush.mockClear();
    mockUseAutocomplete.mockReturnValue({ suggestions: [], isLoading: false, error: null });
  });

  it('renders a search input', () => {
    render(<SearchBar />);
    expect(screen.getByRole('combobox', { name: /search/i })).toBeInTheDocument();
  });

  it('navigates to search results on Enter', async () => {
    const user = userEvent.setup();
    render(<SearchBar />);
    const input = screen.getByRole('combobox', { name: /search/i });
    await user.type(input, 'petstore{Enter}');
    expect(mockPush).toHaveBeenCalledWith('/search?q=petstore');
  });

  it('navigates to search when Enter is pressed without dropdown showing', () => {
    render(<SearchBar />);
    const input = screen.getByRole('combobox', { name: /search/i });

    // Type a value to set inputValue
    fireEvent.change(input, { target: { value: 'test query' } });

    // Press Enter without dropdown showing
    fireEvent.keyDown(input, { key: 'Enter' });

    // Verify navigation occurred
    expect(mockPush).toHaveBeenCalledWith('/search?q=test%20query');
  });

  it('shows clear button when input has value', async () => {
    const user = userEvent.setup();
    render(<SearchBar />);
    const input = screen.getByRole('combobox', { name: /search/i });
    await user.type(input, 'pet');
    expect(screen.getByRole('button', { name: /clear search/i })).toBeInTheDocument();
  });

  it('clears input when clear button is clicked', async () => {
    const user = userEvent.setup();
    render(<SearchBar />);
    const input = screen.getByRole('combobox', { name: /search/i });
    await user.type(input, 'pet');
    await user.click(screen.getByRole('button', { name: /clear search/i }));
    expect(input).toHaveValue('');
  });

  it('shows autocomplete dropdown when suggestions are available', async () => {
    mockUseAutocomplete.mockReturnValue({
      suggestions: [
        {
          apiId: 'api-1',
          title: 'Petstore API',
          description: 'Manages pets',
          kind: ApiKind.REST,
        },
      ],
      isLoading: false,
      error: null,
    });

    const user = userEvent.setup();
    render(<SearchBar />);
    const input = screen.getByRole('combobox', { name: /search/i });
    await user.type(input, 'pet');

    await waitFor(() => {
      expect(screen.getByTestId('suggestion-api-1')).toBeInTheDocument();
    });
  });

  it('navigates to catalog detail when a suggestion is clicked', async () => {
    mockUseAutocomplete.mockReturnValue({
      suggestions: [
        {
          apiId: 'api-2',
          title: 'Payment API',
          description: 'Payment processing',
          kind: ApiKind.REST,
        },
      ],
      isLoading: false,
      error: null,
    });

    const user = userEvent.setup();
    render(<SearchBar />);
    await user.type(screen.getByRole('combobox', { name: /search/i }), 'pay');

    await waitFor(() => expect(screen.getByTestId('suggestion-api-2')).toBeInTheDocument());

    fireEvent.mouseDown(screen.getByTestId('suggestion-api-2'));
    expect(mockPush).toHaveBeenCalledWith('/catalog/api-2');
  });

  it('navigates through suggestions with arrow keys', async () => {
    mockUseAutocomplete.mockReturnValue({
      suggestions: [
        { apiId: 'api-1', title: 'First API', description: '', kind: ApiKind.REST },
        { apiId: 'api-2', title: 'Second API', description: '', kind: ApiKind.REST },
      ],
      isLoading: false,
      error: null,
    });

    const user = userEvent.setup();
    render(<SearchBar />);
    const input = screen.getByRole('combobox', { name: /search/i });
    await user.type(input, 'api');

    // Navigate down to first item and press Enter
    await user.keyboard('{ArrowDown}{Enter}');
    expect(mockPush).toHaveBeenCalledWith('/catalog/api-1');
  });
});
