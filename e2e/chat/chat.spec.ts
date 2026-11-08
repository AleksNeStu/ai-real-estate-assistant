/**
 * Chat/AI Assistant flow E2E tests.
 * Tests chat message sending, SSE streaming, error handling, and sources display.
 */

import { test, expect } from '../conftest';
import {
  mockChatSuccess,
  mockChatError,
  createMockChatWithRetry,
  mockChatWithSources,
} from '../mocks';

test.describe('Chat Flows', () => {
  test.describe('Basic Chat', () => {
    test('should display chat interface @smoke', async ({ authenticatedChatPage }) => {
      await authenticatedChatPage.navigate();

      // Verify chat elements are visible
      await expect(authenticatedChatPage.messageInput).toBeVisible();
      await expect(authenticatedChatPage.sendButton).toBeVisible();
    });

    test('should send message and receive response', async ({ authenticatedChatPage, page }) => {
      // Mock chat API
      await page.route('**/api/v1/chat*', mockChatSuccess);

      await authenticatedChatPage.navigate();
      await authenticatedChatPage.sendMessageAndWaitForResponse('Find me an apartment in Berlin');

      // Verify response is displayed
      const responseText = await authenticatedChatPage.getLastAssistantMessageText();
      expect(responseText.length).toBeGreaterThan(0);
    });

    test('should display streaming response', async ({ authenticatedChatPage, page }) => {
      // Mock streaming chat response
      await page.route('**/api/v1/chat*', mockChatSuccess);

      await authenticatedChatPage.navigate();
      await authenticatedChatPage.sendMessage('Show me properties');

      // Wait for response to appear
      await authenticatedChatPage.waitForResponse();

      // Verify response is displayed
      await expect(authenticatedChatPage.lastAssistantMessage).toBeVisible();
    });

    test('should maintain conversation history', async ({ authenticatedChatPage, page }) => {
      await page.route('**/api/v1/chat*', mockChatSuccess);

      await authenticatedChatPage.navigate();

      // Send first message
      await authenticatedChatPage.sendMessageAndWaitForResponse('Hello');

      // Send second message
      await authenticatedChatPage.sendMessageAndWaitForResponse('How are you?');

      // Verify both user messages are displayed
      const userMessages = await authenticatedChatPage.getUserMessages();
      expect(userMessages.length).toBe(2);

      // Verify both assistant responses are displayed
      const assistantMessages = await authenticatedChatPage.getAssistantMessages();
      expect(assistantMessages.length).toBe(2);
    });
  });

  test.describe('Error Handling', () => {
    test('should display error message on chat failure', async ({
      authenticatedChatPage,
      page,
    }) => {
      await page.route('**/api/v1/chat*', async (route) => {
        await mockChatError(route, 500, 'Internal server error');
      });

      await authenticatedChatPage.navigate();
      await authenticatedChatPage.sendMessage('Test message');

      // Should show error
      expect(await authenticatedChatPage.hasError()).toBe(true);
    });

    test('should show retry button on failure', async ({ authenticatedChatPage, page }) => {
      await page.route('**/api/v1/chat*', createMockChatWithRetry(1));

      await authenticatedChatPage.navigate();
      await authenticatedChatPage.sendMessage('Test message');

      // Should show retry button
      await expect(authenticatedChatPage.retryButton).toBeVisible({ timeout: 10000 });
    });

    test('should recover after retry', async ({ authenticatedChatPage, page }) => {
      await page.route('**/api/v1/chat*', createMockChatWithRetry(1));

      await authenticatedChatPage.navigate();
      await authenticatedChatPage.sendMessage('Test message');

      // Wait for error state
      await expect(authenticatedChatPage.retryButton).toBeVisible({ timeout: 10000 });

      // Click retry
      await authenticatedChatPage.retry();

      // Should show response after retry
      await expect(authenticatedChatPage.lastAssistantMessage).toBeVisible({ timeout: 15000 });
    });

    test('should handle timeout gracefully', async ({ authenticatedChatPage, page }) => {
      // Mock slow/timeout response
      await page.route('**/api/v1/chat*', async (route) => {
        await route.fulfill({
          status: 504,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ detail: 'Request timeout' }),
        });
      });

      await authenticatedChatPage.navigate();
      await authenticatedChatPage.sendMessage('Test message');

      // Should show timeout error
      expect(await authenticatedChatPage.hasError()).toBe(true);
      const errorText = await authenticatedChatPage.getErrorMessage();
      expect(errorText.toLowerCase()).toContain('timeout');
    });
  });

  test.describe('Sources Display', () => {
    test('should display property sources when available', async ({
      authenticatedChatPage,
      page,
    }) => {
      await page.route('**/api/v1/chat*', mockChatWithSources);

      await authenticatedChatPage.navigate();
      await authenticatedChatPage.sendMessageAndWaitForResponse('Find apartments in Berlin');

      // Should show sources
      expect(await authenticatedChatPage.hasSources()).toBe(true);
    });

    test('should show source count', async ({ authenticatedChatPage, page }) => {
      await page.route('**/api/v1/chat*', mockChatWithSources);

      await authenticatedChatPage.navigate();
      await authenticatedChatPage.sendMessageAndWaitForResponse('Show me properties');

      // Should have at least one source
      const sourceCount = await authenticatedChatPage.getSourceCount();
      expect(sourceCount).toBeGreaterThan(0);
    });

    test('should show the citation of a source when it is clicked', async ({
      authenticatedChatPage,
      page,
    }) => {
      await page.route('**/api/v1/chat*', mockChatWithSources);

      await authenticatedChatPage.navigate();
      await authenticatedChatPage.sendMessageAndWaitForResponse('Find properties');

      // Click on first source. A citation points to a document of the
      // knowledge base - it does not lead to a page of a single property.
      await authenticatedChatPage.clickSource(0);

      // The citation of the source is still there and the conversation did not
      // break.
      await expect(authenticatedChatPage.lastAssistantMessage).toBeVisible();
      expect(await authenticatedChatPage.getSourceCount()).toBeGreaterThan(0);
    });
  });

  test.describe('Suggested Prompts', () => {
    test('should display suggested prompts on empty chat', async ({ authenticatedChatPage }) => {
      await authenticatedChatPage.navigate();

      // Should show suggested prompts for new chat
      expect(await authenticatedChatPage.hasSuggestedPrompts()).toBe(true);
    });

    test('should send suggested prompt when clicked', async ({ authenticatedChatPage, page }) => {
      await page.route('**/api/v1/chat*', mockChatSuccess);

      await authenticatedChatPage.navigate();

      // Click first suggested prompt
      await authenticatedChatPage.clickSuggestedPrompt(0);

      // Should send message and show response
      await authenticatedChatPage.waitForResponse();
      await expect(authenticatedChatPage.lastAssistantMessage).toBeVisible();
    });
  });

  test.describe('Session Management', () => {
    test('should keep the conversation in the state of the page', async ({
      authenticatedChatPage,
      page,
    }) => {
      await page.route('**/api/v1/chat*', mockChatSuccess);

      await authenticatedChatPage.navigate();
      await authenticatedChatPage.sendMessageAndWaitForResponse('Hello');

      // Get messages before reload
      const messagesBefore = await authenticatedChatPage.getUserMessages();
      expect(messagesBefore.length).toBe(1);

      // Reload page. The conversation lives in the state of the page - there is
      // no history of the sessions in the product - so a reload starts over.
      await page.reload();

      const messagesAfter = await authenticatedChatPage.getUserMessages();
      expect(messagesAfter.length).toBe(0);
      expect(await authenticatedChatPage.hasSuggestedPrompts()).toBe(true);
    });

    test('should show the empty chat with suggested prompts', async ({
      authenticatedChatPage,
      page,
    }) => {
      await page.route('**/api/v1/chat*', mockChatSuccess);

      await authenticatedChatPage.navigate();

      // A chat without a message offers the suggested prompts
      expect(await authenticatedChatPage.hasSuggestedPrompts()).toBe(true);
      expect(await authenticatedChatPage.getUserMessages()).toHaveLength(0);
    });
  });

  test.describe('Debug Mode', () => {
    test('should show debug info when enabled', async ({ authenticatedChatPage, page }) => {
      await page.route('**/api/v1/chat*', mockChatSuccess);

      // Navigate with debug mode
      await page.goto('/chat?debug=1');

      await authenticatedChatPage.sendMessageAndWaitForResponse('Test');

      // Should show debug info. The intermediate steps arrive with the meta
      // event of the stream and are shown in a details element.
      const debugPanel = page.locator('details').filter({ hasText: /debug trace/i });
      await expect(debugPanel).toBeVisible({ timeout: 10000 });
    });
  });
});
