/**
 * Document management flow E2E tests.
 * Tests document upload, listing, deletion, and expiry alerts.
 */

import { test, expect } from '../conftest';

// Mock document data
const mockDocuments = [
  {
    id: 'doc-1',
    original_filename: 'contract.pdf',
    file_type: 'application/pdf',
    file_size: 1024000,
    document_type: 'contract',
    status: 'uploaded',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    expires_at: null,
    extracted_text: null,
  },
  {
    id: 'doc-2',
    original_filename: 'id_card.jpg',
    file_type: 'image/jpeg',
    file_size: 512000,
    document_type: 'id_document',
    status: 'processed',
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 86400000).toISOString(),
    expires_at: new Date(Date.now() + 7 * 86400000).toISOString(), // Expires in 7 days
    extracted_text: 'Extracted ID text...',
  },
  {
    id: 'doc-3',
    original_filename: 'property_report.docx',
    file_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    file_size: 256000,
    document_type: 'report',
    status: 'uploaded',
    created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    expires_at: null,
    extracted_text: null,
  },
];

const mockDocumentsResponse = {
  items: mockDocuments,
  total: 3,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const mockExpiringResponse = {
  items: [mockDocuments[1]], // Only the ID card is expiring
  total: 1,
};

async function mockDocumentsAPI(page: import('@playwright/test').Page) {
  // Mock documents list
  await page.route('**/api/v1/documents*', async (route) => {
    const request = route.request();
    if (request.method() === 'GET') {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mockDocumentsResponse),
      });
    } else if (request.method() === 'DELETE') {
      await route.fulfill({
        status: 204,
      });
    }
  });

  // Mock expiring documents
  await page.route('**/api/v1/documents/expiring*', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(mockExpiringResponse),
    });
  });
}

async function mockEmptyDocuments(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/documents*', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      }),
    });
  });

  await page.route('**/api/v1/documents/expiring*', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: [], total: 0 }),
    });
  });
}

async function mockDocumentsError(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/documents*', async (route) => {
    await route.fulfill({
      status: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ detail: 'Failed to load documents' }),
    });
  });
}

test.describe('Document Management Flows', () => {
  // Setup authentication for all tests in this describe block
  test.beforeEach(async ({ page }) => {
    // Mock /auth/me to return authenticated user
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: 'test-user-001',
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'user',
          is_active: true,
          is_verified: true,
          created_at: new Date().toISOString(),
        }),
      });
    });

    // Set auth cookie
    await page.context().addCookies([
      {
        name: 'access_token',
        value: 'mock-access-token',
        domain: 'localhost',
        path: '/',
        httpOnly: true,
        sameSite: 'Lax' as const,
      },
    ]);
  });

  test.describe('Document List', () => {
    test('should display documents page @smoke', async ({ page }) => {
      await mockDocumentsAPI(page);
      await page.goto('/documents');

      // Verify header is visible
      await expect(page.getByRole('heading', { name: 'Documents' })).toBeVisible({
        timeout: 10000,
      });
    });

    test('should display list of documents', async ({ page }) => {
      await mockDocumentsAPI(page);
      await page.goto('/documents');

      // Wait for documents to load
      await expect(page.locator('text=contract.pdf').first()).toBeVisible({ timeout: 10000 });
      await expect(page.locator('text=id_card.jpg').first()).toBeVisible();
      await expect(page.locator('text=property_report.docx').first()).toBeVisible();
    });

    test('should display empty state when no documents', async ({ page }) => {
      await mockEmptyDocuments(page);
      await page.goto('/documents');

      // Should show empty state
      await expect(page.locator('text=/no documents yet/i')).toBeVisible({ timeout: 10000 });
    });

    test('should display upload and refresh buttons', async ({ page }) => {
      await mockDocumentsAPI(page);
      await page.goto('/documents');

      await expect(page.getByRole('button', { name: /upload document/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
    });

    test('should display expiring documents alert', async ({ page }) => {
      await mockDocumentsAPI(page);
      await page.goto('/documents');

      // Should show expiring documents alert
      await expect(page.locator('[class*="bg-warning"]')).toBeVisible({ timeout: 10000 });
    });

    test('should display error state on API failure', async ({ page }) => {
      await mockDocumentsError(page);
      await page.goto('/documents');

      // Should show error message
      await expect(page.getByRole('heading', { name: /failed to load documents/i })).toBeVisible({
        timeout: 10000,
      });
      await expect(page.getByRole('button', { name: /try again/i })).toBeVisible();
    });
  });

  test.describe('Document Upload', () => {
    test('should open upload modal when clicking upload button', async ({ page }) => {
      await mockDocumentsAPI(page);
      await page.goto('/documents');

      await page.getByRole('button', { name: /upload document/i }).click();

      // Modal should appear
      await expect(page.locator('dialog')).toBeVisible({ timeout: 5000 });
      await expect(page.getByRole('heading', { name: /upload document/i })).toBeVisible();
    });

    test('should close upload modal when clicking cancel', async ({ page }) => {
      await mockDocumentsAPI(page);
      await page.goto('/documents');

      await page.getByRole('button', { name: /upload document/i }).click();
      await expect(page.locator('dialog')).toBeVisible({ timeout: 5000 });

      // Click close button
      const closeButton = page.locator('dialog button[aria-label]').first();
      await closeButton.click();

      // Modal should close
      await expect(page.locator('dialog')).not.toBeVisible({ timeout: 3000 });
    });
  });

  test.describe('Document Actions', () => {
    test('should refresh document list', async ({ page }) => {
      await mockDocumentsAPI(page);
      await page.goto('/documents');

      await expect(page.locator('text=contract.pdf').first()).toBeVisible({ timeout: 10000 });

      // Click refresh
      await page.getByRole('button', { name: /refresh/i }).click();

      // Should still show documents (refresh happened)
      await expect(page.locator('text=contract.pdf')).toBeVisible({ timeout: 5000 });
    });

    test('should retry loading on error', async ({ page }) => {
      let failCount = 0;

      await page.route('**/api/v1/documents*', async (route) => {
        failCount++;
        if (failCount <= 1) {
          await route.fulfill({
            status: 500,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ detail: 'Failed to load documents' }),
          });
        } else {
          await route.fulfill({
            status: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(mockDocumentsResponse),
          });
        }
      });

      await page.route('**/api/v1/documents/expiring*', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ items: [], total: 0 }),
        });
      });

      await page.goto('/documents');

      // Should show error
      await expect(page.getByRole('heading', { name: /failed to load documents/i })).toBeVisible({
        timeout: 10000,
      });

      // Click retry
      await page.getByRole('button', { name: /try again/i }).click();

      // Should show documents after retry
      await expect(page.locator('text=contract.pdf').first()).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Document Details', () => {
    test('should display document file names', async ({ page }) => {
      await mockDocumentsAPI(page);
      await page.goto('/documents');

      await expect(page.locator('text=contract.pdf').first()).toBeVisible({ timeout: 10000 });
    });

    test('should display document types', async ({ page }) => {
      await mockDocumentsAPI(page);
      await page.goto('/documents');

      // The types of the documents are offered by the filter of the list.
      const categoryFilter = page.getByRole('combobox', { name: /filter by category/i });
      await expect(categoryFilter).toBeVisible({ timeout: 10000 });

      const options = categoryFilter.locator('option');
      await expect(options).toHaveCount(6);
      await expect(options.nth(1)).toHaveText(/contract/i);
      await expect(options.nth(2)).toHaveText(/inspection report/i);
    });
  });

  test.describe('Pagination', () => {
    test('should show load more button when more pages exist', async ({ page }) => {
      await page.route('**/api/v1/documents*', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            items: mockDocuments,
            total: 50,
            page: 1,
            page_size: 20,
            total_pages: 3,
          }),
        });
      });

      await page.route('**/api/v1/documents/expiring*', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ items: [], total: 0 }),
        });
      });

      await page.goto('/documents');

      // Should show load more button
      await expect(page.getByRole('button', { name: /load more/i })).toBeVisible({
        timeout: 10000,
      });
    });

    test('should not show load more when on last page', async ({ page }) => {
      await mockDocumentsAPI(page);
      await page.goto('/documents');

      // Should NOT show load more button (only 1 page)
      await expect(page.getByRole('button', { name: /load more/i })).not.toBeVisible({
        timeout: 10000,
      });
    });
  });

  test.describe('Accessibility', () => {
    test('should have accessible upload button', async ({ page }) => {
      await mockDocumentsAPI(page);
      await page.goto('/documents');

      const uploadButton = page.getByRole('button', { name: /upload document/i });
      await expect(uploadButton).toBeVisible();
      await expect(uploadButton).toBeEnabled();
    });

    test('should have accessible refresh button', async ({ page }) => {
      await mockDocumentsAPI(page);
      await page.goto('/documents');

      const refreshButton = page.getByRole('button', { name: /refresh/i });
      await expect(refreshButton).toBeVisible();
      await expect(refreshButton).toBeEnabled();
    });
  });
});
