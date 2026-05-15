import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// WCAG 2.1 AA accessibility audit — Task 12.19
// Run with: npx playwright test e2e/accessibility.spec.ts

async function mockAuth(page: Parameters<typeof test>[1] extends (args: { page: infer P }) => unknown ? P : never) {
  await page.addInitScript(() => {
    localStorage.setItem(
      "acrqa-auth",
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

test.describe("WCAG 2.1 AA — Scans page", () => {
  test("has no critical/serious axe violations", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    const serious = results.violations.filter((v) =>
      ["critical", "serious"].includes(v.impact ?? "")
    );
    expect(serious, `Axe violations: ${JSON.stringify(serious.map((v) => ({ id: v.id, impact: v.impact, help: v.help })), null, 2)}`).toHaveLength(0);
  });

  test("nav landmark exists", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    await expect(page.getByRole("navigation")).toBeVisible();
  });

  test("main landmark exists", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    await expect(page.getByRole("main")).toBeVisible();
  });

  test("dark-mode toggle has accessible label", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    const btn = page.getByRole("button", { name: /switch to (dark|light) mode/i });
    await expect(btn).toBeVisible();
    await expect(btn).toHaveAttribute("aria-label");
  });

  test("sign-out button has accessible label", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    const btn = page.getByRole("button", { name: /sign out/i });
    await expect(btn).toBeVisible();
  });

  test("language toggle has accessible label", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    const btn = page.getByRole("button", { name: /switch to arabic|switch to english/i });
    await expect(btn).toBeVisible();
  });
});

test.describe("WCAG 2.1 AA — Settings page", () => {
  test("has no critical/serious axe violations", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ status: 200, json: {} }));
    await page.goto("/settings");
    await page.waitForLoadState("networkidle");

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    const serious = results.violations.filter((v) =>
      ["critical", "serious"].includes(v.impact ?? "")
    );
    expect(serious, `Axe violations: ${JSON.stringify(serious.map((v) => ({ id: v.id, impact: v.impact, help: v.help })), null, 2)}`).toHaveLength(0);
  });
});

test.describe("Mobile viewport — 375px", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("layout renders without overflow at 375px", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    const body = page.locator("body");
    const box = await body.boundingBox();
    expect(box?.width).toBeLessThanOrEqual(375);
  });

  test("header is visible at 375px", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    await expect(page.getByRole("banner")).toBeVisible();
  });

  test("nav links exist at 375px", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    await expect(page.getByRole("navigation")).toBeVisible();
  });
});

test.describe("RTL — Arabic language", () => {
  test("language toggle switches dir to rtl", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    await page.getByRole("button", { name: /switch to arabic/i }).click();
    const dir = await page.locator("html").getAttribute("dir");
    expect(dir).toBe("rtl");
  });

  test("switching back to English sets dir ltr", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto("/");
    await page.getByRole("button", { name: /switch to arabic/i }).click();
    await page.getByRole("button", { name: /switch to english/i }).click();
    const dir = await page.locator("html").getAttribute("dir");
    expect(dir).toBe("ltr");
  });
});
