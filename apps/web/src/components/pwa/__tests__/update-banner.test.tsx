import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { UpdateBanner } from '../update-banner';
import { applyUpdate } from '@/lib/sw';

jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => `t:${key}`,
}));

jest.mock('@/lib/sw', () => ({
  applyUpdate: jest.fn(async () => undefined),
}));

const mockApplyUpdate = applyUpdate as jest.MockedFunction<typeof applyUpdate>;

describe('UpdateBanner', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows nothing while there is no new version', () => {
    render(<UpdateBanner />);

    expect(screen.queryByText('t:update.title')).not.toBeInTheDocument();
  });

  it('announces the new version when it arrives', async () => {
    render(<UpdateBanner />);

    window.dispatchEvent(new CustomEvent('sw-update-available'));

    await waitFor(() => expect(screen.getByText('t:update.title')).toBeInTheDocument());
    expect(screen.getByText('t:update.reload')).toBeInTheDocument();
  });

  it('applies the version only when the visitor accepts it', async () => {
    render(<UpdateBanner />);

    window.dispatchEvent(new CustomEvent('sw-update-available'));

    const reload = await screen.findByText('t:update.reload');
    expect(mockApplyUpdate).not.toHaveBeenCalled();

    fireEvent.click(reload);

    await waitFor(() => expect(mockApplyUpdate).toHaveBeenCalledTimes(1));
  });

  it('can be dismissed without applying it', async () => {
    render(<UpdateBanner />);

    window.dispatchEvent(new CustomEvent('sw-update-available'));

    const dismiss = await screen.findByLabelText('t:dismissUpdate');
    fireEvent.click(dismiss);

    await waitFor(() => expect(screen.queryByText('t:update.title')).not.toBeInTheDocument());
    expect(mockApplyUpdate).not.toHaveBeenCalled();
  });
});
