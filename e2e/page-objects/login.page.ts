/**
 * Login Page Object for E2E tests.
 * Encapsulates login page interactions and elements.
 */

import { Page, Locator, expect } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;
  readonly forgotPasswordLink: Locator;
  readonly registerLink: Locator;

  constructor(page: Page) {
    this.page = page;
    // Actual UI uses <Label htmlFor="email"> and <Input id="email">.
    // The name has to match exactly: the footer carries a newsletter field
    // labelled "Email address", and a loose match collects that one as well -
    // two elements, and every action on them fails the strict mode.
    this.emailInput = page
      .getByLabel('Email', { exact: true })
      .or(page.getByRole('textbox', { name: /^email$/i }));
    this.passwordInput = page
      .getByLabel('Password', { exact: true })
      .or(page.getByRole('textbox', { name: /^password$/i }));
    // Submit button - must be inside the form of the login, and be
    // type="submit" to avoid matching nav buttons. The footer newsletter has a
    // form with a submit button of its own, so the form is found through the
    // email field it belongs to.
    const loginForm = page.locator('form').filter({ has: page.locator('#email') });
    this.submitButton = loginForm
      .locator('button[type="submit"]')
      .or(page.locator('button[type="submit"]').filter({ hasText: /sign in|log in|zaloguj/i }));
    // Error message is in div with bg-destructive/15 class - be specific to avoid matching Next.js route announcer
    this.errorMessage = page
      .locator('.bg-destructive\\/15, .text-destructive')
      .filter({ has: page.locator('svg, span, p') })
      .first();
    // Forgot password link - handle multiple languages (EN/PL/RU) - it's a small link next to Password label
    // Use regex for case-insensitive matching
    this.forgotPasswordLink = page
      .locator('a.text-xs')
      .filter({ hasText: /forgot|zapomniał|забыл/i })
      .first();
    // Register/sign up link - handle multiple languages - it's in the card footer with underline class
    this.registerLink = page
      .locator('a.underline')
      .filter({ hasText: /sign up|create account|zarejestruj|зарегистрироваться/i })
      .first();
  }

  /**
   * Navigate to the login page.
   */
  async navigate(): Promise<void> {
    await this.page.goto('/auth/login');
    // Wait for the form to be visible
    await expect(this.emailInput).toBeVisible({ timeout: 10000 });
  }

  /**
   * Fill the login form with credentials.
   */
  async fillForm(email: string, password: string): Promise<void> {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
  }

  /**
   * Submit the login form.
   */
  async submit(): Promise<void> {
    await this.submitButton.click();
  }

  /**
   * Perform a complete login action.
   */
  async login(email: string, password: string): Promise<void> {
    await this.fillForm(email, password);
    await this.submit();
  }

  /**
   * Wait for login to complete (redirect to home or dashboard).
   */
  async waitForLoginSuccess(): Promise<void> {
    // Wait for navigation away from login page
    await this.page.waitForURL(/^(?!.*\/auth\/login).*$/, { timeout: 15000 });
  }

  /**
   * Wait for error message to appear.
   */
  async waitForError(): Promise<string> {
    await expect(this.errorMessage).toBeVisible({ timeout: 5000 });
    return (await this.errorMessage.textContent()) || '';
  }

  /**
   * Check if error message is visible.
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
   * Click the forgot password link.
   */
  async clickForgotPassword(): Promise<void> {
    await this.forgotPasswordLink.click();
  }

  /**
   * Click the register link.
   */
  async clickRegister(): Promise<void> {
    await this.registerLink.click();
  }
}
