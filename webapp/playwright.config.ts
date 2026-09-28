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
    webServer: [
        {
            command: 'uv run python -m kicad_mcp.server --mode dual --port 11016',
            port: 11016,
            cwd: '../',
            timeout: 30000,
            reuseExistingServer: false,
        },
        {
            // baseURL points at the frontend (11017), but nothing started it --
            // only the backend (11016) had a webServer entry, so every spec that
            // navigates via page.goto() got net::ERR_CONNECTION_REFUSED in CI.
            command: 'npx vite --port 11017',
            port: 11017,
            timeout: 30000,
            reuseExistingServer: false,
        },
    ],
});
