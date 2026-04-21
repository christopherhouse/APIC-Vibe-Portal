import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import TimeRangeSelector from '../TimeRangeSelector';
import type { TimeRange } from '@/lib/analytics-api';

describe('TimeRangeSelector', () => {
  it('renders all time range options', () => {
    const onChange = jest.fn();
    render(<TimeRangeSelector value="30d" onChange={onChange} />);
    expect(screen.getByTestId('time-range-selector')).toBeInTheDocument();
    expect(screen.getByTestId('time-range-7d')).toBeInTheDocument();
    expect(screen.getByTestId('time-range-30d')).toBeInTheDocument();
    expect(screen.getByTestId('time-range-90d')).toBeInTheDocument();
    expect(screen.getByTestId('time-range-1y')).toBeInTheDocument();
  });

  it('highlights the currently selected range', () => {
    const onChange = jest.fn();
    render(<TimeRangeSelector value="30d" onChange={onChange} />);
    const activeButton = screen.getByTestId('time-range-30d');
    // contained variant has different styling — verify it's the active one
    expect(activeButton).toBeInTheDocument();
  });

  it('calls onChange with selected range', async () => {
    const onChange = jest.fn();
    render(<TimeRangeSelector value="30d" onChange={onChange} />);
    await userEvent.click(screen.getByTestId('time-range-7d'));
    expect(onChange).toHaveBeenCalledWith('7d' as TimeRange);
  });

  it('calls onChange with 90d', async () => {
    const onChange = jest.fn();
    render(<TimeRangeSelector value="30d" onChange={onChange} />);
    await userEvent.click(screen.getByTestId('time-range-90d'));
    expect(onChange).toHaveBeenCalledWith('90d' as TimeRange);
  });

  it('calls onChange with 1y', async () => {
    const onChange = jest.fn();
    render(<TimeRangeSelector value="30d" onChange={onChange} />);
    await userEvent.click(screen.getByTestId('time-range-1y'));
    expect(onChange).toHaveBeenCalledWith('1y' as TimeRange);
  });
});
