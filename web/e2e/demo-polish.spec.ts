import { expect, fetchJson, openRoute, test } from "./fixtures";

interface IndexedPlayer {
  player_id: string;
  name: string;
  team: string;
  type: "batter" | "pitcher";
  trials: number;
  qualified: boolean;
}

const TEAM = encodeURIComponent("中信兄弟");

test("unknown lineup ids are reported and filled from the selected team", async ({ page }) => {
  await openRoute(page, `/lineup?team=${TEAM}`);
  const slots = page.getByTestId("lineup-slots").locator("select");
  await expect(slots).toHaveCount(9);
  const teamDefault = await slots.evaluateAll((nodes) => nodes.map((n) => (n as HTMLSelectElement).value));

  await page.goto(`./#/lineup?team=${TEAM}&ids=1,2,3`);
  await expect(page.getByRole("status").filter({ hasText: "網址中有 3 個球員代碼找不到" })).toBeVisible();
  await expect(page.getByLabel("以球隊預設打線填入")).toHaveValue("中信兄弟");
  expect(await slots.evaluateAll((nodes) => nodes.map((n) => (n as HTMLSelectElement).value))).toEqual(teamDefault);
});

test("the A/B comparison copies its URL and lays the two histograms out at a readable size", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: (text: string) => { (window as unknown as { copied: string }).copied = text; return Promise.resolve(); } },
    });
  });
  await openRoute(page, "/lineup");
  await page.getByRole("button", { name: "儲存為 A" }).click();
  await page.getByRole("button", { name: "複製 A 到 B" }).click();
  await page.getByRole("button", { name: "複製比較網址" }).click();
  await expect(page.getByRole("status").filter({ hasText: "已複製比較網址" })).toBeVisible();
  const copied = await page.evaluate(() => (window as unknown as { copied: string }).copied);
  expect(copied).toMatch(/^http.*#\/lineup\?.*snapshot=.*&a=.*&b=/);

  await page.getByRole("button", { name: "比較兩組打線" }).click();
  const result = page.getByTestId("paired-lineup-result");
  await expect(result).toContainText("95% 配對模擬區間");
  const boxes = await result.locator(".ab-hist").evaluateAll((nodes) => nodes.map((n) => n.getBoundingClientRect().toJSON() as DOMRect));
  expect(boxes).toHaveLength(2);
  for (const box of boxes) expect(box.width).toBeLessThanOrEqual(561);
  const wide = (page.viewportSize()?.width ?? 0) > 760;
  if (wide) expect(Math.abs(boxes[0]!.y - boxes[1]!.y)).toBeLessThan(2);
  else expect(boxes[1]!.y).toBeGreaterThan(boxes[0]!.y + boxes[0]!.height - 1);
});

test("without clipboard access the comparison URL is offered in a selected field", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: undefined });
  });
  await openRoute(page, "/lineup");
  await page.getByRole("button", { name: "儲存為 A" }).click();
  await page.getByRole("button", { name: "複製 A 到 B" }).click();
  await page.getByRole("button", { name: "複製比較網址" }).click();
  const field = page.getByLabel("無法自動複製，請手動複製這個網址");
  await expect(field).toHaveValue(/#\/lineup\?.*&a=.*&b=/);
  await expect(field).toBeFocused();
});

test("the small-sample sidebar follows the name filter", async ({ page }) => {
  await openRoute(page, `/talent?type=batter&q=${encodeURIComponent("陳")}`);
  const traps = page.getByTestId("traps");
  await expect(traps).toContainText("名字含「陳」");
  const names = await traps.locator("li a").allInnerTexts();
  expect(names.length).toBeGreaterThan(0);
  for (const name of names) expect(name).toContain("陳");
});

test("on phones the talent table keeps the estimate columns on screen", async ({ page }) => {
  test.skip((page.viewportSize()?.width ?? 1440) > 560, "phone layout only");
  await openRoute(page, "/talent");
  const table = page.getByTestId("talent-table");
  await expect(table.getByRole("columnheader", { name: "球隊" })).toBeHidden();
  const header = await table.getByRole("columnheader", { name: "收縮後" }).boundingBox();
  const width = page.viewportSize()!.width;
  expect(header!.x + header!.width).toBeLessThanOrEqual(width);
  const link = await table.locator("tbody th a").first().boundingBox();
  expect(link!.height).toBeGreaterThanOrEqual(44);
});

test("a pitcher's page links to the lineup lab with that pitcher selected", async ({ page }) => {
  await openRoute(page, "/");
  const players = await fetchJson<IndexedPlayer[]>(page, "players.json");
  const pitcher = players.filter((p) => p.type === "pitcher" && p.qualified).sort((a, b) => b.trials - a.trials)[0]!;
  await page.goto(`./#/player/pitcher/${pitcher.player_id}`);
  await page.getByRole("link", { name: "在打線實驗室模擬" }).click();
  await expect(page).toHaveURL(new RegExp(`pitcher=${pitcher.player_id}`));
  await expect(page.getByLabel("對手投手")).toHaveValue(pitcher.player_id);
});

test("search says how many more players match when the list is cut at eight", async ({ page }) => {
  await openRoute(page, "/");
  await page.getByRole("button", { name: "搜尋球員" }).click();
  const dialog = page.getByRole("dialog", { name: "搜尋球員" });
  await dialog.getByRole("combobox").fill("兄弟");
  await expect(dialog.getByRole("option")).toHaveCount(8);
  await expect(dialog.getByTestId("palette-more")).toHaveText(/^還有 \d+ 筆，請輸入更多字。$/);
});

test("an empty comparison says nothing is selected yet, not that data is missing", async ({ page }) => {
  await openRoute(page, "/compare?type=batter");
  await expect(page.locator(".state-kicker")).toHaveText("尚未選擇");
});
