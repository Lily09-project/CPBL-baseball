import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RouteBoundary } from "./RouteBoundary";

afterEach(cleanup);

function Broken(): never {
  throw new Error("Unable to preload CSS");
}

describe("RouteBoundary", () => {
  it("shows a way out instead of a blank page when a route fails to render", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    render(
      <RouteBoundary routeKey="lineup">
        <Broken />
      </RouteBoundary>,
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("頁面無法載入");
    expect(screen.getByRole("alert")).toHaveTextContent("沒有載入成功");
    expect(screen.getByRole("button", { name: "重新整理" })).toBeInTheDocument();
  });

  it("recovers when the visitor moves to another page", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { rerender } = render(
      <RouteBoundary routeKey="lineup">
        <Broken />
      </RouteBoundary>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    rerender(
      <RouteBoundary routeKey="season">
        <p>season page</p>
      </RouteBoundary>,
    );
    expect(screen.getByText("season page")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("renders its children untouched when nothing fails", () => {
    render(
      <RouteBoundary routeKey="home">
        <p>fine</p>
      </RouteBoundary>,
    );
    expect(screen.getByText("fine")).toBeInTheDocument();
  });

  it("reloads the page from the button", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const reload = vi.fn();
    vi.stubGlobal("location", { ...window.location, reload });
    render(
      <RouteBoundary routeKey="lineup">
        <Broken />
      </RouteBoundary>,
    );
    fireEvent.click(screen.getByRole("button", { name: "重新整理" }));
    expect(reload).toHaveBeenCalledOnce();
    vi.unstubAllGlobals();
  });
});
