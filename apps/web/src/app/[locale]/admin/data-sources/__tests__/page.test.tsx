import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import DataSourcesPage from '../page';
import {
  createDataSource,
  fetchFromPortal,
  getExcelSheets,
  ingestData,
  listPortals,
  listDataSources,
} from '@/lib/api';

/**
 * The sources the deployment has, as the mock remembers them. A source the
 * panel creates lands here, so the ledger reads the new row.
 */
const mockCreatedSources: Array<Record<string, unknown>> = [];

jest.mock('@/lib/api', () => {
  class MockApiError extends Error {
    constructor(
      message: string,
      public status: number,
      public request_id?: string
    ) {
      super(message);
      this.name = 'ApiError';
    }
  }
  return {
    listDataSources: jest.fn(async () => ({
      sources: mockCreatedSources,
      total: mockCreatedSources.length,
      page: 1,
      page_size: 20,
    })),
    createDataSource: jest.fn(async (data: Record<string, unknown>) => {
      const source = {
        id: `source-${mockCreatedSources.length + 1}`,
        name: data.name,
        source_type: data.source_type,
        config: data.config,
        status: 'pending',
        total_records: 0,
        health_score: 100,
        consecutive_failures: 0,
        auto_sync_enabled: false,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      };
      mockCreatedSources.push(source);
      return source;
    }),
    syncDataSource: jest.fn(async () => ({})),
    deleteDataSource: jest.fn(async () => undefined),
    updateDataSource: jest.fn(async () => ({})),
    ingestData: jest.fn(async () => ({
      message: 'Ingestion successful',
      properties_processed: 2,
      errors: [],
      source_type: 'file',
      source_name: null,
    })),
    ingestFileUpload: jest.fn(async () => ({
      message: 'Ingestion successful',
      properties_processed: 2,
      errors: [],
      source_type: 'file',
      source_name: null,
    })),
    getExcelSheets: jest.fn(async () => ({
      file_url: 'https://example.com/data.xlsx',
      sheet_names: ['Sheet1', 'Sheet2'],
      default_sheet: 'Sheet1',
      row_count: { Sheet1: 10, Sheet2: 20 },
    })),
    getExcelSheetsUpload: jest.fn(async () => ({
      file_url: 'https://example.com/data.xlsx',
      sheet_names: ['Sheet1', 'Sheet2'],
      default_sheet: 'Sheet1',
      row_count: { Sheet1: 10, Sheet2: 20 },
    })),
    listPortals: jest.fn(async () => ({
      adapters: [
        {
          name: 'overpass',
          display_name: 'OpenStreetMap',
          configured: true,
          has_api_key: false,
          rate_limit: null,
        },
      ],
      count: 1,
    })),
    fetchFromPortal: jest.fn(async () => ({
      message: 'Fetched 1 properties',
      portal: 'overpass',
      properties_processed: 1,
      errors: [],
      source_type: 'portal',
      source_name: 'warsaw_rent',
    })),
    ApiError: MockApiError,
  };
});

// The page renders two buttons named "Import Data": the tab that opens the
// import panel and the submit button inside it. This helper returns both.
const getImportButtons = () =>
  screen.getAllByRole('button', { name: 'Import Data' }) as HTMLButtonElement[];

describe('DataSourcesPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockCreatedSources.length = 0;
  });

  it('loads the configured data sources on mount', async () => {
    render(<DataSourcesPage />);

    await waitFor(() => expect(listDataSources).toHaveBeenCalled());
    expect(await screen.findByText('No data sources configured yet.')).toBeInTheDocument();
  });

  it('ingests CSV from URL', async () => {
    render(<DataSourcesPage />);

    // Open the import panel
    const [importTab] = getImportButtons();
    fireEvent.click(importTab);

    fireEvent.change(screen.getByLabelText('File URL'), {
      target: { value: 'https://example.com/data.csv' },
    });
    fireEvent.change(screen.getByLabelText(/Source Name/), {
      target: { value: 'Q1 Imports' },
    });

    const [, importButton] = getImportButtons();
    fireEvent.click(importButton);

    await waitFor(() => expect(ingestData).toHaveBeenCalled());
    expect((ingestData as jest.Mock).mock.calls[0][0]).toEqual({
      file_urls: ['https://example.com/data.csv'],
      sheet_name: undefined,
      header_row: 0,
      source_name: 'Q1 Imports',
    });
    await waitFor(() => expect(screen.getByText('Ingestion successful')).toBeInTheDocument());
  });

  it('loads Excel sheets and ingests selected sheet', async () => {
    render(<DataSourcesPage />);

    // Open the import panel
    const [importTab] = getImportButtons();
    fireEvent.click(importTab);

    fireEvent.change(screen.getByLabelText('File URL'), {
      target: { value: 'https://example.com/data.xlsx' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Load Sheets' }));

    await waitFor(() => expect(getExcelSheets).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByLabelText('Select Sheet')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText('Select Sheet'), {
      target: { value: 'Sheet2' },
    });
    fireEvent.change(screen.getByLabelText('Header Row (0-indexed)'), {
      target: { value: '2' },
    });

    const [, importButton] = getImportButtons();
    fireEvent.click(importButton);

    await waitFor(() => expect(ingestData).toHaveBeenCalled());
    expect((ingestData as jest.Mock).mock.calls[0][0]).toEqual({
      file_urls: ['https://example.com/data.xlsx'],
      sheet_name: 'Sheet2',
      header_row: 2,
      source_name: undefined,
    });
  });

  it('fetches from portal', async () => {
    render(<DataSourcesPage />);

    // Open the import panel, then switch to the portal mode
    const [importTab] = getImportButtons();
    fireEvent.click(importTab);
    fireEvent.click(screen.getByRole('button', { name: 'Portal API' }));

    await waitFor(() => expect(listPortals).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByLabelText('Portal')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/City/), { target: { value: 'Warsaw' } });

    fireEvent.click(screen.getByRole('button', { name: 'Fetch from Portal' }));

    await waitFor(() => expect(fetchFromPortal).toHaveBeenCalled());
    expect((fetchFromPortal as jest.Mock).mock.calls[0][0]).toMatchObject({
      portal: 'overpass',
      city: 'Warsaw',
      listing_type: 'rent',
      limit: 50,
    });
    await waitFor(() => expect(screen.getByText('Fetched 1 properties')).toBeInTheDocument());
  });

  it('registers the official price register as a source', async () => {
    render(<DataSourcesPage />);

    // Open the import panel, then switch to the register mode
    const [importTab] = getImportButtons();
    fireEvent.click(importTab);
    fireEvent.click(screen.getByRole('button', { name: 'Price Register' }));

    await waitFor(() => expect(screen.getByLabelText(/City/)).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/City/), { target: { value: 'Kraków' } });

    fireEvent.click(screen.getByRole('button', { name: 'Register Source' }));

    await waitFor(() => expect(createDataSource).toHaveBeenCalled());
    expect((createDataSource as jest.Mock).mock.calls[0][0]).toMatchObject({
      name: 'Kraków price register',
      source_type: 'register',
      config: { city: 'Kraków' },
    });

    // The panel says the register took the source.
    await waitFor(() => expect(screen.getByText(/is registered/)).toBeInTheDocument());

    // The ledger carries the new row, and the row names its kind.
    await waitFor(() => expect(screen.getByText('Official Price Register')).toBeInTheDocument());
  });
});
