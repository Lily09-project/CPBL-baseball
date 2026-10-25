import { expect, expectAccessible, openRoute, test } from "./fixtures";

test.describe("Q4/Q5 navigation, keyboard and accessibility", () => {
  test("the whole site can be driven by keyboard: skip link, nav, palette search", async ({ page }) => {
    await openRoute(page, "/");
    await page.keyboard.press("Tab");
    await expect(page.getByText("跳到主要內容")).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("main")).toBeFocused();

    await page.keyboard.press("Control+k");
    const input = page.getByRole("combobox", { name: "輸入球員或球隊名稱" });
    await expect(input).toBeFocused();
    await input.fill("郭天信");
    await expect(page.getByRole("listbox", { name: "搜尋結果" }).getByRole("option").first()).toContainText("郭天信");
    await page.keyboard.press("Enter");
    await expect(page.locator("h1")).toHaveText("郭天信");
    await expect(page).toHaveURL(/#\/player\/batter\/0000005549/);

    await page.keyboard.press("/");
    await expect(page.getByRole("combobox", { name: "輸入球員或球隊名稱" })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeHidden();
  });

  test("navigation links move focus to the new page and mark the current page", async ({ page }) => {
    await openRoute(page, "/");
    const nav = page.getByRole("navigation", { name: "主要頁面" });
    await nav.getByRole("link", { name: "季末模擬" }).click();
    await expect(page.locator("h1")).toHaveText("季末戰績模擬");
    await expect(nav.getByRole("link", { name: "季末模擬" })).toHaveAttribute("aria-current", "page");
    await expect(page.locator("main")).toBeFocused();
    await expect(page).toHaveTitle(/季末戰績模擬/);
  });

  test("theme choice is applied and remembered", async ({ page }) => {
    await openRoute(page, "/");
    const picker = page.getByLabel("介面主題");
    await picker.selectOption("dark");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await expectAccessible(page);
    await picker.selectOption("light");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await expectAccessible(page);
  });

  test("unknown routes render a helpful not-found page", async ({ page }) => {
    await page.goto("./#/nowhere");
    await expect(page.getByText("找不到這個頁面")).toBeVisible();
    await expectAccessible(page);
  });

  test("every chart offers an equivalent data table", async ({ page }) => {
    for (const route of ["/", "/season", "/data", "/player/batter/0000005549"]) {
      await openRoute(page, route);
      const figures = page.locator("figure.chart-frame");
      const count = await figures.count();
      expect(count, `charts on ${route}`).toBeGreaterThan(0);
      await expect(page.locator("figure.chart-frame details table")).toHaveCount(count);
    }
  });

  test("layout never scrolls horizontally", async ({ page }) => {
    for (const route of ["/", "/talent", "/lineup", "/season", "/player/batter/0000005549", "/compare?type=batter&ids=0000005549", "/data"]) {
      await openRoute(page, route);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `horizontal overflow on ${route}`).toBeLessThanOrEqual(0);
    }
  });
});

test.describe("Q6 performance and Q8 security", () => {
  test("main content appears within 1.5 s and no third-party request is made", async ({ page }) => {
    const hosts = new Set<string>();
    page.on("request", (r) => hosts.add(new URL(r.url()).host));
    const start = Date.now();
    await page.goto("./");
    await expect(page.locator("main h1")).toBeVisible();
    expect(Date.now() - start).toBeLessThan(1500);
    await page.waitForLoadState("networkidle");
    expect([...hosts]).toEqual([new URL(page.url()).host]);
  });

  test("a strict Content-Security-Policy is declared", async ({ page }) => {
    await page.goto("./");
    const csp = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute("content");
    expect(csp).toContain("script-src 'self'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).not.toContain("unsafe-eval");
  });
});
