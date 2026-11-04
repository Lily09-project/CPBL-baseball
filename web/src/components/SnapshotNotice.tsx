import { DATA_FROZEN } from "../lib/dataPolicy";
import { formatDateTime, freshness } from "../lib/format";
import type { Provenance } from "../lib/types";

/**
 * States plainly which snapshot the standings come from. Once the data is frozen
 * (or the snapshot is no longer recent) it says that later games are missing,
 * without claiming anything about them: the page only knows what the snapshot contains.
 */
export function SnapshotNotice({
  provenance,
  now = new Date(),
  frozen = DATA_FROZEN,
}: {
  provenance: Provenance;
  now?: Date;
  frozen?: boolean;
}) {
  const age = freshness(provenance.generated_at, now);
  const captured = formatDateTime(provenance.generated_at);
  if (frozen) {
    return (
      <p className="notice" data-testid="snapshot-notice" data-level="frozen">
        <strong>資料已凍結：</strong>以下戰績與模擬固定在 {captured}（台北時間）擷取的官方快照，之後不再更新。快照之後的比賽沒有納入；這裡呈現的是「當時」所做的情境推演，實際結果請以 CPBL 官方戰績為準。
      </p>
    );
  }
  return (
    <p className="notice" data-testid="snapshot-notice" data-level={age.level}>
      <strong>資料時間點：</strong>以下戰績與模擬都以 {captured}（台北時間）擷取的官方快照為準
      {age.level === "stale"
        ? `，距今 ${age.days} 天。快照之後的比賽沒有納入，這段期間半季可能已經打完；這裡呈現的是「當時」所做的情境推演，實際結果請以 CPBL 官方戰績為準。`
        : "。"}
    </p>
  );
}
