import { formatDateTime, freshness } from "../lib/format";
import type { Provenance } from "../lib/types";

/**
 * States plainly which snapshot the standings come from. When the snapshot is
 * no longer recent it says that later games are missing, without claiming
 * anything about them: the page only knows what the snapshot contains.
 */
export function SnapshotNotice({ provenance, now = new Date() }: { provenance: Provenance; now?: Date }) {
  const age = freshness(provenance.generated_at, now);
  return (
    <p className="notice" data-testid="snapshot-notice" data-level={age.level}>
      <strong>資料時間點：</strong>以下戰績與模擬都以 {formatDateTime(provenance.generated_at)}（台北時間）擷取的官方快照為準
      {age.level === "stale"
        ? `，距今 ${age.days} 天。快照之後的比賽沒有納入，這段期間半季可能已經打完；這裡呈現的是「當時」所做的情境推演，實際結果請以 CPBL 官方戰績為準。`
        : "。"}
    </p>
  );
}
