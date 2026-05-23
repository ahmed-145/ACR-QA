import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test("login page loads with ACR-QA title", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "ACR-QA" })).toBeVisible();
  });

  test("shows sign-in form with email and password fields", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  });

  test("shows error on invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill("bad@example.com");
    await page.getByLabel("Password").fill("wrongpass");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByText("Invalid email or password")).toBeVisible({ timeout: 5000 });
  });

  test("unauthenticated access to / shows landing page", async ({ page }) => {
    await page.goto("/");
    // Should show landing page with ACR-QA branding, not redirect
    await expect(page.getByText("Sign in").first()).toBeVisible();
  });

  test("landing page has sign-in and get-started links", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: "Sign in" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Get Started" })).toBeVisible();
  });

  test("unauthenticated access to /supply-chain redirects to /login", async ({ page }) => {
    await page.goto("/supply-chain");
    await expect(page).toHaveURL(/\/login/);
  });

  test("register page is accessible without login", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByRole("heading", { name: "Create account" })).toBeVisible();
  });

  test("register page has all required fields", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByPlaceholder("you@example.com")).toBeVisible();
    await expect(page.getByPlaceholder("Minimum 8 characters")).toBeVisible();
    await expect(page.getByPlaceholder("Repeat password")).toBeVisible();
  });

  test("register page shows error when passwords do not match", async ({ page }) => {
    await page.goto("/register");
    await page.getByPlaceholder("you@example.com").fill("test@test.com");
    await page.getByPlaceholder("Minimum 8 characters").fill("password123");
    await page.getByPlaceholder("Repeat password").fill("differentpass");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Passwords do not match")).toBeVisible();
  });
});
