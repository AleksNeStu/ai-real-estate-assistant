import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import SettingsPage from '../page';
import { getModelsCatalog, testModelRuntime, ApiError } from '@/lib/api';

// Mock API
jest.mock('@/lib/api', () => ({
  ...jest.requireActual('@/lib/api'),
  getNotificationSettings: jest.fn(),
  updateNotificationSettings: jest.fn(),
  getModelsCatalog: jest.fn(),
  testModelRuntime: jest.fn(),
  getModelPreferences: jest.fn(),
  updateModelPreferences: jest.fn(),
  getTaskModelPreferences: jest.fn(),
  createTaskModelPreference: jest.fn(),
  updateTaskModelPreference: jest.fn(),
  deleteTaskModelPreference: jest.fn(),
  getSystemModelDefaults: jest.fn(),
}));

// The gate belongs to another lane and is mocked here.
jest.mock('@/components/shell/gate', () => ({
  AccountGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock child component to simplify integration test
jest.mock('@/components/settings/notification-settings', () => ({
  NotificationSettings: () => (
    <div data-testid="notification-settings">Notification Settings Component</div>
  ),
}));

jest.mock('@/components/settings/profile-settings', () => ({
  ProfileSettings: () => <div data-testid="profile-settings">Profile Settings Component</div>,
}));

jest.mock('@/components/settings/privacy-settings', () => ({
  PrivacySettings: () => <div data-testid="privacy-settings">Privacy Settings Component</div>,
}));

const openaiCatalog = [
  {
    name: 'openai',
    display_name: 'OpenAI',
    is_local: false,
    requires_api_key: true,
    models: [
      {
        id: 'gpt-4o',
        display_name: 'GPT-4o',
        provider_name: 'OpenAI',
        context_window: 128000,
        pricing: { input_price_per_1m: 2.5, output_price_per_1m: 10, currency: 'USD' },
        capabilities: ['streaming', 'vision'],
        description: null,
        recommended_for: [],
      },
    ],
  },
];

describe('SettingsPage', () => {
  const mockGetModelsCatalog = getModelsCatalog as jest.Mock;
  const mockTestModelRuntime = testModelRuntime as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    mockGetModelsCatalog.mockImplementation(() => new Promise(() => {}));
  });

  it('renders page title and description', () => {
    render(<SettingsPage />);
    expect(screen.getByText('Settings')).toBeInTheDocument();
    expect(
      screen.getByText('Manage your account settings and notification preferences.')
    ).toBeInTheDocument();
  });

  it('shows the five tabs of the prototype', () => {
    render(<SettingsPage />);
    expect(screen.getByRole('tab', { name: 'Identity' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Models' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Notifications' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Profile' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Privacy' })).toBeInTheDocument();
  });

  it('opens one tab at a time', () => {
    render(<SettingsPage />);
    expect(screen.getByRole('tab', { name: 'Models' })).toHaveAttribute(
      'aria-selected',
      'true'
    );

    fireEvent.click(screen.getByRole('tab', { name: 'Notifications' }));
    expect(screen.getByRole('tab', { name: 'Notifications' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
    expect(screen.getByTestId('notification-settings')).toBeInTheDocument();
  });

  it('renders the profile and the privacy panel on their tabs', () => {
    render(<SettingsPage />);

    fireEvent.click(screen.getByRole('tab', { name: 'Profile' }));
    expect(screen.getByTestId('profile-settings')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Privacy' }));
    expect(screen.getByTestId('privacy-settings')).toBeInTheDocument();
  });

  it('renders the models tab with the catalogue, its context and its prices', async () => {
    mockGetModelsCatalog.mockResolvedValueOnce(openaiCatalog);

    render(<SettingsPage />);
    fireEvent.click(screen.getByRole('tab', { name: 'Models' }));

    expect(screen.getByRole('button', { name: 'Refresh catalog' })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText('OpenAI').length).toBeGreaterThan(0);
    });

    expect(screen.getAllByText('gpt-4o').length).toBeGreaterThan(0);
    expect(screen.getByText('128k')).toBeInTheDocument();
    expect(screen.getByText('USD 2.50')).toBeInTheDocument();
    expect(screen.getByText('USD 10.00')).toBeInTheDocument();
  });

  it('runs the runtime test and reports the measured round trip', async () => {
    mockGetModelsCatalog.mockResolvedValueOnce(openaiCatalog);
    mockTestModelRuntime.mockResolvedValueOnce({
      provider: 'openai',
      is_local: false,
      runtime_available: true,
      available_models: [],
      runtime_error: null,
    });

    render(<SettingsPage />);
    fireEvent.click(screen.getByRole('tab', { name: 'Models' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Test' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Test' }));

    await waitFor(() => {
      expect(mockTestModelRuntime).toHaveBeenCalledWith('openai');
      expect(screen.getByText(/ok · \d+ ms/)).toBeInTheDocument();
    });
  });

  it('says that a key is missing when the provider has none', async () => {
    mockGetModelsCatalog.mockResolvedValueOnce(openaiCatalog);
    mockTestModelRuntime.mockResolvedValueOnce({
      provider: 'openai',
      is_local: false,
      runtime_available: false,
      available_models: [],
      runtime_error: 'API key not provided',
    });

    render(<SettingsPage />);
    fireEvent.click(screen.getByRole('tab', { name: 'Models' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Test' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Test' }));

    await waitFor(() => {
      expect(screen.getByText('no key set')).toBeInTheDocument();
    });
  });

  it('shows retry on catalog load failure', async () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockGetModelsCatalog.mockRejectedValueOnce(
      new ApiError('Failed to load model catalog. Please try again.', 500)
    );

    render(<SettingsPage />);
    fireEvent.click(screen.getByRole('tab', { name: 'Models' }));

    await waitFor(() => {
      expect(
        screen.getByText('Failed to load model catalog. Please try again.')
      ).toBeInTheDocument();
    });
    expect(errorSpy).not.toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it('says that the catalogue is empty when it carries no provider', async () => {
    mockGetModelsCatalog.mockResolvedValueOnce([]);

    render(<SettingsPage />);
    fireEvent.click(screen.getByRole('tab', { name: 'Models' }));

    await waitFor(() => {
      expect(screen.getByText('No models available.')).toBeInTheDocument();
    });
  });
});
