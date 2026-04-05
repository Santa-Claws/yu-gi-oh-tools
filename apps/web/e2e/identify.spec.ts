import { test, expect } from "@playwright/test";

test("identify page loads and shows dropzone", async ({ page }) => {
  await page.goto("/identify");
  await expect(page.getByText("Identify a Card")).toBeVisible();
  await expect(page.getByText("Drag and drop a card image")).toBeVisible();
});

test("identify by text search", async ({ page }) => {
  await page.goto("/identify");
  await page.getByPlaceholder("Card name or description text...").fill("Blue-Eyes");
  await page.getByRole("button", { name: "Search" }).click();
  // Results or loading state should appear
  await expect(page.locator("body")).not.toContainText("Error");
});
