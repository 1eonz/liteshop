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
  ],
});
