import { Component, type ReactNode } from "react";

/**
 * Catches a page that fails to render, most often a lazily loaded route file that did not arrive
 * (flaky network, or a deploy that replaced the file names while the tab was open). Without it React
 * unmounts the whole app and the visitor is left with a blank white page and no way out.
 * The shell stays on screen, so the menu still works; moving to another page resets the boundary.
 */
export class RouteBoundary extends Component<{ children: ReactNode; routeKey: string }, { failedKey: string | null }> {
  state = { failedKey: null as string | null };

  static getDerivedStateFromError() {
    return { failedKey: "failed" };
  }

  componentDidUpdate(previous: { routeKey: string }) {
    if (this.state.failedKey !== null && previous.routeKey !== this.props.routeKey) this.setState({ failedKey: null });
  }

  render() {
    if (this.state.failedKey === null) return this.props.children;
    return (
      <div className="page stack">
        <header>
          <h1>頁面無法載入</h1>
        </header>
        <div className="state state-error" role="alert">
          <span className="state-kicker">載入失敗</span>
          <strong className="state-title">這個頁面的檔案沒有載入成功</strong>
          <p className="muted">可能是網路中斷，或網站剛更新過。請重新整理；也可以先從上方選單前往其他頁面。</p>
          <p>
            <button type="button" className="btn" onClick={() => window.location.reload()}>
              重新整理
            </button>
          </p>
        </div>
      </div>
    );
  }
}
