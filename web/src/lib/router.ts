/**
 * Hash-based routes: they work on any static host (GitHub Pages included)
 * and every screen state lives in the URL, so any view can be shared.
 */
export type Route =
  | { name: "home" }
  | { name: "talent"; type: "batter" | "pitcher"; metric?: string; sort?: "raw" | "posterior"; team?: string; q?: string }
  | { name: "lineup"; team?: string; ids?: string[]; pitcher?: string; seed?: number }
  | { name: "season" }
  | { name: "player"; type: "batter" | "pitcher"; id: string }
  | { name: "compare"; type: "batter" | "pitcher"; ids: string[] }
  | { name: "data" }
  | { name: "not-found"; path: string };

const MAX_COMPARE = 3;
const asType = (value: string | null | undefined): "batter" | "pitcher" => (value === "pitcher" ? "pitcher" : "batter");
const list = (value: string | null) => (value ? value.split(",").map((v) => v.trim()).filter(Boolean) : []);

export function parseRoute(hash: string): Route {
  const raw = hash.replace(/^#/, "") || "/";
  const [path = "/", query = ""] = raw.split("?");
  const params = new URLSearchParams(query);
  const parts = path.split("/").filter(Boolean).map(decodeURIComponent);
  const [head, second, third] = parts;
  switch (head) {
    case undefined:
      return { name: "home" };
    case "talent": {
      const sort = params.get("sort");
      return {
        name: "talent",
        type: asType(params.get("type")),
        metric: params.get("metric") ?? undefined,
        sort: sort === "raw" ? "raw" : sort === "posterior" ? "posterior" : undefined,
        team: params.get("team") ?? undefined,
        q: params.get("q") ?? undefined,
      };
    }
    case "lineup": {
      const seed = Number(params.get("seed"));
      return {
        name: "lineup",
        team: params.get("team") ?? undefined,
        ids: list(params.get("ids")).slice(0, 9),
        pitcher: params.get("pitcher") ?? undefined,
        seed: Number.isInteger(seed) && seed > 0 ? seed : undefined,
      };
    }
    case "season":
      return { name: "season" };
    case "player":
      if (second && third) return { name: "player", type: asType(second), id: third };
      return { name: "not-found", path };
    case "compare":
      return { name: "compare", type: asType(params.get("type")), ids: [...new Set(list(params.get("ids")))].slice(0, MAX_COMPARE) };
    case "data":
      return { name: "data" };
    default:
      return { name: "not-found", path };
  }
}

export function routeToHash(route: Route): string {
  const query = (entries: Record<string, string | number | undefined>) => {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(entries)) {
      if (value !== undefined && value !== "") params.set(key, String(value));
    }
    const text = params.toString();
    return text ? `?${text}` : "";
  };
  switch (route.name) {
    case "home":
      return "#/";
    case "talent":
      return `#/talent${query({ type: route.type, metric: route.metric, sort: route.sort, team: route.team, q: route.q })}`;
    case "lineup":
      return `#/lineup${query({ team: route.team, ids: route.ids?.join(","), pitcher: route.pitcher, seed: route.seed })}`;
    case "season":
      return "#/season";
    case "player":
      return `#/player/${route.type}/${encodeURIComponent(route.id)}`;
    case "compare":
      return `#/compare${query({ type: route.type, ids: route.ids.join(",") })}`;
    case "data":
      return "#/data";
    case "not-found":
      return `#${route.path}`;
  }
}
