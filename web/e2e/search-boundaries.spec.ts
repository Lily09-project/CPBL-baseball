import { expect, expectAccessible, openRoute, test } from "./fixtures";

test("player search distinguishes loading from an empty result and recovers", async ({ page }) => {
  let release = () => {};
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let arrived = () => {};
  const requested = new Promise<void>((resolve) => { arrived = resolve; });
  let done = () => {};
  const finished = new Promise<void>((resolve) => { done = resolve; });
  await page.route("**/data/players.json", async (route) => {
    arrived();
    try {
      await gate;
      await route.continue();
    } finally { done(); }
  });
  await openRoute(page, "/");
  await page.getByRole("button", { name: "搜尋球員" }).click();
  await requested;
  const dialog = page.getByRole("dialog", { name: "搜尋球員" });
  await dialog.getByRole("combobox").fill("郭");
  try {
    await expect(dialog.getByRole("status")).toContainText("正在載入球員資料");
    await expect(dialog.getByText(/找不到符合/)).toHaveCount(0);
  } finally {
    release();
    await finished;
  }
  await expect(dialog.getByRole("option").first()).toBeVisible();
  await expect(dialog.getByRole("status")).toHaveCount(0);
  await expectAccessible(page);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
});

test("a rejected player index is an error, not an empty search result", async ({ page }) => {
  await page.route("**/data/players.json", (route) => route.fulfill({
    status: 200, contentType: "application/json", body: "[]",
  }));
  await openRoute(page, "/");
  const search = page.getByRole("button", { name: "搜尋球員" });
  await search.click();
  const dialog = page.getByRole("dialog", { name: "搜尋球員" });
  await dialog.getByRole("combobox").fill("郭");
  await expect(dialog.getByRole("alert")).toContainText("無法載入球員資料");
  await expect(dialog.getByRole("alert")).toContainText("重新整理");
  await expect(dialog.getByText(/找不到符合/)).toHaveCount(0);
  await expect(dialog.getByRole("option")).toHaveCount(0);
  await expectAccessible(page);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(search).toBeFocused();
});
