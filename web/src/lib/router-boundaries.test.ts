import { describe, expect, it } from "vitest";
import { parseRoute } from "./router";

describe("malformed percent-encoded routes", () => {
  it.each(["#/player/batter/%", "#/player/batter/%E0%A4%A", "#/%zz", "#/player/%FF/123"])(
    "renders an unknown route rather than throwing for %s", (hash) => {
      expect(() => parseRoute(hash)).not.toThrow();
      expect(parseRoute(hash).name).toBe("not-found");
    },
  );
  it("still decodes valid player identifiers", () => {
    expect(parseRoute("#/player/batter/%E7%8E%8B")).toMatchObject({ name: "player", id: "王" });
  });
});
