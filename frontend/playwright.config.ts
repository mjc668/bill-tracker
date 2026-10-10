import { defineConfig, devices } from '@playwright/test';

// NixOS and other FHS-less systems can point Playwright at a system Chromium
// (e.g. `nix shell nixpkgs#chromium`); CI and normal dev boxes use the
// bundled browser and leave this unset.
const chromiumPath = process.env.PLAYWRIGHT_CHROMIUM_PATH;

export default defineConfig({
  testDir: './tests/e2e',
  outputDir: './tests/test-results',
  globalTeardown: './tests/e2e/global-teardown',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'html',
  webServer: {
    command: 'docker compose -f ../docker-compose.yml up -d --wait --timeout 180 app demo-data',
    url: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3010',
    reuseExistingServer: true,
    timeout: 120_000,
  },
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3010',
    trace: 'on-first-retry',
    actionTimeout: 15000,
    // The PWA service worker proxies same-origin fetches, which bypasses
    // page.route mocks once it takes control; tests must not race that.
    serviceWorkers: 'block',
    launchOptions: chromiumPath ? { executablePath: chromiumPath } : {},
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
