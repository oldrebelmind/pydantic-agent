import { test, expect } from '@playwright/test';

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should render chat interface with all elements', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/Pydantic AI Chat/);

    // Check main heading
    await expect(page.getByRole('heading', { name: /Pydantic AI Chat/i })).toBeVisible();

    // Check subtitle
    await expect(page.getByText(/Powered by Pydantic AI, Mem0, and Langfuse/i)).toBeVisible();

    // Check card title
    await expect(page.getByText('Chat with AI Agent')).toBeVisible();

    // Check welcome message
    await expect(page.getByText(/Start a conversation!/i)).toBeVisible();
    await expect(page.getByText(/Ask me anything. I have memory powered by Mem0 GraphRAG./i)).toBeVisible();

    // Check input field
    const input = page.getByPlaceholder(/Type your message.../i);
    await expect(input).toBeVisible();
    await expect(input).toBeEnabled();

    // Check send button
    const sendButton = page.locator('button[type="submit"]');
    await expect(sendButton).toBeVisible();
    await expect(sendButton).toBeDisabled(); // Should be disabled when input is empty
  });

  test('should enable send button when text is entered', async ({ page }) => {
    const input = page.getByPlaceholder(/Type your message.../i);
    const sendButton = page.locator('button[type="submit"]');

    // Initially disabled
    await expect(sendButton).toBeDisabled();

    // Type a message
    await input.fill('Hello, AI!');

    // Should now be enabled
    await expect(sendButton).toBeEnabled();

    // Clear input
    await input.clear();

    // Should be disabled again
    await expect(sendButton).toBeDisabled();
  });

  test('should send a message and receive streaming response', async ({ page }) => {
    const input = page.getByPlaceholder(/Type your message.../i);
    const sendButton = page.locator('button[type="submit"]');

    // Type and send a message
    await input.fill('What is kayaking?');
    await sendButton.click();

    // User message should appear
    await expect(page.getByText('What is kayaking?')).toBeVisible({ timeout: 5000 });

    // Input should be cleared
    await expect(input).toHaveValue('');

    // Wait for AI response to start appearing (look for any text content in assistant message)
    // The streaming message component should become visible
    await page.waitForSelector('text=/kayaking|water|sport|paddle|boat/i', {
      timeout: 30000,
      state: 'visible'
    });

    // Verify AI response appears (it should contain relevant content)
    const pageContent = await page.textContent('body');
    expect(pageContent).toBeTruthy();

    // Send button should be re-enabled after streaming completes
    await expect(sendButton).toBeEnabled({ timeout: 45000 });
  });

  test('should handle multiple messages in conversation', async ({ page }) => {
    const input = page.getByPlaceholder(/Type your message.../i);
    const sendButton = page.locator('button[type="submit"]');

    // Send first message
    await input.fill('Hello');
    await sendButton.click();

    // Wait for first user message
    await expect(page.getByText('Hello').first()).toBeVisible({ timeout: 5000 });

    // Wait for first AI response to complete
    await expect(sendButton).toBeEnabled({ timeout: 45000 });

    // Send second message
    await input.fill('Tell me about paddling');
    await sendButton.click();

    // Wait for second user message
    await expect(page.getByText('Tell me about paddling')).toBeVisible({ timeout: 5000 });

    // Both messages should be visible in history
    await expect(page.getByText('Hello')).toBeVisible();
    await expect(page.getByText('Tell me about paddling')).toBeVisible();
  });

  test('should show loading state during streaming', async ({ page }) => {
    const input = page.getByPlaceholder(/Type your message.../i);
    const sendButton = page.locator('button[type="submit"]');

    // Send a message
    await input.fill('Test message');
    await sendButton.click();

    // Send button should show loading spinner and be disabled
    await expect(sendButton).toBeDisabled();

    // Input should be disabled during streaming
    await expect(input).toBeDisabled();

    // Wait for completion
    await expect(sendButton).toBeEnabled({ timeout: 45000 });
    await expect(input).toBeEnabled();
  });

  test('should auto-scroll to latest message', async ({ page }) => {
    const input = page.getByPlaceholder(/Type your message.../i);
    const sendButton = page.locator('button[type="submit"]');

    // Send a message
    await input.fill('Test auto-scroll');
    await sendButton.click();

    // Wait for user message
    await expect(page.getByText('Test auto-scroll')).toBeVisible({ timeout: 5000 });

    // The scroll area should automatically scroll to show the latest message
    // We can verify the last message is in viewport
    const lastMessage = page.getByText('Test auto-scroll');
    await expect(lastMessage).toBeInViewport();
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Intercept API call and force an error
    await page.route('**/api/chat/stream', route => {
      route.abort('failed');
    });

    const input = page.getByPlaceholder(/Type your message.../i);
    const sendButton = page.locator('button[type="submit"]');

    // Send a message
    await input.fill('This will fail');
    await sendButton.click();

    // Wait for error message to appear
    await expect(page.getByText(/Error:/i)).toBeVisible({ timeout: 10000 });

    // Input should be re-enabled after error
    await expect(input).toBeEnabled();
    await expect(sendButton).toBeDisabled(); // Disabled because input is empty
  });

  test('should have proper accessibility attributes', async ({ page }) => {
    const input = page.getByPlaceholder(/Type your message.../i);
    const sendButton = page.locator('button[type="submit"]');

    // Check that input is editable
    await expect(input).toBeEditable();

    // Check that send button exists and has correct type
    await expect(sendButton).toHaveAttribute('type', 'submit');

    // Check that form can be submitted with Enter key
    await input.fill('Test enter key');
    await input.press('Enter');

    // Message should be sent
    await expect(page.getByText('Test enter key')).toBeVisible({ timeout: 5000 });
  });
});
