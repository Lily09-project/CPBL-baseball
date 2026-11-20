import { expect, openRoute, test } from "./fixtures";

for (const [low, high] of [[-1.2, -0.8], [-0.8, 0.2], [-0.2, 0.8], [0.2, 0.8]]) {
  test(`held-out lineup verdict respects both interval bounds (${low}, ${high})`, async ({ page }) => {
    await page.addInitScript(({ low, high }) => {
      class ResultWorker extends EventTarget {
        postMessage(request: { id: number }) {
          setTimeout(() => this.dispatchEvent(new MessageEvent("message", { data: {
            id: request.id, type: "optimised", search: {
              order: [1, 0, 2, 3, 4, 5, 6, 7, 8], baselineMean: 5,
              bestMean: 5 + (low + high) / 2, delta: (low + high) / 2,
              deltaLow: low, deltaHigh: high, evaluations: 28,
            },
          } })), 100);
        }
        terminate() {}
      }
      Object.defineProperty(window, "Worker", { value: ResultWorker });
    }, { low: low!, high: high! });
    await openRoute(page, "/lineup");
    await page.getByRole("button", { name: "搜尋更好的棒次" }).click();
    const result = page.getByTestId("order-search");
    await expect(result).toBeVisible();
    if (low! <= 0 && high! >= 0) await expect(result).toContainText("區間包含 0");
    else await expect(result).not.toContainText("區間包含 0");
    if (high! < 0) await expect(result).toContainText("調整後得分較低");
    const delta = (low! + high!) / 2;
    const apply = result.getByRole("button", { name: /套用/ });
    if (delta <= 0) {
      // No improvement: no recommendation and nothing to apply.
      await expect(result.getByRole("heading")).toHaveText("沒有找到明顯更好的棒次");
      await expect(apply).toHaveCount(0);
    } else if (low! <= 0) {
      // Positive but uncertain: offered, but as a secondary action that names the doubt.
      await expect(result.getByRole("heading")).toContainText("尚不確定");
      await expect(apply).toHaveText("仍要套用（改善可能只是雜訊）");
      await expect(apply).not.toHaveClass(/btn-primary/);
    } else {
      await expect(result.getByRole("heading")).toHaveText("建議棒次");
      await expect(apply).toHaveText("套用建議棒次");
      await expect(apply).toHaveClass(/btn-primary/);
    }
  });
}
