import { expect, openRoute, test } from "./fixtures";

test("打線方案 A／B keeps settings after reload", async ({ page }) => {
  await openRoute(page, "/lineup");
  await page.getByRole("button", { name: "儲存為 A" }).click();
  await page.getByRole("button", { name: "複製 A 到 B" }).click();
  await expect(page).toHaveURL(/snapshot=/);
  await page.reload();
  await page.getByRole("button", { name: "比較兩組打線" }).click();
  await expect(page.getByTestId("paired-lineup-result")).toContainText("0.00 至 0.00");
  await expect(page.getByRole("button", { name: "下載比較 CSV" })).toBeEnabled();
});
