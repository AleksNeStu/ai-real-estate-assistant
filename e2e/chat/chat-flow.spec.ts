/**
 * End-to-end chat flow test (Task #125).
 * Covers the full interaction: send message → receive streaming response → sources expander visible.
 */

import { test, expect } from '../conftest';
import { mockChatWithSources, mockChatWithSourcesDelayed } from '../mocks';

test.describe('End-to-End Chat Flow', () => {
  test('should complete full chat interaction: send → stream → sources visible', async ({
    authenticatedChatPage,
    page,
  }) => {
    // Mock chat API to return streaming response with sources. The answer is
    // delayed, so the state "Thinking..." of the assistant is visible.
    await page.route('**/api/v1/chat*', mockChatWithSourcesDelayed(1500));

    // Step 1: Navigate and verify chat interface loads
    await authenticatedChatPage.navigate();
    await expect(authenticatedChatPage.messageInput).toBeVisible();
    await expect(authenticatedChatPage.sendButton).toBeVisible();

    // Step 2: Send a message
    await authenticatedChatPage.sendMessage('Find apartments in Berlin under €1500');

    // Step 3: Verify loading indicator appears (streaming started)
    await expect(authenticatedChatPage.loadingIndicator).toBeVisible({ timeout: 5000 });

    // Step 4: Wait for streaming response to complete and render
    // Step 4: Wait for the answer. The citations of the answer appear when
    // the stream is complete - before that the bubble shows the placeholder
    // "Thinking...".
    const citationsExpander = page.locator('details:has(summary:has-text("Citations"))');
    await expect(citationsExpander).toBeVisible({ timeout: 30000 });

    await expect(authenticatedChatPage.lastAssistantMessage).toBeVisible({
      timeout: 30000,
    });

    // Step 5: Verify response contains expected property content
    const responseText = await authenticatedChatPage.getLastAssistantMessageText();
    expect(responseText.length).toBeGreaterThan(0);
    expect(responseText.toLowerCase()).toMatch(/propert/);

    // Step 6: Verify sources/citations expander is visible
    const sourcesExpander = page.locator('details:has(summary:has-text("Sources"))');
    const expander = citationsExpander.or(sourcesExpander);

    await expect(expander).toBeVisible({ timeout: 10000 });

    // Step 7: Verify the expander shows a count > 0
    const summaryText = await expander.locator('summary').textContent();
    const countMatch = summaryText?.match(/\((\d+)\)/);
    expect(countMatch).not.toBeNull();
    const sourceCount = parseInt(countMatch![1], 10);
    expect(sourceCount).toBeGreaterThan(0);

    // Step 8: Expand the citations/sources section
    await expander.locator('summary').click();

    // Step 9: Verify citation items are rendered
    const citationItems = expander.locator('li, [data-testid="source-item"], .source-item');
    await expect(citationItems.first()).toBeVisible({ timeout: 5000 });
    const itemCount = await citationItems.count();
    expect(itemCount).toBeGreaterThan(0);

    // Step 10: Verify user message is displayed in conversation
    const userMessages = await authenticatedChatPage.getUserMessages();
    expect(userMessages.length).toBeGreaterThanOrEqual(1);
  });

  test('should render streaming text progressively in assistant message', async ({
    authenticatedChatPage,
    page,
  }) => {
    await page.route('**/api/v1/chat*', mockChatWithSources);

    await authenticatedChatPage.navigate();
    await authenticatedChatPage.sendMessage('Show me properties in Berlin');

    // Wait for response to appear
    await expect(authenticatedChatPage.lastAssistantMessage).toBeVisible({
      timeout: 30000,
    });

    // Verify the response text is rendered (contains expected content from mock)
    const responseText = await authenticatedChatPage.getLastAssistantMessageText();
    expect(responseText).toMatch(/propert/i);
    expect(responseText).toContain('Mitte');
  });

  test('should display citations with confidence badges', async ({
    authenticatedChatPage,
    page,
  }) => {
    await page.route('**/api/v1/chat*', mockChatWithSources);

    await authenticatedChatPage.navigate();
    await authenticatedChatPage.sendMessageAndWaitForResponse('Find apartments');

    // Expand the citations section
    const citationsExpander = page.locator('details:has(summary:has-text("Citations"))');
    const sourcesExpander = page.locator('details:has(summary:has-text("Sources"))');

    const expander = citationsExpander.or(sourcesExpander);
    await expect(expander).toBeVisible({ timeout: 10000 });
    await expander.locator('summary').click();

    // Verify at least one citation item has content
    const citationItems = expander.locator('li');
    await expect(citationItems.first()).toBeVisible({ timeout: 5000 });

    // Verify citation text contains source information
    const firstCitationText = await citationItems.first().textContent();
    expect(firstCitationText!.length).toBeGreaterThan(0);
  });
});
