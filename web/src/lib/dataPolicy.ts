/**
 * The published data is frozen at its last verified snapshot. Since October 2026
 * the official site has blocked automated fetches; this project does not work
 * around that protection, so it stopped refreshing instead of publishing
 * unverified data. The snapshot time itself always comes from provenance.json.
 */
export const DATA_FROZEN = true;

export const FROZEN_REASON =
  "CPBL 官方網站自 2026 年 10 月起阻擋自動化擷取；本站不繞過網站防護，因此停止自動更新，保留最後一份通過驗證的快照。";
