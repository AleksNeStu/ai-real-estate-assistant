/**
 * Chat Page Object for E2E tests.
 * Encapsulates chat page interactions and elements.
 */

import { Page, Locator, expect } from '@playwright/test';

export class ChatPage {
  readonly page: Page;
  readonly messageInput: Locator;
  readonly sendButton: Locator;
  readonly messagesContainer: Locator;
  readonly userMessage: Locator;
  readonly assistantMessage: Locator;
  readonly lastAssistantMessage: Locator;
  readonly retryButton: Locator;
  readonly errorMessage: Locator;
  readonly sourcesContainer: Locator;
  readonly loadingIndicator: Locator;
  readonly suggestedPrompts: Locator;
  readonly sessionHistory: Locator;

  constructor(page: Page) {
    this.page = page;
    // Actual UI: input with aria-label="Chat message input"
    this.messageInput = page
      .getByLabel(/chat message input/i)
      .or(page.getByPlaceholder(/type your question|ask about properties/i));
    // Send button: the chat marks it with data-testid="chat-send" and gives
    // it the aria-label "Send message" (or "Sending..." while it waits). The
    // newsletter of the footer has a form with a submit button of its own, so
    // the plain "form button[type=submit]" collected that one as well.
    this.sendButton = page.getByTestId('chat-send').or(page.getByLabel(/^send(ing)? message$/i));
    // Messages container - the scrollable div containing the messages
    this.messagesContainer = page.locator('div.flex-1.overflow-y-auto').first();
    // A message bubble is a direct child of the messages container. The user
    // bubble carries a muted background, the assistant one a plain background
    // with a border. The loading indicator shares the classes of an assistant
    // bubble, but it is marked with an aria-label and is therefore excluded.
    this.userMessage = this.messagesContainer.locator(
      ':scope > div.w-full.items-start.bg-muted\\/50'
    );
    this.assistantMessage = this.messagesContainer.locator(
      ':scope > div.w-full.items-start.bg-background.border:not([aria-label])'
    );
    this.lastAssistantMessage = this.assistantMessage.last();
    // Retry button appears in error state - button with RefreshCw icon or "Retry" text
    this.retryButton = page.getByRole('button', { name: /^retry$/i });
    // The error bubble is the only alert inside the conversation
    this.errorMessage = this.messagesContainer.locator('[role="alert"]');
    // Citations are in a details element with a "Citations (N)" summary
    this.sourcesContainer = page.locator('details:has(summary:has-text("Citations"))');
    // Loading indicator - the "Thinking..." status of the streaming answer.
    // It is the only status with an aria-label (the empty state has none).
    this.loadingIndicator = page.locator('[role="status"][aria-label]');
    // Suggested prompts are buttons in the empty state with text-left class
    this.suggestedPrompts = page.locator(
      'button.text-left.text-sm.text-primary, .space-y-2 button.text-left'
    );
    // Session history not currently in UI
    this.sessionHistory = page.locator('aside, [data-testid="session-history"]');
  }

  /**
   * Navigate to the chat page.
   */
  async navigate(): Promise<void> {
    await this.page.goto('/chat');
    // Wait for the chat interface to be visible
    await expect(this.messageInput).toBeVisible({ timeout: 10000 });
  }

  /**
   * Send a message in the chat.
   */
  async sendMessage(message: string): Promise<void> {
    await this.messageInput.fill(message);
    await this.sendButton.click();
  }

  /**
   * Send a message and wait for response.
   */
  async sendMessageAndWaitForResponse(message: string): Promise<void> {
    await this.sendMessage(message);
    await this.waitForResponse();
  }

  /**
   * Wait for the assistant response to appear.
   */
  async waitForResponse(): Promise<void> {
    // The answer is streamed: the bubble of the assistant appears at once and
    // is filled while the stream runs. It counts as answered when it carries
    // a text.
    await expect
      .poll(async () => ((await this.lastAssistantMessage.textContent()) ?? '').trim().length, {
        timeout: 30000,
      })
      .toBeGreaterThan(0);
  }

  /**
   * Get the last assistant message text.
   */
  async getLastAssistantMessageText(): Promise<string> {
    await expect(this.lastAssistantMessage).toBeVisible({ timeout: 5000 });
    return (await this.lastAssistantMessage.textContent()) || '';
  }

  /**
   * Check if the last message contains expected text.
   */
  async lastMessageContains(text: string): Promise<boolean> {
    const messageText = await this.getLastAssistantMessageText();
    return messageText.toLowerCase().includes(text.toLowerCase());
  }

  /**
   * Wait for and click the retry button.
   */
  async retry(): Promise<void> {
    await expect(this.retryButton).toBeVisible({ timeout: 5000 });
    await this.retryButton.click();
  }

  /**
   * Check if error is displayed.
   */
  async hasError(): Promise<boolean> {
    return await this.errorMessage.isVisible();
  }

  /**
   * Get the error message text.
   */
  async getErrorMessage(): Promise<string> {
    return (await this.errorMessage.textContent()) || '';
  }

  /**
   * Check if sources are displayed.
   */
  async hasSources(): Promise<boolean> {
    return await this.sourcesContainer.isVisible();
  }

  /**
   * Get the number of displayed sources (citations).
   */
  async getSourceCount(): Promise<number> {
    if (!(await this.hasSources())) return 0;
    const sources = this.sourcesContainer.locator('ol > li');
    return await sources.count();
  }

  /**
   * Click on a source to view property details.
   */
  async clickSource(index: number = 0): Promise<void> {
    const sources = this.sourcesContainer.locator('ol > li');
    const source = sources.nth(index);
    if (await source.isVisible()) {
      await source.click();
    }
  }

  /**
   * Check if suggested prompts are displayed.
   */
  async hasSuggestedPrompts(): Promise<boolean> {
    const count = await this.suggestedPrompts.count();
    return count > 0;
  }

  /**
   * Click on a suggested prompt.
   */
  async clickSuggestedPrompt(index: number = 0): Promise<void> {
    // The suggested prompts ARE the buttons themselves
    const prompt = this.suggestedPrompts.nth(index);
    if (await prompt.isVisible()) {
      await prompt.click();
    }
  }

  /**
   * Get all user messages in the conversation.
   */
  async getUserMessages(): Promise<string[]> {
    const count = await this.userMessage.count();
    const messages: string[] = [];
    for (let i = 0; i < count; i++) {
      messages.push((await this.userMessage.nth(i).textContent()) || '');
    }
    return messages;
  }

  /**
   * Get all assistant messages in the conversation.
   */
  async getAssistantMessages(): Promise<string[]> {
    const count = await this.assistantMessage.count();
    const messages: string[] = [];
    for (let i = 0; i < count; i++) {
      messages.push((await this.assistantMessage.nth(i).textContent()) || '');
    }
    return messages;
  }

  /**
   * Clear the chat session (if button exists).
   */
  async clearSession(): Promise<void> {
    const clearButton = this.page.getByRole('button', { name: /clear|new chat|reset/i });
    if (await clearButton.isVisible()) {
      await clearButton.click();
    }
  }
}
