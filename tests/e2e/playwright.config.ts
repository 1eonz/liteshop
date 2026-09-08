import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './specs',
  use: { baseURL: 'http://127.0.0.1:5173' },
  reporter: [['list']],
  webServer: [
    {
      command: 'pnpm exec vite --host 127.0.0.1 --port 5173',
      cwd: '../../packages/h5-app',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: 'pnpm exec vite --host 127.0.0.1 --port 5174',
      cwd: '../../packages/admin-app',
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: 'pnpm exec next dev --hostname 127.0.0.1 --port 5175',
      cwd: '../../packages/site-app',
      env: { REVALIDATE_TOKEN: 'e2e-revalidate-token' },
      url: 'http://127.0.0.1:5175',
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
