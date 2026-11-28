import { expect, openRoute, test } from "./fixtures";

test("a page file that fails to load leaves the menu and a reload button, not a blank page", async ({ page, watch }) => {
  // Block before the first load: the site prefetches every page while idle.
  await page.route(/assets\/Season-.*\.(js|css)$/, (route) => route.abort());
  await openRoute(page, "/");
  await page.getByRole("navigation").getByRole("link", { name: "季末模擬" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "頁面無法載入" })).toBeVisible();
  await expect(page.getByRole("button", { name: "重新整理" })).toBeVisible();

  // The shell is still alive: another page opens without reloading.
  await page.getByRole("navigation").getByRole("link", { name: "資料可信度" }).click();
  await expect(page.locator("main h1").first()).toHaveText("資料可信度");
  watch.errors.length = 0; // the failed requests and logged errors above are the point of this test
});
