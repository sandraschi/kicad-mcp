import { test, expect } from '@playwright/test';

// ── Frontend Tests ──────────────────────────────────────────────────────────

test('Dashboard loads with KPIs', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1, h2, [class*="title"]').first()).toBeVisible();
    await expect(page).toHaveURL(/\/$/);
});

test('PCB page loads', async ({ page }) => {
    await page.goto('/pcb');
    await expect(page.locator('h1, h2, [class*="title"]').first()).toBeVisible();
    await expect(page).toHaveURL(/\/pcb/);
});

test('Schematic page loads', async ({ page }) => {
    await page.goto('/schematic');
    await expect(page.locator('h1, h2, [class*="title"]').first()).toBeVisible();
    await expect(page).toHaveURL(/\/schematic/);
});

test('BOM page loads', async ({ page }) => {
    await page.goto('/bom');
    await expect(page.locator('h1, h2, [class*="title"]').first()).toBeVisible();
    await expect(page).toHaveURL(/\/bom/);
});

test('Status page loads', async ({ page }) => {
    await page.goto('/status');
    await expect(page.locator('h1, h2, [class*="title"]').first()).toBeVisible();
    await expect(page).toHaveURL(/\/status/);
});

test('Files page loads', async ({ page }) => {
    await page.goto('/files');
    await expect(page.locator('h1, h2, [class*="title"]').first()).toBeVisible();
    await expect(page).toHaveURL(/\/files/);
});

test('Marketplace page loads', async ({ page }) => {
    await page.goto('/marketplace');
    await expect(page.locator('h1, h2, [class*="title"]').first()).toBeVisible();
    await expect(page).toHaveURL(/\/marketplace/);
});

test('Library page loads', async ({ page }) => {
    await page.goto('/library');
    await expect(page.locator('h1, h2, [class*="title"]').first()).toBeVisible();
    await expect(page).toHaveURL(/\/library/);
});

// ── REST API Tests ──────────────────────────────────────────────────────────

test('GET /api/v1/status returns 200', async ({ request }) => {
    const resp = await request.get('http://localhost:11016/api/v1/status');
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.server).toBe('kicad-mcp');
});

test('GET /api/v1/tools lists tools', async ({ request }) => {
    const resp = await request.get('http://localhost:11016/api/v1/tools');
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.tools).toBeDefined();
    expect(Array.isArray(body.tools)).toBe(true);
    expect(body.count).toBeGreaterThanOrEqual(5);
});

test('POST invalid input → 404 (unknown tool)', async ({ request }) => {
    const resp = await request.post('http://localhost:11016/api/v1/control/nonexistent_tool', {
        data: {},
    });
    expect(resp.status()).toBe(404);
});

test('POST /api/v1/upload without file → 422', async ({ request }) => {
    const resp = await request.post('http://localhost:11016/api/v1/upload');
    expect(resp.status()).toBe(422);
});
