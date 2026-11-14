import { expect, it } from "vitest";
import { summarizePairedRuns } from "./pairedLineup";
import { parseRoute, routeToHash, type Route } from "./router";

it("uses paired differences from the same numbered games", () => {
  expect(summarizePairedRuns([1, 8, 2], [1, 8, 2])).toEqual({ a: 11 / 3, b: 11 / 3, delta: 0, low: 0, high: 0 });
  expect(summarizePairedRuns([1, 8, 2], [2, 9, 3])).toMatchObject({ delta: 1, low: 1, high: 1 });
  expect(() => summarizePairedRuns([1], [])).toThrow();
});

it("round-trips both lineups and pins their shared settings and snapshot", () => {
  const ids = Array.from({ length: 9 }, (_, index) => String(index + 1));
  const route: Route = { name: "lineup", a: { ids, pitcher: "p1" }, b: { ids: [...ids].reverse() }, snapshot: "snap", games: 1000, seed: 55 };
  expect(parseRoute(routeToHash(route))).toMatchObject(route);
});
