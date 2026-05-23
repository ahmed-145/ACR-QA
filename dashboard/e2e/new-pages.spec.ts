import { test, expect } from "@playwright/test";

const loginAndGo = async (page: Parameters<Parameters<typeof test>[1]>[0]["page"], path: string) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(process.env.E2E_EMAIL ?? "admin@acrqa.test");
  await page.getByLabel("Password").fill(process.env.E2E_PASSWORD ?? "changeme");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/(overview|scans)/);
  await page.goto(path);
};

async function mockAuth(page: Parameters<Parameters<typeof test>[1]>[0]["page"]) {
  await page.addInitScript(() => {
    localStorage.setItem(
      "acrqa_auth",
      JSON.stringify({
        state: { token: "test-token", user: { email: "test@example.com", role: "admin" } },
        version: 0,
      })
    );
  });
}

test.describe("Landing Page", () => {
  test("renders hero section", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Automated Code Review")).toBeVisible();
  });

  test("renders feature cards", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Multi-Tool SAST")).toBeVisible();
    await expect(page.getByText("AI Explainer")).toBeVisible();
    await expect(page.getByText("ECDSA Attestation")).toBeVisible();
  });

  test("renders stats bar", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Detection Rules")).toBeVisible();
    await expect(page.getByText("327")).toBeVisible();
  });

  test("sign-in link navigates to login", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Sign in" }).first().click();
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("Overview Page (authenticated)", () => {
  test("renders Security Overview heading", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/overview");
    await expect(page.getByText("Security Overview")).toBeVisible();
  });

  test("has bento grid or empty state", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/overview");
    const bento = page.locator(".bento-grid, .empty");
    await expect(bento.first()).toBeVisible();
  });
});

test.describe("All Findings Page (authenticated)", () => {
  test("renders page heading", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/findings");
    await expect(page.getByRole("heading", { name: "All Findings" })).toBeVisible();
  });

  test("has search input", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/findings");
    await expect(page.getByPlaceholder(/search rules/i)).toBeVisible();
  });

  test("has severity filter buttons", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/findings");
    await expect(page.getByRole("button", { name: "HIGH" })).toBeVisible();
    await expect(page.getByRole("button", { name: "MEDIUM" })).toBeVisible();
    await expect(page.getByRole("button", { name: "LOW" })).toBeVisible();
  });
});

test.describe("Repos Page (authenticated)", () => {
  test("renders page heading", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/repos");
    await expect(page.getByRole("heading", { name: "Repositories" })).toBeVisible();
  });
});

test.describe("Cost & ROI Page (authenticated)", () => {
  test("renders page heading", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/cost");
    await expect(page.getByRole("heading", { name: "Cost & ROI" })).toBeVisible();
  });

  test("shows ROI formula section", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/cost");
    await expect(page.getByText("How ROI Is Calculated")).toBeVisible();
  });
});

test.describe("Rules Browser (authenticated)", () => {
  test("renders page heading", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/rules");
    await expect(page.getByRole("heading", { name: "Rules Browser" })).toBeVisible();
  });

  test("has search input", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/rules");
    await expect(page.getByPlaceholder(/search canonical/i)).toBeVisible();
  });
});

test.describe("Policy Page (authenticated)", () => {
  test("renders page heading", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.route("/v1/policy", (route) => route.fulfill({
      json: {
        success: true, config_file: ".acrqa.yml", is_valid: true,
        errors: [], warnings: [], schema_keys: [],
        active_policy: {
          disabled_rules: [], severity_overrides: {}, ignored_paths: [],
          min_severity: "low",
          quality_gate: { max_high: 0, max_medium: 5, max_total: 20, max_security: 0 },
          autofix: { enabled: false, min_confidence: 0.8 },
          ai_explanations: { enabled: true, max_explanations: 10 },
        },
      },
    }));
    await page.goto("/policy");
    await expect(page.getByRole("heading", { name: "Policy Configuration" })).toBeVisible();
  });
});

test.describe("Run Detail new tabs (authenticated)", () => {
  test("run detail has Summary tab", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/runs/1");
    const summaryTab = page.getByRole("button", { name: "Summary" });
    await expect(summaryTab).toBeVisible();
  });

  test("run detail has Attestation tab", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/runs/1");
    const attTab = page.getByRole("button", { name: "Attestation" });
    await expect(attTab).toBeVisible();
  });
});

test.describe("Fleet Page (authenticated)", () => {
  test("renders Fleet Posture heading", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/fleet");
    await expect(page.getByRole("heading", { name: "Fleet Posture" })).toBeVisible();
  });

  test("has heatmap tab", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/fleet");
    await expect(page.getByRole("tab", { name: /heatmap/i })).toBeVisible();
  });
});

test.describe("Workbench Page (authenticated)", () => {
  test("renders Workbench heading", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/workbench");
    await expect(page.getByRole("heading", { name: "Workbench" })).toBeVisible();
  });

  test("has Query tab", async ({ page }) => {
    await mockAuth(page);
    await page.route("/v1/**", (route) => route.fulfill({ json: {} }));
    await page.goto("/workbench");
    await expect(page.getByRole("tab", { name: /query/i })).toBeVisible();
  });
});

test.describe("Trust Page (public)", () => {
  test("shows loading or error for unknown repo", async ({ page }) => {
    await page.route("/v1/trust/**", (route) =>
      route.fulfill({ status: 404, json: { detail: "No completed scans found" } })
    );
    await page.goto("/trust/unknown-repo");
    // Should render the trust page shell (no auth required)
    await expect(page.locator(".trust-page")).toBeVisible();
  });

  test("does not require authentication", async ({ page }) => {
    await page.route("/v1/trust/**", (route) =>
      route.fulfill({ status: 404, json: { detail: "No completed scans found" } })
    );
    // No mockAuth — visiting as unauthenticated user
    await page.goto("/trust/my-repo");
    // Should NOT redirect to /login
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.locator(".trust-page")).toBeVisible();
  });
});
