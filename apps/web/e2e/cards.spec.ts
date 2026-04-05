import { test, expect } from "@playwright/test";

test("cards page loads", async ({ page }) => {
  await page.goto("/cards");
  await expect(page.getByText("Cards")).toBeVisible();
});

test("card filter by type", async ({ page }) => {
  await page.goto("/cards");
  await page.selectOption("select[name=card_type]", "monster");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.locator("body")).not.toContainText("Error");
});
