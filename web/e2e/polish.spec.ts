import { expect, openRoute, test } from "./fixtures";

test("the other pages' code is fetched while idle, so the first menu click needs no download", async ({ page }) => {
  const season = page.waitForRequest(/assets\/Season-[^/]+\.js/);
  await openRoute(page, "/");
  await (await season).response();
  // The page counts as loaded once its shared chunks and CSS have arrived too.
  await page.waitForLoadState("networkidle");
  // Watch the whole switch: the 頁面載入中 placeholder should never be drawn.
  await page.evaluate(() => {
    const w = window as unknown as { sawPlaceholder: boolean };
    w.sawPlaceholder = false;
    new MutationObserver(() => {
      if (document.querySelector("main")?.textContent?.includes("頁面載入中")) w.sawPlaceholder = true;
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  });
  await page.getByRole("navigation").getByRole("link", { name: "季末模擬" }).click();
  await expect(page.locator("main h1").first()).toHaveText("季末戰績模擬");
  expect(await page.evaluate(() => (window as unknown as { sawPlaceholder: boolean }).sawPlaceholder)).toBe(false);
});

test("teams that never finish first get no bar sliver and step back visually", async ({ page }) => {
  await openRoute(page, "/season");
  const rows = page.getByTestId("title-odds").locator("li");
  await expect(rows).toHaveCount(6);
  for (const row of await rows.all()) {
    const zero = (await row.locator(".prob-value").innerText()).trim() === "0.0%";
    if (zero) {
      await expect(row).toHaveClass(/prob-out/);
      await expect(row.locator(".prob-track span")).toBeHidden();
    } else {
      await expect(row).not.toHaveClass(/prob-out/);
    }
  }
});

test("the qualified-only check box keeps its label on one line on wide screens", async ({ page }) => {
  test.skip((page.viewportSize()?.width ?? 0) < 1000, "wide layout only");
  await openRoute(page, "/talent?type=batter");
  const label = page.locator(".controls > .check");
  const box = await label.boundingBox();
  expect(box!.height).toBeLessThan(48);
});

test("icons decorate the front page without changing what assistive tech reads", async ({ page }) => {
  await openRoute(page, "/");
  const icons = page.locator("svg.icon");
  expect(await icons.count()).toBeGreaterThanOrEqual(10);
  for (const icon of await icons.all()) await expect(icon).toHaveAttribute("aria-hidden", "true");
  await expect(page.getByRole("button", { name: "搜尋球員" })).toBeVisible();
  await expect(page.getByRole("link", { name: "開始模擬打線" })).toBeVisible();
  await expect(page.locator(".story-icon")).toHaveCount(4);
});

test("on phones, player-name links in lists are full 44px tap targets", async ({ page }) => {
  test.skip((page.viewportSize()?.width ?? 1440) > 640, "phone layout only");
  await openRoute(page, "/talent?type=batter");
  const trap = page.getByTestId("traps").locator("a").first();
  await expect(trap).toBeVisible();
  expect((await trap.boundingBox())!.height).toBeGreaterThanOrEqual(44);

  await trap.click();
  const similar = page.getByTestId("similar-players").locator(".similar-head a").first();
  if ((await similar.count()) > 0) expect((await similar.boundingBox())!.height).toBeGreaterThanOrEqual(44);
});
