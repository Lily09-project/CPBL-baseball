import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Loader } from "../lib/data";
import type { DataFiles } from "../lib/types";
import { LoaderContext, useDataset } from "./hooks";

type DetailsFile = "player-details-batter.json" | "player-details-pitcher.json";

function Probe({ name }: { name: DetailsFile }) {
  const state = useDataset(name);
  return <p data-testid="state">{state.status === "ready" ? Object.keys(state.data).join(",") : state.status}</p>;
}

describe("useDataset", () => {
  it("never shows the previous file's data after the file name changes", async () => {
    const pending = new Map<string, (value: unknown) => void>();
    const loader = {
      load: (name: keyof DataFiles) => new Promise((resolve) => pending.set(name, resolve)),
      manifest: () => Promise.reject(new Error("unused")),
      verifiedFiles: () => [],
    } as unknown as Loader;
    const { rerender } = render(
      <LoaderContext.Provider value={loader}>
        <Probe name="player-details-batter.json" />
      </LoaderContext.Provider>,
    );
    pending.get("player-details-batter.json")?.({ "1:batter": {} });
    expect(await screen.findByText("1:batter")).toBeInTheDocument();

    rerender(
      <LoaderContext.Provider value={loader}>
        <Probe name="player-details-pitcher.json" />
      </LoaderContext.Provider>,
    );
    expect(screen.getByTestId("state")).toHaveTextContent("loading");
    pending.get("player-details-pitcher.json")?.({ "2:pitcher": {} });
    expect(await screen.findByText("2:pitcher")).toBeInTheDocument();
  });
});
