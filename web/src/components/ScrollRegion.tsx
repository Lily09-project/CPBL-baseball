import { useEffect, useRef, useState, type ReactNode } from "react";

/**
 * A horizontally scrollable table wrapper that keyboard users can focus and
 * scroll. When the table is wider than the screen and there is more to the
 * right, a short visible hint says so (phones show no scrollbar until you swipe).
 */
export function ScrollRegion({ label, children }: { label: string; children: ReactNode }) {
  const region = useRef<HTMLDivElement>(null);
  const [more, setMore] = useState(false);

  useEffect(() => {
    const node = region.current;
    if (!node) return;
    const check = () => setMore(node.scrollWidth - node.clientWidth - node.scrollLeft > 1);
    check();
    node.addEventListener("scroll", check, { passive: true });
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(check);
    observer?.observe(node);
    if (node.firstElementChild) observer?.observe(node.firstElementChild);
    return () => {
      node.removeEventListener("scroll", check);
      observer?.disconnect();
    };
  }, []);

  return (
    <div className="scroll-wrap">
      <div ref={region} className="table-scroll" role="region" aria-label={label} tabIndex={0}>
        {children}
      </div>
      {more && (
        <p className="scroll-hint" aria-hidden="true" data-testid="scroll-hint">
          向右滑動看更多欄位 →
        </p>
      )}
    </div>
  );
}
