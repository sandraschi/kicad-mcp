import { defineConfig } from '@playwright/test';

export default defineConfig({
    testDir: './e2e',
    timeout: 60000,
    retries: 1,
    use: {
        baseURL: 'http://localhost:11017',
        headless: true,
        screenshot: 'only-on-failure',
    },
    webServer: {
        command: 'uv run python -m kicad_mcp.server --mode dual --port 11016',
        port: 11016,
        cwd: '../',
        timeout: 30000,
        reuseExistingServer: false,
    },
});
