import { lazy, Suspense, useEffect, useMemo, useRef } from "react";
import { LoaderContext, useRoute } from "./app/hooks";
import { Shell } from "./components/Shell";
import { EmptyState, Loading } from "./components/States";
import { createLoader, type Loader } from "./lib/data";
import { routeToHash } from "./lib/router";
import Home from "./routes/Home";

const Talent = lazy(() => import("./routes/Talent"));
const Lineup = lazy(() => import("./routes/Lineup"));
const Season = lazy(() => import("./routes/Season"));
const Player = lazy(() => import("./routes/Player"));
const Compare = lazy(() => import("./routes/Compare"));
const DataTrust = lazy(() => import("./routes/DataTrust"));

function Routes() {
  const [route] = useRoute();
  const first = useRef(true);
  const key = route.name === "player" ? `player-${route.type}-${route.id}` : route.name;

  // Move focus to the new page for keyboard and screen-reader users.
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    window.scrollTo({ top: 0 });
    document.getElementById("main")?.focus({ preventScroll: true });
  }, [key]);

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
      return (
        <div className="page stack">
          <header>
            <h1>找不到這個頁面</h1>
          </header>
          <EmptyState title="網址不存在">
            <p>
              <code>{route.path}</code> 不是這個網站的頁面。<a href={routeToHash({ name: "home" })}>回到首頁</a>，或從上方選單選擇一個實驗。
            </p>
          </EmptyState>
        </div>
      );
  }
}

export default function App({ loader }: { loader?: Loader }) {
  const value = useMemo(() => loader ?? createLoader(import.meta.env.BASE_URL), [loader]);
  return (
    <LoaderContext.Provider value={value}>
      <Shell>
        <Suspense
          fallback={
            <div className="page">
              <Loading label="頁面載入中" />
            </div>
          }
        >
          <Routes />
        </Suspense>
      </Shell>
    </LoaderContext.Provider>
  );
}
