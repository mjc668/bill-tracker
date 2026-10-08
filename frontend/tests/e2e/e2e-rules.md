# E2E Testing Rules — Hearthbill

## Locator strategy
- Use `getByRole`, `getByLabel`, `getByText` as primary locators.
- Fall back to `getByTestId` only when accessibility attributes are ambiguous.
- Never use CSS selectors, XPath, or DOM structure.

## Test isolation
- Each test must be independently runnable — no shared state between tests.
- Each test creates its own user via `loginNewUser(page)` (API call, not UI login).
- Use `Date.now()` in test data names to avoid collisions in parallel runs.

## Waiting
- Never use `page.waitForTimeout()`.
- Wait for specific states: `toBeVisible()`, `waitForURL()`, `waitForResponse()`.

## Assertions
- Assert the business outcome, not implementation details.
- Every assertion must fail if its named risk materializes.

## Auth
- Authenticate via `page.request.post()` to the backend API — never log in
  through the UI in individual tests (except flow 1 which tests the register UI).
- The `loginNewUser()` helper in `helpers.ts` handles auth setup.

## Real vs mocked
- Internal boundaries (auth, routing, DB) stay real.
- External SMTP is not available in test environments; the forgot-password test
  verifies UI flow only and mocks the reset-password API call.
