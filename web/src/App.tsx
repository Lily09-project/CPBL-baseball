import { lazy, Suspense, useEffect, useMemo, useRef, useState, useSyncExternalStore, type ComponentType } from "react";
import { LoaderContext, useDocumentTitle, useRoute } from "./app/hooks";
import { RouteBoundary } from "./components/RouteBoundary";
import { Shell } from "./components/Shell";
import { EmptyState, ErrorState, Loading } from "./components/States";
import { createLoader, DeploymentChangedError, type Loader } from "./lib/data";
import { routeToHash, type Route } from "./lib/router";
import Home from "./routes/Home";

/**
 * A lazily loaded page that can be fetched ahead of time. `React.lazy` suspends on its first render
 * even when the code has already arrived, which flashes 頁面載入中; once `preload` has finished, the
 * page renders the loaded component directly. The choice is made once per mount, so a page that
 * mounted through the lazy path never remounts (and never loses its state) when the code lands.
 */
function page<P extends object>(load: () => Promise<{ default: ComponentType<P> }>) {
  let loaded: ComponentType<P> | undefined;
  const preload = () =>
    load().then((module) => {
      loaded = module.default;
      return module;
    });
  const Lazy = lazy(preload);
  function Page(props: P) {
    const [Component] = useState<ComponentType<P>>(() => loaded ?? Lazy);
    return <Component {...props} />;
  }
  return { Page, preload };
}

const pages = {
  talent: page(() => import("./routes/Talent")),
  lineup: page(() => import("./routes/Lineup")),
  season: page(() => import("./routes/Season")),
  player: page(() => import("./routes/Player")),
  compare: page(() => import("./routes/Compare")),
  data: page(() => import("./routes/DataTrust")),
};
const Talent = pages.talent.Page;
const Lineup = pages.lineup.Page;
const Season = pages.season.Page;
const Player = pages.player.Page;
const Compare = pages.compare.Page;
const DataTrust = pages.data.Page;

/**
 * Once the first page has painted and the browser is idle, fetch the other pages' code so the
 * first click on the menu opens instantly instead of flashing 頁面載入中. Skipped when the visitor
 * asked to save data. A failure here is harmless: the page retries when it is actually opened.
 */
function prefetchPages() {
  const connection = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection;
  if (connection?.saveData) return () => undefined;
  const run = () => {
    for (const { preload } of Object.values(pages)) preload().catch(() => undefined);
  };
  if (typeof window.requestIdleCallback === "function") {
    const id = window.requestIdleCallback(run, { timeout: 4000 });
    return () => window.cancelIdleCallback(id);
  }
  const id = window.setTimeout(run, 2000);
  return () => window.clearTimeout(id);
}

function NotFound({ path }: { path: string }) {
  useDocumentTitle("找不到頁面");
  return (
    <div className="page stack">
      <header>
        <h1>找不到這個頁面</h1>
      </header>
      <EmptyState title="網址不存在">
        <p>
          <code>{path}</code> 不是這個網站的頁面。<a href={routeToHash({ name: "home" })}>回到首頁</a>，或從上方選單選擇一個實驗。
        </p>
      </EmptyState>
    </div>
  );
}

function Routes({ route }: { route: Route }) {
  const key = route.name === "player" ? `player-${route.type}-${route.id}` : route.name;

  switch (route.name) {
    case "home":
      return <Home />;
    case "talent":
      return <Talent />;
    case "lineup":
      return <Lineup />;
    case "season":
      return <Season />;
    case "player":
      return <Player key={key} type={route.type} id={route.id} />;
    case "compare":
      return <Compare type={route.type} ids={route.ids} />;
    case "data":
      return <DataTrust />;
    case "not-found":
      return <NotFound path={route.path} />;
  }
}

export default function App({ loader }: { loader?: Loader }) {
  const value = useMemo(() => loader ?? createLoader(import.meta.env.BASE_URL), [loader]);
  const deploymentChanged = useSyncExternalStore(value.subscribe, value.hasDeploymentChanged);
  const [route] = useRoute();
  const key = route.name === "player" ? `player-${route.type}-${route.id}` : route.name;
  const previousKey = useRef(key);

  useEffect(prefetchPages, []);

  // The shell is available even when the next route's module is still loading.
  useEffect(() => {
    if (previousKey.current === key) return;
    previousKey.current = key;
    window.scrollTo({ top: 0 });
    document.getElementById("main")?.focus({ preventScroll: true });
  }, [key]);

  return (
    <LoaderContext.Provider value={value}>
      <Shell>
        <RouteBoundary routeKey={key}>
          <Suspense
            fallback={
              <div className="page">
                <Loading label="頁面載入中" />
              </div>
            }
          >
            {deploymentChanged ? (
              <div className="page">
                <ErrorState error={new DeploymentChangedError()} />
                <button type="button" className="btn" onClick={() => window.location.reload()}>重新整理</button>
              </div>
            ) : <Routes route={route} />}
          </Suspense>
        </RouteBoundary>
      </Shell>
    </LoaderContext.Provider>
  );
}
