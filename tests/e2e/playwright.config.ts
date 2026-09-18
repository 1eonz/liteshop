import { defineConfig } from '@playwright/test';

const h5Port = process.env.E2E_H5_PORT ?? '5173';
const adminPort = process.env.E2E_ADMIN_PORT ?? '5174';
const sitePort = process.env.E2E_SITE_PORT ?? '5175';

export default defineConfig({
  testDir: './specs',
  use: { baseURL: process.env.E2E_H5_BASE_URL ?? `http://127.0.0.1:${h5Port}` },
  reporter: [['list']],
  webServer: [
    {
      command: `pnpm exec vite --host 127.0.0.1 --port ${h5Port}`,
      cwd: '../../packages/h5-app',
      env: { VITE_API_BASE: process.env.E2E_API_BASE ?? 'http://127.0.0.1:8000/api/v1' },
      url: `http://127.0.0.1:${h5Port}`,
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: `pnpm exec vite --host 127.0.0.1 --port ${adminPort}`,
      cwd: '../../packages/admin-app',
      url: `http://127.0.0.1:${adminPort}`,
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: `pnpm exec next dev --hostname 127.0.0.1 --port ${sitePort}`,
      cwd: '../../packages/site-app',
      env: { REVALIDATE_TOKEN: 'e2e-revalidate-token' },
      url: `http://127.0.0.1:${sitePort}`,
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
