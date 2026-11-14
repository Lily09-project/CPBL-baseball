import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ContributionBars, TrendLine } from "./charts";

afterEach(cleanup);

const tickLabels = (container: HTMLElement) => Array.from(container.querySelectorAll("g text"), (node) => node.textContent ?? "");

describe("TrendLine", () => {
  it.each([false, true])("never labels a negative OPS or ERA when the series sits at zero (invert=%s)", (invert) => {
    const { container } = render(
      <TrendLine points={[{ t: "2026-09-18", v: 0 }, { t: "2026-09-30", v: 0 }]} format={(v) => v.toFixed(2)} invert={invert} />,
    );
    const labels = tickLabels(container);
    expect(labels.length).toBeGreaterThan(0);
    expect(labels.filter((label) => label.startsWith("-"))).toEqual([]);
  });

  it("still pads the axis around values away from zero", () => {
    const { container } = render(<TrendLine points={[{ t: "a", v: 0.7 }, { t: "b", v: 0.8 }]} format={(v) => v.toFixed(3)} />);
    expect(Math.min(...tickLabels(container).map(Number))).toBeGreaterThan(0.6);
  });
});

describe("ContributionBars", () => {
  it("shows contributions that round to zero without a sign", () => {
    const { container } = render(<ContributionBars items={{ a: 0.31, b: 0.004, c: -0.004, d: -0.02 }} labels={{}} />);
    const values = Array.from(container.querySelectorAll(".contrib-value"), (node) => node.textContent);
    expect(values).toEqual(["+0.31", "0.00", "0.00", "-0.02"]);
  });
});
