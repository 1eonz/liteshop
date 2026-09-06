import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './specs',
  use: { baseURL: 'http://127.0.0.1:5173' },
  reporter: [['list']],
  webServer: {
    command: 'F:/work/liteshop/node_modules/.bin/vite.cmd --host 127.0.0.1 --port 5173',
    cwd: '../../packages/h5-app',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
