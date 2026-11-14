import { expect, openRoute, test } from "./fixtures";

test("打線方案 A／B keeps settings after reload", async ({ page }) => {
  await openRoute(page, "/lineup");
  await page.getByRole("button", { name: "儲存為 A" }).click();
  await page.getByRole("button", { name: "複製 A 到 B" }).click();
  await expect(page).toHaveURL(/snapshot=/);
  await page.reload();
  await expect(page.getByTestId("lineup-differences")).toContainText("棒次與打者相同");
  await page.getByRole("button", { name: "比較兩組打線" }).click();
  await expect(page.getByTestId("paired-lineup-result")).toContainText("0.00 至 0.00");
  await expect(page.getByTestId("paired-lineup-result")).toContainText("區間包含 0");
  const downloadReady = page.waitForEvent("download");
  await page.getByRole("button", { name: "下載比較 CSV" }).click();
  expect((await downloadReady).suggestedFilename()).toBe("cpbl-lineup-comparison.csv");
  await page.getByRole("button", { name: /往後一棒/ }).first().click();
  await page.getByRole("button", { name: "儲存為 B" }).click();
  await expect(page.getByTestId("lineup-differences")).toContainText("第 1、2 棒不同");
  await expect(page.getByTestId("paired-lineup-result")).toHaveCount(0);
});
