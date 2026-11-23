import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { InstallButton } from '../install-button';
import { canInstallPWA, promptPWAInstall } from '@/lib/sw';

// The locale the button reads. It starts in the maintained set and moves to
// a frozen catalogue where the button must not appear.
let mockLocale = 'en';

jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => `t:${key}`,
  useLocale: () => mockLocale,
}));

jest.mock('@/lib/sw', () => ({
  canInstallPWA: jest.fn(() => false),
  promptPWAInstall: jest.fn(async () => true),
}));

const mockCanInstall = canInstallPWA as jest.MockedFunction<typeof canInstallPWA>;
const mockPromptInstall = promptPWAInstall as jest.MockedFunction<typeof promptPWAInstall>;

describe('InstallButton', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocale = 'en';
    mockCanInstall.mockReturnValue(false);
    mockPromptInstall.mockResolvedValue(true);
  });

  it('shows nothing when the browser cannot install the app', () => {
    render(<InstallButton />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('appears when the browser offers the install', async () => {
    mockCanInstall.mockReturnValue(true);

    render(<InstallButton />);

    await waitFor(() => expect(screen.getByRole('button')).toBeInTheDocument());
    expect(screen.getByText('t:install')).toBeInTheDocument();
  });

  it('appears when the offer arrives after the page was painted', async () => {
    render(<InstallButton />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();

    window.dispatchEvent(new CustomEvent('pwa-install-available'));

    await waitFor(() => expect(screen.getByRole('button')).toBeInTheDocument());
  });

  it('is offered in Polish too', async () => {
    mockLocale = 'pl';
    mockCanInstall.mockReturnValue(true);

    render(<InstallButton />);

    await waitFor(() => expect(screen.getByRole('button')).toBeInTheDocument());
  });

  it('is not offered in a frozen catalogue', () => {
    mockLocale = 'de';
    mockCanInstall.mockReturnValue(true);

    render(<InstallButton />);

    // The frozen catalogues are not asked about the install at all.
    expect(mockCanInstall).not.toHaveBeenCalled();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('asks the browser to install when it is pressed', async () => {
    mockCanInstall.mockReturnValue(true);
    render(<InstallButton />);

    const button = await screen.findByRole('button');
    fireEvent.click(button);

    await waitFor(() => expect(mockPromptInstall).toHaveBeenCalled());
  });

  it('disappears once the app is installed', async () => {
    mockCanInstall.mockReturnValue(true);
    render(<InstallButton />);

    await screen.findByRole('button');

    window.dispatchEvent(new CustomEvent('pwa-installed'));

    await waitFor(() => expect(screen.queryByRole('button')).not.toBeInTheDocument());
  });
});
