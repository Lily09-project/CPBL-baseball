import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { Provenance } from "../lib/types";
import { SnapshotNotice } from "./SnapshotNotice";

const provenance = { generated_at: "2026-09-29T20:48:33+00:00" } as Provenance;

afterEach(cleanup);

describe("SnapshotNotice", () => {
  it("dates the standings in Taipei time and flags later games as missing once stale", () => {
    render(<SnapshotNotice provenance={provenance} now={new Date("2026-11-03T00:00:00Z")} />);
    const notice = screen.getByTestId("snapshot-notice");
    expect(notice).toHaveTextContent("2026-09-30 04:48（台北時間）");
    expect(notice).toHaveTextContent("距今 34 天");
    expect(notice).toHaveTextContent("快照之後的比賽沒有納入");
    expect(notice).toHaveAttribute("data-level", "stale");
  });

  it("does not warn about missing games while the snapshot is recent", () => {
    render(<SnapshotNotice provenance={provenance} now={new Date("2026-09-30T12:00:00Z")} />);
    expect(screen.getByTestId("snapshot-notice")).not.toHaveTextContent("沒有納入");
  });
});
