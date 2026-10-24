import { readFile } from "node:fs/promises";
import { expect, expectAccessible, fetchJson, openRoute, test } from "./fixtures";

interface League {
  teams: { team: string; pythag_win_pct: number; simulation: { first_place_probability: number } }[];
}

test.describe("F1 聯盟脈動", () => {
  test("standings show six teams with Pythagorean expectation from the export", async ({ page }) => {
    await openRoute(page, "/");
    const league = await fetchJson<League>(page, "league.json");
    const rows = page.getByTestId("standings").locator("tbody tr");
    await expect(rows).toHaveCount(6);
    const first = league.teams[0]!;
    await expect(rows.first()).toContainText(first.team);
    await expect(rows.first()).toContainText(first.pythag_win_pct.toFixed(3));
    await expect(page.getByTestId("data-age")).toBeVisible();
    await expectAccessible(page);
  });
});

test.describe("F2 真實實力", () => {
  test("filters live in the URL and the sort switches between raw and posterior", async ({ page }) => {
    await openRoute(page, "/talent");
    await expect(page.getByTestId("traps").locator("li")).toHaveCount(5);
    const table = page.getByTestId("talent-table");
    const posteriorFirst = await table.locator("tbody tr").first().locator("th").innerText();

    await page.getByRole("radio", { name: "原始數據" }).check();
    await expect(page).toHaveURL(/sort=raw/);
    await page.getByLabel("只看達比較門檻").uncheck();
    const rawFirst = await table.locator("tbody tr").first().locator("th").innerText();
    expect(rawFirst).not.toBe(posteriorFirst);

    await page.getByRole("radio", { name: "投手" }).check();
    await expect(page).toHaveURL(/type=pitcher/);
    await page.getByLabel("指標").selectOption("bb_rate");
    await expect(page).toHaveURL(/metric=bb_rate/);
    await expectAccessible(page);

    await page.reload();
    await expect(page.getByLabel("指標")).toHaveValue("bb_rate");
  });
});

test.describe("F3 打線實驗室", () => {
  test("simulation is reproducible and the order search reports a gain with a CI", async ({ page }) => {
    await openRoute(page, "/lineup");
    await expect(page.getByTestId("lineup-slots").locator("li")).toHaveCount(9);
    await page.getByRole("radio", { name: "1,000" }).check();
    await page.getByRole("button", { name: /模擬 1,000 場/ }).click();
    const value = page.getByTestId("runs-per-game");
    await expect(value).toBeVisible();
    const first = Number(await value.innerText());
    expect(first).toBeGreaterThan(1);
    expect(first).toBeLessThan(8);

    await page.getByRole("button", { name: /模擬 1,000 場/ }).click();
    await expect(page.getByRole("progressbar")).toHaveCount(0);
    expect(Number(await value.innerText())).toBe(first);

    await page.getByRole("button", { name: "搜尋更好的棒次" }).click();
    await expect(page.getByTestId("order-search")).toBeVisible({ timeout: 45_000 });
    await expect(page.getByTestId("order-search")).toContainText("評估");
    await expectAccessible(page);
  });

  test("a long simulation can be cancelled and the lineup can be reordered by keyboard", async ({ page }) => {
    await openRoute(page, "/lineup");
    const firstSlot = page.locator("#slot-0");
    const secondSlot = page.locator("#slot-1");
    const a = await firstSlot.inputValue();
    const b = await secondSlot.inputValue();
    await page.getByRole("button", { name: /往後一棒/ }).first().focus();
    await page.keyboard.press("Enter");
    await expect(firstSlot).toHaveValue(b);
    await expect(secondSlot).toHaveValue(a);
    await expect(page).toHaveURL(new RegExp(`ids=${b}%2C${a}|ids=${b},${a}`));

    // The order search evaluates ~100 orders × 1,500 games, long enough to cancel.
    await page.getByRole("button", { name: "搜尋更好的棒次" }).click();
    await expect(page.getByRole("progressbar")).toBeVisible();
    await page.getByRole("button", { name: "取消" }).click();
    await expect(page.getByRole("progressbar")).toHaveCount(0);
    await expect(page.getByTestId("order-search")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "搜尋更好的棒次" })).toBeEnabled();
  });
});

test.describe("F4 季末模擬", () => {
  test("first-place probabilities are shown for all teams and sum to 100%", async ({ page }) => {
    await openRoute(page, "/season");
    const items = page.getByTestId("title-odds").locator("li");
    await expect(items).toHaveCount(6);
    const values = await page.getByTestId("title-odds").locator(".prob-value").allInnerTexts();
    const total = values.reduce((sum, v) => sum + Number(v.replace("%", "")), 0);
    expect(Math.abs(total - 100)).toBeLessThan(0.6);
    await page.getByLabel("檢視球隊").selectOption({ index: 1 });
    await expectAccessible(page);
  });
});

test.describe("F5 球員檔案", () => {
  test("scouting notes cite evidence and similar players are navigable", async ({ page }) => {
    await openRoute(page, "/player/batter/0000005549");
    await expect(page.locator("h1")).toHaveText("郭天信");
    const notes = page.getByTestId("scouting-notes").locator("li");
    expect(await notes.count()).toBeGreaterThanOrEqual(2);
    for (const text of await notes.allInnerTexts()) expect(text).not.toMatch(/[{}]/);

    const chip = page.getByTestId("scouting-notes").getByRole("button").first();
    await chip.focus();
    await expect(chip).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator(".pbar-focus")).toHaveCount(1);

    const similar = page.getByTestId("similar-players").locator("ol > li");
    await expect(similar).toHaveCount(5);
    const name = await similar.first().locator("a").innerText();
    await similar.first().locator("a").click();
    await expect(page.locator("h1")).toHaveText(name);
    await expectAccessible(page);
  });

  test("unknown players show a clear empty state", async ({ page }) => {
    await page.goto("./#/player/batter/does-not-exist");
    await expect(page.getByText("找不到這位球員")).toBeVisible();
  });
});

test.describe("F6 比較與分享", () => {
  test("comparison is shareable and exports a safe CSV", async ({ page }) => {
    await openRoute(page, "/compare?type=batter&ids=0000005549");
    await page.getByLabel("加入球員").selectOption({ index: 1 });
    await expect(page.getByTestId("compare-grid").locator("article")).toHaveCount(2);
    const url = page.url();
    await page.reload();
    expect(page.url()).toBe(url);
    await expect(page.getByTestId("compare-grid").locator("article")).toHaveCount(2);

    const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "匯出 CSV" }).click()]);
    const csv = await readFile((await download.path())!, "utf-8");
    expect(csv.startsWith("﻿player_id,name,team")).toBe(true);
    expect(csv).toContain("郭天信");
    expect(csv.split("\r\n").filter(Boolean)).toHaveLength(1 + 2 * 6);

    const [json] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "匯出 JSON" }).click()]);
    const parsed = JSON.parse(await readFile((await json.path())!, "utf-8"));
    expect(parsed.players).toHaveLength(2);
    await expectAccessible(page);
  });
});

test.describe("F7 資料可信度", () => {
  test("all files pass in-browser SHA-256 verification and match the release", async ({ page }) => {
    await openRoute(page, "/data");
    await expect(page.getByTestId("integrity-summary")).toHaveText("5/5", { timeout: 15_000 });
    const provenance = await fetchJson<{ release_id: string; snapshots: unknown[] }>(page, "provenance.json");
    await expect(page.getByTestId("release-id")).toHaveText(provenance.release_id);
    await expect(page.getByTestId("snapshot-table").locator("tbody tr")).toHaveCount(provenance.snapshots.length);
    await expectAccessible(page);
  });
});
