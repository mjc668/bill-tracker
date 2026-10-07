/**
 * Flow 15: Unarchive a bill → returns to the active list
 * Risk: after a successful unarchive the bill stays on the archived page (or
 *       never reappears on the active list), so the user believes it is still
 *       archived.
 * Real boundaries: auth (cookie), Bills API (POST /bills,
 *                  POST /bills/:id/archive, POST /bills/:id/unarchive),
 *                  archived/active bills pages.
 */
import { test, expect } from '@playwright/test';
import { API, loginNewUser, createBillViaApi } from './helpers';

test('unarchived bill leaves archived page and reappears on active list', async ({ page }) => {
  const billName = `E2E Unarchive ${Date.now()}`;

  // Setup: authenticate + create a bill via API
  await loginNewUser(page);
  const billId = await createBillViaApi(page, billName);

  // Setup: archive it via API (the archive UI flow itself is covered by flow 5)
  const archiveRes = await page.request.post(`${API}/bills/${billId}/archive`);
  expect(archiveRes.ok()).toBeTruthy();

  // Step: open the archived page and confirm the row is present
  await page.goto('/dashboard/bills/archived');
  await expect(page.getByText(billName)).toBeVisible();

  // Step: click Unarchive on the row
  await page.getByRole('button', { name: 'Unarchive' }).click();

  // Assert: the row is removed from the archived list
  await expect(page.getByText(billName, { exact: true })).not.toBeVisible();

  // Assert: the bill is visible again on the active bills page
  await page.goto('/dashboard/bills');
  await expect(page.getByText(billName)).toBeVisible();
});
