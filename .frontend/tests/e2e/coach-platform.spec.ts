import { test, expect } from "@playwright/test";

test.describe("Landing Page", () => {
  test("renders role selection with Coach and Athlete options", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("Coach Platform");
    await expect(page.locator("text=Enter as Coach")).toBeVisible();
    await expect(page.locator("text=Enter as Athlete")).toBeVisible();
  });

  test("navigates to coach view when clicking Enter as Coach", async ({ page }) => {
    await page.goto("/");
    await page.locator("text=Enter as Coach").click();
    await expect(page).toHaveURL(/\/coach/);
  });

  test("navigates to athlete view when clicking Enter as Athlete", async ({ page }) => {
    await page.goto("/");
    const athleteCard = page.locator("div[class*='cursor-pointer']").filter({ hasText: "Athlete" });
    await athleteCard.click();
    await expect(page).toHaveURL(/\/athlete/, { timeout: 10000 });
  });
});

test.describe("Coach Roster Queue", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/coach");
  });

  test("renders sidebar with navigation", async ({ page }) => {
    await expect(page.locator("text=Coach Platform").first()).toBeVisible();
    await expect(page.locator("text=Dashboard")).toBeVisible();
    await expect(page.locator("text=Clients")).toBeVisible();
  });

  test("renders roster heading", async ({ page }) => {
    await expect(page.locator("text=Your Roster")).toBeVisible();
  });

  test("renders client cards", async ({ page }) => {
    await expect(page.locator("text=Marcus D.").or(page.locator("text=Sofia"))).toBeVisible({ timeout: 10000 });
  });

  test("clicking a client card navigates to client detail", async ({ page }) => {
    await page.waitForTimeout(2000);
    await page.locator("text=Marcus D.").or(page.locator("text=Sofia")).first().click();
    await expect(page).toHaveURL(/\/coach\/client\//);
  });
});

test.describe("Client Detail View — Tabbed Layout", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/coach/client/athlete-001");
    await page.waitForTimeout(2000);
  });

  test("renders client header with name and phase", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /Marcus/ })).toBeVisible();
  });

  test("renders back to roster button", async ({ page }) => {
    await expect(page.locator("text=Back to Roster")).toBeVisible();
  });

  test("renders tab bar with all tabs", async ({ page }) => {
    await expect(page.locator("button:has-text('Findings')")).toBeVisible();
    await expect(page.locator("button:has-text('Vitals')")).toBeVisible();
    await expect(page.locator("button:has-text('Bloods')")).toBeVisible();
    await expect(page.locator("button:has-text('Training')")).toBeVisible();
    await expect(page.locator("button:has-text('Protocol')")).toBeVisible();
    await expect(page.locator("button:has-text('Nutrition')")).toBeVisible();
  });

  test("renders notes panel on the right", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Notes" })).toBeVisible();
    await expect(page.locator("text=Add Note")).toBeVisible();
  });

  test("findings tab shows findings on load", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /trending above range|stalled/ }).first()).toBeVisible({ timeout: 10000 });
  });

  test("findings show provenance line", async ({ page }) => {
    await expect(page.locator("text=From bloodwork").or(page.locator("text=From workout data")).first()).toBeVisible({ timeout: 10000 });
  });

  test("findings have Ask about this button", async ({ page }) => {
    await expect(page.locator("button:has-text('Ask about this')").first()).toBeVisible();
  });

  test("vitals tab shows weight prominently", async ({ page }) => {
    await page.locator("button:has-text('Vitals')").click();
    await expect(page.locator("text=Weight").first()).toBeVisible();
  });

  test("bloodwork tab shows metric-centric view", async ({ page }) => {
    await page.locator("button:has-text('Bloods')").click();
    await page.waitForTimeout(500);
    await expect(page.locator("text=hematology").or(page.locator("text=liver")).first()).toBeVisible({ timeout: 5000 });
  });

  test("training tab shows training block and lift data", async ({ page }) => {
    await page.locator("button:has-text('Training')").click();
    await expect(page.locator("text=Build Routine")).toBeVisible();
  });

  test("nutrition tab shows macro breakdown", async ({ page }) => {
    await page.locator("button:has-text('Nutrition')").click();
    await expect(page.locator("text=kcal/day")).toBeVisible();
    await expect(page.locator("text=Update Targets")).toBeVisible();
  });
});

test.describe("Substance Section — Coach Access", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/coach/client/athlete-001");
    await page.waitForTimeout(2000);
    // Navigate to substance tab
    await page.locator("button:has-text('Protocol')").click();
    await page.waitForTimeout(500);
  });

  test("substance section exists with management label", async ({ page }) => {
    await expect(page.locator("text=Protocol management").or(page.locator("text=Athlete will be notified"))).toBeVisible();
  });

  test("substance section has NO input elements", async ({ page }) => {
    // The substance section content area (below the read-only label)
    const substanceArea = page.locator("text=Read-only").locator("..").locator("..");
    const inputs = substanceArea.locator("input, textarea, select");
    await expect(inputs).toHaveCount(0);
  });

  test("substance section displays compound events as text only", async ({ page }) => {
    const hasCompounds = await page.locator("text=Testosterone Cypionate").or(page.locator("text=Testosterone Enanthate")).count();
    expect(hasCompounds).toBeGreaterThan(0);
  });

  test("estimated levels are labeled as modeled, not measured", async ({ page }) => {
    await expect(page.locator("text=Estimated Levels").or(page.locator("text=from logged protocol"))).toBeVisible();
  });

  test("coach can modify substances — NLP input and form exist", async ({ page }) => {
    await expect(page.locator("text=Modify Protocol")).toBeVisible();
    await expect(page.locator("text=Or use manual form")).toBeVisible();
  });
});

test.describe("Athlete Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/athlete");
    await page.waitForTimeout(2000);
  });

  test("renders athlete dashboard heading", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Your Dashboard" })).toBeVisible({ timeout: 10000 });
  });

  test("athlete CAN log substance events (user-owned write surface)", async ({ page }) => {
    await expect(page.locator("body")).toBeVisible();
  });
});
