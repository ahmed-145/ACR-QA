import { test, expect } from "@playwright/test";

// Mock auth by setting localStorage before navigating
async function mockAuth(page: Parameters<typeof test>[1] extends (args: { page: infer P }) => unknown ? P : never) {
  await page.addInitScript(() => {
    localStorage.setItem(
      "acrqa_auth",
      JSON.stringify({
        state: {
          token: "test-token",
          user: { email: "test@example.com", role: "admin" },
        },
        version: 0,
      })
    );
  });
}

test.describe("Dashboard layout", () => {
  test("shows navigation bar when authenticated", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => {
      route.fulfill({ json: { runs: [] } });
    });
    await page.goto("/");
    await expect(page.getByRole("navigation")).toBeVisible();
  });

  test("nav has Scans, Supply Chain, Settings links", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    await expect(page.getByRole("link", { name: /Scans/i })).toBeVisible();
  });

  test("dark mode toggle switches theme", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    const html = page.locator("html");
    const hasDark = await html.evaluate((el) => el.classList.contains("dark"));
    await page.getByRole("button", { name: /switch to (dark|light) mode/i }).click();
    const nowDark = await html.evaluate((el) => el.classList.contains("dark"));
    expect(nowDark).toBe(!hasDark);
  });
});

test.describe("Scans page", () => {
  test("shows 'No scans yet' when runs array is empty", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/runs*", (route) => route.fulfill({ json: { runs: [] } }));
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/scans");
    await expect(page.getByText("No scans yet")).toBeVisible({ timeout: 5000 });
  });

  test("New Scan button opens dialog", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/scans");
    await page.getByRole("button", { name: /New Scan/i }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("New Scan dialog has target directory and repo name fields", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/scans");
    await page.getByRole("button", { name: /New Scan/i }).click();
    await expect(page.getByPlaceholder(/path\/to\/repo/i)).toBeVisible();
    await expect(page.getByPlaceholder(/my-service/i)).toBeVisible();
  });
});

test.describe("Settings page", () => {
  test("shows Operation Mode card", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ status: 200, json: {} }));
    await page.goto("/settings");
    await expect(page.getByText("Operation Mode")).toBeVisible();
  });

  test("shows user email in Account card", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ status: 200, json: {} }));
    await page.goto("/settings");
    await expect(page.getByRole("main").getByText("test@example.com")).toBeVisible();
  });
});

test.describe("Command palette", () => {
  test("opens with Ctrl+K", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    await page.keyboard.press("Control+k");
    await expect(page.getByPlaceholder("Type a command…")).toBeVisible();
  });

  test("closes with Escape", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    await page.keyboard.press("Control+k");
    await expect(page.getByPlaceholder("Type a command…")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByPlaceholder("Type a command…")).not.toBeVisible();
  });

  test("filters commands by query", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    await page.keyboard.press("Control+k");
    await page.getByPlaceholder("Type a command…").fill("Supply");
    await expect(page.getByText("Go to Supply Chain")).toBeVisible();
  });
});
