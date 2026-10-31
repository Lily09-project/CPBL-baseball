import { describe, expect, it, vi } from "vitest";
import { escapeCell, toCsv } from "./csv";
import { createLoader, IntegrityError, sha256Hex } from "./data";
import { formatDate, formatMetric, formatPercent, formatSigned, freshness, ordinalPercentile } from "./format";
import { gameSeed, mulberry32 } from "./rng";
import { parseRoute, routeToHash, type Route } from "./router";
import { searchPlayers } from "./search";
import { integerHistogram, mean, quantile, shareAtLeast, standardDeviation } from "./stats";
import type { PlayerSummary } from "./types";

describe("rng", () => {
  it("is deterministic and uniform-ish", () => {
    const a = mulberry32(5);
    const b = mulberry32(5);
    const values = Array.from({ length: 1000 }, () => a());
    expect(values.slice(0, 5)).toEqual(Array.from({ length: 5 }, () => b()));
    expect(Math.min(...values)).toBeGreaterThanOrEqual(0);
    expect(Math.max(...values)).toBeLessThan(1);
    expect(mean(values)).toBeGreaterThan(0.45);
    expect(mean(values)).toBeLessThan(0.55);
    expect(gameSeed(1, 0)).not.toBe(gameSeed(1, 1));
  });
});

describe("stats", () => {
  it("computes summary statistics", () => {
    expect(mean([1, 2, 3])).toBe(2);
    expect(Number.isNaN(mean([]))).toBe(true);
    expect(standardDeviation([2, 4, 4, 4, 5, 5, 7, 9])).toBeCloseTo(2.138, 3);
    expect(standardDeviation([1])).toBe(0);
    expect(quantile([1, 2, 3, 4], 0.5)).toBe(2.5);
    expect(quantile([5], 0.9)).toBe(5);
    expect(Number.isNaN(quantile([], 0.5))).toBe(true);
    expect(integerHistogram([0, 1, 1, 7, 20], 5)).toEqual([1, 2, 0, 0, 0, 2]);
    expect(shareAtLeast([1, 5, 6, 2], 5)).toBe(0.5);
    expect(Number.isNaN(shareAtLeast([], 5))).toBe(true);
  });
});

describe("format", () => {
  it("formats metrics consistently", () => {
    expect(formatMetric(0.3214, "rate3")).toBe(".321");
    expect(formatMetric(1.234, "rate3")).toBe("1.234");
    expect(formatMetric(0.1572, "pct1")).toBe("15.7%");
    expect(formatMetric(3.456, "num2")).toBe("3.46");
    expect(formatMetric(null, "num2")).toBe("—");
    expect(formatPercent(0.623)).toBe("62%");
    expect(formatPercent(undefined)).toBe("—");
    expect(formatSigned(1.25)).toBe("+1.3");
    expect(formatSigned(-0.04)).toBe("0.0");
    expect(formatSigned(-2.5)).toBe("-2.5");
    expect(ordinalPercentile(87.4)).toBe("PR 87");
    expect(ordinalPercentile(null)).toBe("—");
    expect(formatDate("2026-09-29T20:48:33+00:00")).toBe("2026-09-29");
  });

  it("classifies data freshness without pretending to be live", () => {
    const now = new Date("2026-10-10T00:00:00Z");
    expect(freshness("2026-10-09T12:00:00Z", now)).toEqual({ level: "current", days: 0 });
    expect(freshness("2026-10-05T00:00:00Z", now).level).toBe("recent");
    expect(freshness("2026-09-29T20:48:33+00:00", now)).toEqual({ level: "stale", days: 10 });
    expect(freshness("2026-11-01T00:00:00Z", now).days).toBe(0);
  });
});

describe("router", () => {
  const roundTrip = (route: Route) => expect(parseRoute(routeToHash(route))).toEqual(route);

  it("round-trips every route", () => {
    roundTrip({ name: "home" });
    roundTrip({ name: "season" });
    roundTrip({ name: "data" });
    roundTrip({ name: "talent", type: "pitcher", metric: "k_rate_post", sort: "raw", team: "味全龍", q: "王" });
    roundTrip({ name: "lineup", team: "中信兄弟", ids: ["1", "2"], pitcher: "9", seed: 7 });
    roundTrip({ name: "player", type: "batter", id: "0000005549" });
    roundTrip({ name: "compare", type: "batter", ids: ["a", "b"] });
  });

  it("normalises unknown or invalid input", () => {
    expect(parseRoute("")).toEqual({ name: "home" });
    expect(parseRoute("#/nowhere")).toEqual({ name: "not-found", path: "/nowhere" });
    expect(parseRoute("#/player/batter")).toEqual({ name: "not-found", path: "/player/batter" });
    expect(parseRoute("#/talent?type=x&sort=y")).toMatchObject({ type: "batter", sort: undefined });
    expect(parseRoute("#/talent?sort=posterior")).toMatchObject({ sort: "posterior" });
    expect(parseRoute("#/compare?ids=a,a,b,c,d")).toMatchObject({ ids: ["a", "b", "c"] });
    expect(parseRoute("#/lineup?seed=-3")).toMatchObject({ seed: undefined, ids: [] });
    expect(routeToHash({ name: "not-found", path: "/x" })).toBe("#/x");
    expect(routeToHash({ name: "lineup" })).toBe("#/lineup");
  });
});

describe("csv", () => {
  it("neutralises spreadsheet formulas and quotes special characters", () => {
    expect(escapeCell("=HYPERLINK(1)")).toBe("'=HYPERLINK(1)");
    expect(escapeCell("@cmd")).toBe("'@cmd");
    expect(escapeCell(-3)).toBe("-3");
    expect(escapeCell('a,"b"')).toBe('"a,""b"""');
    expect(escapeCell(null)).toBe("");
    // Bypasses covered by the original Python exporter's tests.
    for (const attack of ['=HYPERLINK("https://example.invalid")', "+SUM(1,2)", "-2+3", "@SUM(1,2)", "\t=1+1", " =1+1", "\n@SUM(1,2)", "\v-2+3", "\f+1"]) {
      expect(escapeCell(attack).replace(/^"/, "")).toMatch(/^'/);
    }
    expect(escapeCell("一般文字")).toBe("一般文字");
    expect(escapeCell("-")).toBe("-");
    expect(escapeCell(" normal text")).toBe(" normal text");
    expect(escapeCell(7)).toBe("7");
    expect(toCsv(["=FORMULA"], []).startsWith("\uFEFF'=FORMULA")).toBe(true);
    const csv = toCsv(["name", "ops"], [{ name: "郭天信", ops: 0.676 }]);
    expect(csv.startsWith("﻿name,ops\r\n郭天信,0.676")).toBe(true);
  });
});

const player = (overrides: Partial<PlayerSummary>): PlayerSummary => ({
  player_id: "1",
  name: "王",
  team: "味全龍",
  type: "batter",
  position: "野手",
  trials: 100,
  qualified: true,
  metrics: {},
  percentiles: {},
  talent: {},
  trend: "steady",
  ...overrides,
});

describe("search", () => {
  it("ranks exact, prefix, substring and team matches", () => {
    const players = [
      player({ player_id: "a", name: "林子偉", team: "樂天桃猿" }),
      player({ player_id: "b", name: "林立", team: "樂天桃猿" }),
      player({ player_id: "c", name: "王柏融", team: "台鋼雄鷹" }),
      player({ player_id: "d", name: "林", team: "富邦悍將", qualified: false, trials: 3 }),
    ];
    const lin = searchPlayers(players, "林").map((p) => p.player_id);
    expect(lin[0]).toBe("d"); // exact name beats prefix matches
    expect(new Set(lin.slice(1))).toEqual(new Set(["a", "b"]));
    expect(searchPlayers(players, "子偉")[0]?.player_id).toBe("a");
    expect(searchPlayers(players, "台鋼")[0]?.player_id).toBe("c");
    expect(searchPlayers(players, "  ")).toEqual([]);
    expect(searchPlayers(players, "林", 1)).toHaveLength(1);
  });
});

describe("data loader", () => {
  const encoder = new TextEncoder();
  const respond = (body: string, status = 200) => new Response(encoder.encode(body), { status });

  it("verifies every file against the manifest", async () => {
    const league = '{"teams":[]}';
    const digest = await sha256Hex(encoder.encode(league).buffer as ArrayBuffer);
    const fetcher = vi.fn(async (url: string) => {
      if (url.endsWith("manifest.json")) return respond(JSON.stringify({ schema_version: "2.0", files: { "league.json": digest } }));
      if (url.endsWith("league.json")) return respond(league);
      return respond("missing", 404);
    });
    const loader = createLoader("./", fetcher);
    await expect(loader.load("league.json")).resolves.toEqual({ teams: [] });
    await loader.load("league.json");
    expect(fetcher).toHaveBeenCalledTimes(2); // manifest + league, then cached
    expect(loader.verifiedFiles()).toEqual(["league.json"]);
    await expect(loader.load("players.json")).rejects.toThrow("HTTP 404");
  });

  it("rejects tampered files", async () => {
    const fetcher = async (url: string) =>
      url.endsWith("manifest.json") ? respond(JSON.stringify({ schema_version: "2.0", files: { "league.json": "0".repeat(64) } })) : respond("{}");
    const loader = createLoader("./", fetcher);
    await expect(loader.load("league.json")).rejects.toBeInstanceOf(IntegrityError);
  });

  it("retries the manifest after a failed load instead of caching the rejection", async () => {
    const league = '{"teams":[]}';
    const digest = await sha256Hex(encoder.encode(league).buffer as ArrayBuffer);
    let manifestCalls = 0;
    const fetcher = vi.fn(async (url: string) => {
      if (url.endsWith("manifest.json")) {
        manifestCalls += 1;
        return manifestCalls === 1 ? respond("unavailable", 503) : respond(JSON.stringify({ schema_version: "2.0", files: { "league.json": digest } }));
      }
      return respond(league);
    });
    const loader = createLoader("./", fetcher);
    await expect(loader.load("league.json")).rejects.toThrow("HTTP 503");
    await expect(loader.load("league.json")).resolves.toEqual({ teams: [] });
    expect(manifestCalls).toBe(2);
  });

  it("refetches a stale manifest and file once, bypassing the cache, before failing integrity", async () => {
    const newLeague = '{"teams":["new"]}';
    const oldDigest = await sha256Hex(encoder.encode('{"teams":["old"]}').buffer as ArrayBuffer);
    const newDigest = await sha256Hex(encoder.encode(newLeague).buffer as ArrayBuffer);
    let deployed = false;
    const fetcher = vi.fn(async (url: string) => {
      if (url.endsWith("manifest.json")) {
        return respond(JSON.stringify({ schema_version: "2.0", files: { "league.json": deployed ? newDigest : oldDigest } }));
      }
      // The file request already hits the new deployment.
      deployed = true;
      return respond(newLeague);
    });
    const loader = createLoader("./", fetcher);
    await loader.manifest(); // the tab still holds the old manifest
    await expect(loader.load("league.json")).resolves.toEqual({ teams: ["new"] });
    expect(fetcher).toHaveBeenCalledWith("./data/manifest.json", { cache: "reload" });
    expect(fetcher).toHaveBeenCalledWith("./data/league.json", { cache: "reload" });

    const tampered = vi.fn(async (url: string) =>
      url.endsWith("manifest.json") ? respond(JSON.stringify({ schema_version: "2.0", files: { "league.json": oldDigest } })) : respond(newLeague),
    );
    await expect(createLoader("./", tampered).load("league.json")).rejects.toBeInstanceOf(IntegrityError);
    expect(tampered).toHaveBeenCalledTimes(4); // manifest + file, then one reload of each
  });
});
