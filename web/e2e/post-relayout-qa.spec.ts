import { expect, fetchJson, openRoute, test } from "./fixtures";

interface IndexedPlayer {
  player_id: string;
  type: "batter" | "pitcher";
  trials: number;
}

test.describe("post-relayout QA: keyboard focus survives actions that redraw the control", () => {
  test("a moved batter keeps focus on its move button, also at the ends of the order", async ({ page }) => {
    await openRoute(page, "/lineup");
    const slots = page.getByTestId("lineup-slots").locator("li");
    await expect(slots).toHaveCount(9);
    const second = await slots.nth(1).locator("select").inputValue();

    await slots.nth(1).getByRole("button", { name: /往後一棒/ }).focus();
    await page.keyboard.press("Enter");
    await expect(slots.nth(2).locator("select")).toHaveValue(second);
    await expect(slots.nth(2).getByRole("button", { name: /往後一棒/ })).toBeFocused();

    await slots.nth(1).getByRole("button", { name: /往前一棒/ }).focus();
    await page.keyboard.press("Enter");
    // Slot 1 cannot move further up, so focus lands on its remaining enabled arrow.
    await expect(slots.nth(0).getByRole("button", { name: /往前一棒/ })).toBeDisabled();
    await expect(slots.nth(0).getByRole("button", { name: /往後一棒/ })).toBeFocused();
  });

  test("cancelling a running order search returns focus to the run button", async ({ page }) => {
    await openRoute(page, "/lineup");
    await expect(page.getByTestId("lineup-slots").locator("li")).toHaveCount(9);
    await page.getByRole("button", { name: "搜尋更好的棒次" }).click();
    const cancel = page.getByRole("button", { name: "取消" });
    await cancel.focus();
    await page.keyboard.press("Enter");
    await expect(cancel).toHaveCount(0);
    await expect(page.getByRole("button", { name: /^模擬 .+ 場$/ })).toBeFocused();
    await expect(page.getByTestId("order-search")).toHaveCount(0);
  });

  test("removing a compared player moves focus to the add-player menu", async ({ page }) => {
    await openRoute(page, "/compare?type=batter&ids=0000005549");
    await page.getByRole("button", { name: /從比較中移除/ }).click();
    await expect(page.getByTestId("compare-grid")).toHaveCount(0);
    await expect(page.getByLabel("加入球員")).toBeFocused();
  });
});

test.describe("post-relayout QA: talent filters and boundary players", () => {
  test("the qualifier toggle is kept in the URL across navigation, and an unknown team falls back to the league", async ({ page }) => {
    await openRoute(page, "/talent");
    const toggle = page.getByLabel("只看達比較門檻");
    await toggle.uncheck();
    await expect(page).toHaveURL(/all=1/);
    const table = page.getByTestId("talent-table");
    await expect(table.locator("tbody tr").first()).toBeVisible();

    await table.locator("tbody a").first().click();
    await expect(page.getByTestId("raw-stats")).toBeVisible();
    await page.goBack();
    await expect(toggle).not.toBeChecked();
    await toggle.check();
    await expect(page).not.toHaveURL(/all=/);

    await page.goto("./#/talent?type=batter&team=%E4%B8%8D%E5%AD%98%E5%9C%A8");
    await expect(page.getByLabel("球隊", { exact: true })).toHaveValue("");
    await expect(table.locator("tbody tr").first()).toBeVisible();
    await expect(page.getByTestId("traps")).toContainText("全聯盟");
  });

  test("a batter without plate appearances shows no rates instead of .000", async ({ page }) => {
    await openRoute(page, "/");
    const players = await fetchJson<IndexedPlayer[]>(page, "players.json");
    const empty = players.find((p) => p.type === "batter" && p.trials === 0);
    test.skip(!empty, "this snapshot has no batter with zero plate appearances");
    await page.goto(`./#/player/batter/${empty!.player_id}`);
    const cells = page.getByTestId("raw-stats").locator("tbody td");
    await expect(cells).toHaveCount(12);
    await expect(cells.nth(0)).toHaveText("0");
    for (const index of [8, 9, 10, 11]) await expect(cells.nth(index)).toHaveText("—");
    await expect(page.getByTestId("scouting-notes").locator("li")).toHaveCount(1);
    await expect(page.locator("main")).not.toContainText(/NaN|undefined|-0\.0/);
  });

  test("an unknown player id keeps a page heading", async ({ page }) => {
    await page.goto("./#/player/batter/9999999999");
    await expect(page.locator("main h1")).toHaveText("球員檔案");
    await expect(page.getByText("找不到這位球員")).toBeVisible();
  });

  test("four-up front-page rows never leave a single orphan on a tablet", async ({ page }) => {
    for (const width of [768, 1024]) {
      await page.setViewportSize({ width, height: 900 });
      await openRoute(page, "/");
      await expect(page.getByTestId("standings")).toBeVisible();
      for (const selector of [".kpis > .kpi", ".story-list > li"]) {
        const tops = await page.locator(selector).evaluateAll((nodes) => nodes.map((node) => Math.round(node.getBoundingClientRect().top)));
        const rows = [...new Set(tops)].map((top) => tops.filter((value) => value === top).length);
        expect(rows.every((count) => count === rows[0]), `${selector} at ${width}px: ${rows.join("+")}`).toBe(true);
      }
    }
  });
});


test("a changed deployment blocks a mixed player comparison and offers a reload", async ({ page }) => {
  await openRoute(page, "/");
  await expect(page.getByRole("link", { name: "打線實驗室", exact: true }).first()).toBeVisible();
  await expect(page.getByTestId("headline-insight")).toBeVisible();
  await page.route("**/data/player-details-batter.json", (route) => route.fulfill({ json: { updated: true } }));
  await page.route("**/data/manifest.json", async (route) => {
    const response = await route.fetch();
    const manifest = await response.json();
    manifest.files["player-details-batter.json"] = "0".repeat(64);
    await route.fulfill({ response, json: manifest });
  });
  await page.evaluate(() => { window.location.hash = "/compare?type=batter&ids=0000005549"; });
  await expect(page.getByRole("alert")).toContainText("網站資料已更新");
  await expect(page.getByRole("button", { name: "重新整理" })).toBeVisible();
  await expect(page.getByTestId("compare-grid")).toHaveCount(0);
});
