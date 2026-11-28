import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Icon } from "./Icon";

afterEach(cleanup);

describe("Icon", () => {
  it("is decorative, takes the text colour and keeps the square geometry", () => {
    const { container } = render(<Icon name="trophy" />);
    const svg = container.querySelector("svg")!;
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg).toHaveAttribute("focusable", "false");
    expect(svg).toHaveAttribute("stroke", "currentColor");
    expect(svg).toHaveAttribute("stroke-linecap", "square");
    expect(svg).toHaveAttribute("width", "18");
    expect(svg).toHaveClass("icon");
  });

  it("accepts a size and an extra class", () => {
    const { container } = render(<Icon name="diamond" size={30} className="story-icon" />);
    const svg = container.querySelector("svg")!;
    expect(svg).toHaveAttribute("width", "30");
    expect(svg).toHaveClass("icon", "story-icon");
  });
});
