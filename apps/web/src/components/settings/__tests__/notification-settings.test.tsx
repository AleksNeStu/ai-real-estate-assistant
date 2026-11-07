import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { NotificationSettings } from '../notification-settings';
import { getNotificationSettings, updateNotificationSettings } from '@/lib/api';
import { NotificationSettings as SettingsType } from '@/lib/types';

// Mock API
jest.mock('@/lib/api', () => ({
  getNotificationSettings: jest.fn(),
  updateNotificationSettings: jest.fn(),
  sendNotificationPreview: jest.fn(),
}));

// The global next-intl mock returns the raw translation key. The component
// renders user-visible English, so the mock resolves the real `en` messages
// (including `{placeholder}` interpolation).
jest.mock('next-intl', () => {
  const messages = jest.requireActual<Record<string, unknown>>('../../../../messages/en.json');
  const resolve = (path: string): unknown =>
    path.split('.').reduce<unknown>(
      (acc, part) =>
        acc && typeof acc === 'object' ? (acc as Record<string, unknown>)[part] : undefined,
      messages
    );
  const interpolate = (template: string, params?: Record<string, unknown>) =>
    params
      ? template.replace(/\{(\w+)\}/g, (match, name) =>
          name in params ? String(params[name]) : match
        )
      : template;
  return {
    useTranslations:
      (namespace?: string) =>
      (key: string, params?: Record<string, unknown>) => {
        const value = resolve(namespace ? `${namespace}.${key}` : key);
        return typeof value === 'string' ? interpolate(value, params) : key;
      },
    useLocale: () => 'en',
    useMessages: () => messages,
    NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => children,
  };
});

const mockSettings: SettingsType = {
  price_alerts_enabled: true,
  new_listings_enabled: true,
  saved_search_enabled: false,
  market_updates_enabled: false,
  alert_frequency: 'weekly',
  email_enabled: true,
  push_enabled: false,
  in_app_enabled: true,
  quiet_hours_start: '22:00',
  quiet_hours_end: '07:00',
  price_drop_threshold: 5,
  daily_digest_time: '08:00',
  weekly_digest_day: 'monday',
  expert_mode: false,
  marketing_emails: false,
  unsubscribe_token: null,
  unsubscribed_at: null,
  unsubscribed_types: null,
};

// The payload the component sends on save (read-only unsubscribe fields excluded).
const expectedUpdate = {
  price_alerts_enabled: true,
  new_listings_enabled: true,
  saved_search_enabled: false,
  market_updates_enabled: false,
  alert_frequency: 'weekly' as const,
  email_enabled: true,
  push_enabled: false,
  in_app_enabled: true,
  quiet_hours_start: '22:00',
  quiet_hours_end: '07:00',
  price_drop_threshold: 5,
  daily_digest_time: '08:00',
  weekly_digest_day: 'monday',
  expert_mode: false,
  marketing_emails: false,
};

describe('NotificationSettings Component', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it('prompts for an email when no user email is set', () => {
    render(<NotificationSettings userEmail={null} />);
    expect(
      screen.getByText('Set an email in Identity settings above to access this section.')
    ).toBeInTheDocument();
  });

  it('renders loading state initially', () => {
    (getNotificationSettings as jest.Mock).mockImplementation(() => new Promise(() => {}));
    render(<NotificationSettings userEmail="user@example.com" />);
    expect(screen.getByText('Loading settings...')).toBeInTheDocument();
  });

  it('renders settings form after loading', async () => {
    (getNotificationSettings as jest.Mock).mockResolvedValue(mockSettings);
    render(<NotificationSettings userEmail="user@example.com" />);

    await waitFor(() => {
      expect(screen.getByText('Email Digests')).toBeInTheDocument();
    });

    // Check checkboxes
    const priceAlertsCheckbox = screen.getByLabelText(/Price Alerts/i);
    expect(priceAlertsCheckbox).toBeChecked();

    const newListingsCheckbox = screen.getByLabelText(/New Listings/i);
    expect(newListingsCheckbox).toBeChecked();

    const savedSearchCheckbox = screen.getByLabelText(/Saved Search Updates/i);
    expect(savedSearchCheckbox).not.toBeChecked();

    const expertCheckbox = screen.getByLabelText(/Expert Mode/i);
    expect(expertCheckbox).not.toBeChecked();

    // Check select
    const frequencySelect = screen.getByLabelText(/Alert Frequency/i) as HTMLSelectElement;
    expect(frequencySelect.value).toBe('weekly');
  });

  it('handles error when loading fails', async () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    (getNotificationSettings as jest.Mock).mockRejectedValue(new Error('API Error'));
    render(<NotificationSettings userEmail="user@example.com" />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load settings. Please try again.')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
    expect(errorSpy).not.toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it('toggles checkboxes', async () => {
    (getNotificationSettings as jest.Mock).mockResolvedValue(mockSettings);
    render(<NotificationSettings userEmail="user@example.com" />);

    await waitFor(() => {
      expect(screen.getByText('Email Digests')).toBeInTheDocument();
    });

    const expertCheckbox = screen.getByLabelText(/Expert Mode/i);
    fireEvent.click(expertCheckbox);
    expect(expertCheckbox).toBeChecked();
  });

  it('changes frequency', async () => {
    (getNotificationSettings as jest.Mock).mockResolvedValue(mockSettings);
    render(<NotificationSettings userEmail="user@example.com" />);

    await waitFor(() => {
      expect(screen.getByText('Email Digests')).toBeInTheDocument();
    });

    const frequencySelect = screen.getByLabelText(/Alert Frequency/i);
    fireEvent.change(frequencySelect, { target: { value: 'daily' } });
    expect((frequencySelect as HTMLSelectElement).value).toBe('daily');
  });

  it('saves settings successfully', async () => {
    (getNotificationSettings as jest.Mock).mockResolvedValue(mockSettings);
    (updateNotificationSettings as jest.Mock).mockImplementation(async (s) => ({
      ...mockSettings,
      ...s,
    }));

    render(<NotificationSettings userEmail="user@example.com" />);

    await waitFor(() => {
      expect(screen.getByText('Email Digests')).toBeInTheDocument();
    });

    // Change something
    const expertCheckbox = screen.getByLabelText(/Expert Mode/i);
    fireEvent.click(expertCheckbox);

    // Click Save
    const saveButton = screen.getByRole('button', { name: /Save Preferences/i });
    fireEvent.click(saveButton);

    expect(saveButton).toBeDisabled();
    expect(screen.getByText('Saving...')).toBeInTheDocument();

    await waitFor(() => {
      expect(updateNotificationSettings).toHaveBeenCalledWith({
        ...expectedUpdate,
        expert_mode: true,
      });
      expect(screen.getByText('Settings saved successfully.')).toBeInTheDocument();
    });
  });

  it('handles save error', async () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    (getNotificationSettings as jest.Mock).mockResolvedValue(mockSettings);
    (updateNotificationSettings as jest.Mock).mockRejectedValue(new Error('Save failed'));

    render(<NotificationSettings userEmail="user@example.com" />);

    await waitFor(() => {
      expect(screen.getByText('Email Digests')).toBeInTheDocument();
    });

    const saveButton = screen.getByRole('button', { name: /Save Preferences/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('Failed to save settings.')).toBeInTheDocument();
    });
    expect(errorSpy).not.toHaveBeenCalled();
    errorSpy.mockRestore();
  });
});
