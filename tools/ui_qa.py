from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode, urlsplit


PAGE_CONTRACTS = (
    "資料訊號總覽",
    "聯盟總覽",
    "版本趨勢",
    "分析驗證",
    "球探工作台",
    "球探報告",
    "球員排行榜",
    "球員個人頁",
    "投打對決",
    "分項排行",
)
CORE_VIEWPORTS = (
    ("desktop", 1440, 1000),
    ("small-mobile", 375, 812),
    ("tablet", 768, 1024),
    ("landscape", 844, 390),
    ("wide-tablet", 1024, 768),
)
EXTENDED_VIEWPORTS = (
    ("tiny-mobile", 320, 568),
    ("large-mobile", 414, 896),
)
VIEWPORTS = CORE_VIEWPORTS
STREAMLIT_EXCEPTION_SELECTOR = '[data-testid="stException"]'
TEXT_SCALE_CSS = ":root { font-size: 200% !important; }"
THEME_OPTION_LABELS = {"light":"淺色","dark":"深色"}
# WCAG-friendly touch target floor for user-facing controls. Streamlit's
# internal toolbar/header controls are explicitly excluded below.
MIN_INTERACTIVE_TARGET_PX = 44


def viewport_matrix(extended: bool = False) -> tuple[tuple[str, int, int], ...]:
    return CORE_VIEWPORTS + EXTENDED_VIEWPORTS if extended else CORE_VIEWPORTS


def layout_issues(page) -> list[str]:
    """Return observable layout/accessibility defects from the rendered page."""
    return page.evaluate(
        """() => {
            const issues = [];
            const visible = (element) => {
                const rect = element.getBoundingClientRect();
                const style = getComputedStyle(element);
                return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                    && style.visibility !== 'hidden';
            };
            const main = document.querySelector('#cpbl-main, main');
            const heading = main?.querySelector('h1') || document.querySelector('h1');
            if (!heading || !visible(heading)) {
                issues.push('main heading is missing or hidden');
            } else {
                const rect = heading.getBoundingClientRect();
                const inViewport = rect.bottom > 0 && rect.top < window.innerHeight;
                if (inViewport) {
                    const x = Math.min(window.innerWidth - 1, Math.max(1, rect.left + rect.width / 2));
                    const y = Math.min(window.innerHeight - 1, Math.max(1, rect.top + rect.height / 2));
                    const top = document.elementFromPoint(x, y);
                    if (!top || (!heading.contains(top) && !top.contains(heading))) {
                        issues.push('main heading is obscured');
                    }
                }
            }
            for (const control of document.querySelectorAll('button[data-testid^="stBaseButton"], [data-testid="stButton"] button, select, textarea')) {
                if (!visible(control)) continue;
                const rect = control.getBoundingClientRect();
                const inViewport = rect.right > 0 && rect.left < window.innerWidth
                    && rect.bottom > 0 && rect.top < window.innerHeight;
                const testId = control.getAttribute('data-testid') || '';
                if (!inViewport || testId === 'stBaseButton-elementToolbar'
                    || testId.startsWith('stBaseButton-header')) continue;
                if (rect.width < 44 || rect.height < 44) {
                    issues.push(`small interactive target: ${control.tagName}`);
                    break;
                }
            }
            for (const element of document.querySelectorAll('button, [role="button"]')) {
                if (!visible(element)) continue;
                const style = getComputedStyle(element);
                if ((style.overflow === 'hidden' || style.overflowX === 'hidden' || style.overflowY === 'hidden')
                    && (element.scrollWidth > element.clientWidth + 3 || element.scrollHeight > element.clientHeight + 3)) {
                    issues.push('interactive label is clipped');
                    break;
                }
            }
            return issues;
        }"""
    )


def wait_for_app_idle(page) -> None:
    """Synchronize with Streamlit reruns before judging rendered UI or uploading."""
    # Widgets debounce before starting a rerun; wait for the actual completion
    # state and removed skeletons, as Streamlit's own browser tests do.
    page.wait_for_timeout(250)
    page.locator(
        '[data-testid="stApp"][data-test-connection-state="CONNECTED"]'
        '[data-test-script-state="notRunning"]'
    ).wait_for(state="attached", timeout=60_000)
    page.wait_for_function(
        "() => document.querySelectorAll('[data-testid=stSkeleton]').length === 0",
        timeout=60_000,
    )
    page.wait_for_timeout(100)


def focus_issues(page) -> list[str]:
    """Traverse real Tab order, validating visible controls and their focused proxies."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    wait_for_app_idle(page)
    issues: list[str] = []
    page.evaluate(
        """() => {
            document.activeElement?.blur();
            document.body.setAttribute('tabindex', '-1');
            document.body.focus();
            document.body.removeAttribute('tabindex');
            window.scrollTo(0, 0);
        }"""
    )
    reached_skip_link = False
    reached_interactive_control = False
    visited: set[str] = set()
    visited_order: list[str] = []

    for _attempt in range(24):
        page.keyboard.press("Tab")
        try:
            page.wait_for_function(
                """() => {
                    const target = document.activeElement;
                    if (!target || !target.matches('a.skip-link')) return true;
                    if (!target.matches(':focus-visible')) return false;
                    const transform = getComputedStyle(target).transform;
                    return transform === 'none'
                        || Math.abs(new DOMMatrixReadOnly(transform).m42) < 1;
                }""",
                timeout=2_000,
            )
        except PlaywrightTimeoutError:
            pass

        state = page.evaluate(
            """() => {
                const inViewport = rect => rect.right > 0 && rect.left < window.innerWidth
                    && rect.bottom > 0 && rect.top < window.innerHeight;
                const rendered = element => {
                    if (!element || !(element instanceof Element)) return false;
                    const rect = element.getBoundingClientRect();
                    if (rect.width <= 0 || rect.height <= 0) return false;
                    for (let node = element; node && node instanceof HTMLElement; node = node.parentElement) {
                        const style = getComputedStyle(node);
                        if (style.display === 'none' || style.visibility === 'hidden'
                                || Number(style.opacity) === 0) return false;
                    }
                    return true;
                };
                const target = document.activeElement;
                if (!target || target === document.body) {
                    return {key: '', skipLink: false, interactive: false, issue: ''};
                }

                const targetRect = target.getBoundingClientRect();
                const targetStyle = getComputedStyle(target);
                const isRadio = target.matches('input[type="radio"]');
                const radioItem = isRadio
                    ? target.closest('[data-baseweb="radio"], [role="radio"], label')
                    : null;
                const radioWidget = isRadio
                    ? target.closest('[data-testid="stRadio"], [role="radiogroup"], [data-baseweb="radio"]')
                    : null;
                const associatedLabel = isRadio
                    ? Array.from(target.labels || []).find(label => rendered(label))
                    : null;
                const proxy = associatedLabel || radioItem;
                const proxyText = proxy
                    ? (proxy.getAttribute('aria-label') || proxy.innerText || proxy.textContent || '').trim()
                    : '';
                const namedProxy = Boolean(proxy && (
                    proxy.getAttribute('aria-label') || proxy.getAttribute('aria-labelledby') || proxyText
                ));
                const hiddenRadioInput = isRadio && (
                    targetRect.width <= 1 || targetRect.height <= 1
                    || targetStyle.display === 'none' || targetStyle.visibility === 'hidden'
                    || Number(targetStyle.opacity) === 0 || !inViewport(targetRect)
                );
                const usesProxy = Boolean(
                    hiddenRadioInput && radioWidget && radioItem && proxy && proxy !== target
                    && namedProxy && rendered(proxy)
                );
                const visualTarget = usesProxy ? proxy : target;
                const rect = visualTarget.getBoundingClientRect();
                const style = getComputedStyle(visualTarget);
                const details = JSON.stringify({
                    focusedTag: target.tagName,
                    focusedRect: [Math.round(targetRect.left), Math.round(targetRect.top),
                        Math.round(targetRect.right), Math.round(targetRect.bottom)],
                    visibleTarget: visualTarget.tagName,
                    label: proxyText.slice(0, 80),
                    visibleRect: [Math.round(rect.left), Math.round(rect.top),
                        Math.round(rect.right), Math.round(rect.bottom)],
                    display: style.display,
                    visibility: style.visibility,
                    position: style.position,
                    transform: style.transform,
                    occluder: (() => {
                        const top = document.elementFromPoint(Math.max(1, Math.min(innerWidth - 1, rect.left + rect.width / 2)), Math.max(1, Math.min(innerHeight - 1, rect.top + rect.height / 2)));
                        return top ? top.outerHTML.slice(0, 500) : null;
                    })(),
                });
                const key = [
                    target.tagName, target.id || '', target.getAttribute('data-testid') || '',
                    target.getAttribute('aria-label') || '', target.type || '', target.value || '',
                    proxyText.slice(0, 80), (target.textContent || '').trim().slice(0, 40),
                ].join('|');

                if (!rendered(visualTarget)) {
                    const message = usesProxy ? 'radio proxy is hidden' : 'keyboard-focused target is hidden';
                    return {key, skipLink: false, interactive: false, issue: message + ' (' + details + ')'};
                }
                if (!inViewport(rect)) {
                    return {key, skipLink: false, interactive: false, issue: 'keyboard-focused target is outside viewport (' + details + ')'};
                }
                if (!target.matches(':focus-visible')) {
                    return {key, skipLink: false, interactive: false, issue: 'keyboard-focused target lacks focus-visible state (' + details + ')'};
                }
                if (usesProxy) {
                    const width = Number.parseFloat(style.outlineWidth || '0');
                    const color = style.outlineColor;
                    if (width < 2 || style.outlineStyle === 'none'
                            || color === 'transparent' || color === 'rgba(0, 0, 0, 0)') {
                        return {
                            key,
                            skipLink: false,
                            interactive: false,
                            issue: 'keyboard-focused radio proxy lacks a visible focus indicator (' + details + ')',
                        };
                    }
                }

                const x = Math.min(window.innerWidth - 1, Math.max(1, rect.left + rect.width / 2));
                const y = Math.min(window.innerHeight - 1, Math.max(1, rect.top + rect.height / 2));
                const top = document.elementFromPoint(x, y);
                const widget = visualTarget.closest('[data-baseweb], [data-testid], [role="radiogroup"]');
                const topWidget = top?.closest('[data-baseweb], [data-testid], [role="radiogroup"]');
                const unobscured = usesProxy
                    ? Boolean(top && (visualTarget.contains(top) || top.contains(visualTarget)))
                    : Boolean(top && (
                        visualTarget.contains(top) || top.contains(visualTarget)
                        || (widget && topWidget && widget === topWidget)
                    ));
                if (!unobscured) {
                    return {key, skipLink: false, interactive: false, issue: 'keyboard-focused target is obscured (' + details + ')'};
                }

                const skipLink = visualTarget.matches('a.skip-link');
                const interactive = usesProxy || (
                    !skipLink && target.matches(
                        'a[href], button, input, select, textarea, [role="button"], [tabindex]'
                    )
                );
                return {key, skipLink, interactive, issue: ''};
            }"""
        )
        key = str(state.get("key", ""))
        if not key or key in visited:
            continue
        visited.add(key)
        visited_order.append(key)
        if state.get("issue"):
            issues.append(f"{state['issue']}: {key}")
        reached_skip_link = reached_skip_link or bool(state.get("skipLink"))
        reached_interactive_control = reached_interactive_control or bool(
            state.get("interactive")
        )
        if reached_skip_link and reached_interactive_control:
            break

    if not reached_skip_link:
        traversal = " -> ".join(visited_order[:8]) or "(none)"
        issues.append(f"keyboard focus did not reach the skip link; visited: {traversal}")
    if not reached_interactive_control:
        issues.append("keyboard focus did not reach an interactive control")
    return issues

def interaction_smoke(page, base_url: str) -> list[str]:
    """Exercise the reviewer path: nav -> player profile -> return."""
    from playwright.sync_api import Error as PlaywrightError

    failures: list[str] = []
    page.goto(f"{base_url.rstrip('/')}/?page=球探工作台", wait_until="domcontentloaded", timeout=60_000)
    page.get_by_role("heading", name="球探工作台", exact=True).wait_for(timeout=60_000)
    sidebar = page.locator('[data-testid="stSidebar"]')
    try:
        if sidebar.get_attribute("aria-expanded") != "true":
            expand_control = page.locator('[data-testid="stExpandSidebarButton"]')
            expand_button = expand_control.locator("button")
            if expand_button.count():
                expand_button.click(timeout=15_000)
            else:
                expand_control.click(timeout=15_000)
            page.wait_for_function(
                "() => document.querySelector('[data-testid=stSidebar]')?.getAttribute('aria-expanded') === 'true'",
                timeout=30_000,
            )
    except PlaywrightError:
        failures.append("sidebar did not open through its expand control")
    labels = sidebar.locator('[data-testid="stRadio"] label')
    try:
        page.wait_for_function(
            "expected => document.querySelectorAll('[data-testid=\\\"stSidebar\\\"] [data-testid=\\\"stRadio\\\"] label').length >= expected",
            arg=len(PAGE_CONTRACTS),
            timeout=60_000,
        )
    except PlaywrightError:
        failures.append("sidebar navigation did not finish loading")
    if labels.count() < len(PAGE_CONTRACTS):
        failures.append("sidebar navigation did not expose every public page")
    for label in labels.all():
        if not label.inner_text().strip():
            failures.append("sidebar navigation contains an unlabeled item")
            break
    player_option = labels.filter(has_text="球員個人頁").first
    if not player_option.count():
        failures.append("球員個人頁 navigation option missing")
    else:
        player_option.click()
        try:
            page.get_by_role("heading", name="球員個人頁", exact=True).wait_for(timeout=60_000)
        except PlaywrightError:
            failures.append("navigation did not reach 球員個人頁")
    workbench_option = labels.filter(has_text="球探工作台").first
    if workbench_option.count():
        workbench_option.click()
        try:
            page.get_by_role("heading", name="球探工作台", exact=True).wait_for(timeout=60_000)
        except PlaywrightError:
            failures.append("navigation did not return to 球探工作台")
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    if overflow > 4:
        failures.append(f"interaction flow introduced horizontal overflow: {overflow}px")
    return failures


def failure_screenshot_names(screenshot_dir: Path, error: str) -> list[str]:
    names = {path.name for path in screenshot_dir.glob("failure-*.png")}
    for failure in error.split("; "):
        scope = failure.split(":", 1)[0]
        if "/" not in scope:
            continue
        viewport, route = scope.split("/", 1)
        candidate = screenshot_dir / f"{route}-{viewport}.png"
        if candidate.is_file():
            names.add(candidate.name)
    return sorted(names)


def write_failure_evidence(base_url: str, screenshot_dir: Path, error: str) -> Path:
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = screenshot_dir / "failure-evidence.json"
    payload = {
        "schema_version": "1.0",
        "status": "failed",
        "base_url": base_url,
        "error": error,
        "screenshots": failure_screenshot_names(screenshot_dir, error),
    }
    temporary = evidence_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(evidence_path)
    return evidence_path


def check_health(base_url: str) -> None:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("UI QA URL must use http(s) with a host")
    with urllib.request.urlopen(  # nosec B310 - scheme and host are validated above
        f"{base_url.rstrip('/')}/_stcore/health", timeout=5
    ) as response:
        body = response.read(4096).decode("utf-8", errors="replace")
    if "ok" not in body.lower():
        raise RuntimeError(f"Unexpected Streamlit health response: {body[:200]}")


def apply_theme_mode(
    page,
    theme_mode: str | None,
    *,
    selector_label: str | None = None,
    option_labels: dict[str, str] | None = None,
) -> None:
    if theme_mode is None:
        return
    if theme_mode not in {"light", "dark"}:
        raise ValueError("theme_mode must be light or dark")
    current_theme = page.evaluate(
        "getComputedStyle(document.documentElement).colorScheme"
    )
    if selector_label is not None and current_theme != theme_mode:
        sidebar = page.locator('[data-testid="stSidebar"]')
        if sidebar.get_attribute("aria-expanded") != "true":
            expand_control = page.locator('[data-testid="stExpandSidebarButton"]')
            expand_button = expand_control.locator("button")
            if expand_button.count():
                expand_button.click(timeout=15_000)
            else:
                expand_control.click(timeout=15_000)
        option_label = (option_labels or {}).get(theme_mode)
        if not option_label:
            raise ValueError(f"missing app theme label for {theme_mode}")
        selector = page.get_by_role("combobox", name=selector_label)
        selector.scroll_into_view_if_needed(timeout=15_000)
        selector.click(timeout=15_000)
        option = page.get_by_role("option", name=option_label, exact=True)
        option.wait_for(state="visible", timeout=15_000)
        # Use absolute keyboard navigation because Streamlit may detach a menu
        # option during a pointer click. The app's theme options are ordered
        # dark, then light.
        page.keyboard.press("Home")
        if theme_mode == "light":
            page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        collapse_button = page.locator('[data-testid="stSidebarCollapseButton"] button')
        if sidebar.get_attribute("aria-expanded") == "true" and collapse_button.count():
            collapse_button.click(timeout=15_000)
    page.wait_for_function(
        "expected => getComputedStyle(document.documentElement).colorScheme === expected",
        arg=theme_mode,
        timeout=15_000,
    )


def download_payload(page, label: str, suffix: str) -> bytes:
    """Read the real browser download, not the button's presence or URL."""
    wait_for_app_idle(page)
    with page.expect_download(timeout=30_000) as pending:
        page.get_by_role("button", name=label).click(timeout=30_000)
    download = pending.value
    failure = download.failure()
    if failure or not download.suggested_filename.endswith(suffix):
        raise RuntimeError(f"download failed or unexpected filename: {label}: {failure}")
    path = download.path()
    if path is None:
        raise RuntimeError(f"download has no readable payload: {label}")
    payload = Path(path).read_bytes()
    if not payload:
        raise RuntimeError(f"download is empty: {label}")
    return payload


def open_sidebar(page) -> None:
    sidebar = page.locator('[data-testid="stSidebar"]')
    if sidebar.get_attribute("aria-expanded") != "true":
        control = page.locator('[data-testid="stExpandSidebarButton"]')
        button = control.locator("button")
        (button if button.count() else control).click(timeout=15_000)
    page.wait_for_function(
        "() => document.querySelector('[data-testid=stSidebar]')?.getAttribute('aria-expanded') === 'true'",
        timeout=15_000,
    )


def choose_option(page, label: str, value: str) -> None:
    selector = page.get_by_role("combobox", name=label)
    selector.scroll_into_view_if_needed()
    selector.click()
    page.get_by_role("option", name=value, exact=True).click()
    page.keyboard.press("Escape")
    wait_for_app_idle(page)


def functional_download_smoke(page, base_url: str, theme_mode: str | None) -> None:
    import csv
    import re
    from io import StringIO

    root = str(Path(__file__).resolve().parents[1])
    if root not in sys.path:
        sys.path.insert(0, root)
    from src.scouting_report import verify_report_manifest

    page.goto(f"{base_url.rstrip('/')}/?{urlencode({'page': '球探報告'})}", wait_until="domcontentloaded", timeout=60_000)
    page.get_by_role("heading", name="球探報告", exact=True).wait_for(timeout=60_000)
    apply_theme_mode(page, theme_mode, selector_label="介面主題", option_labels=THEME_OPTION_LABELS)
    threshold = page.get_by_role("spinbutton", name="最低打席 (PA)", exact=True)
    threshold.fill("50")
    threshold.press("Enter")
    wait_for_app_idle(page)
    page.get_by_role("button", name="清除觀察名單").click()
    wait_for_app_idle(page)
    selected_labels: list[str] = []
    for _ in range(2):
        selector = page.get_by_role("combobox", name="觀察名單")
        selector.scroll_into_view_if_needed()
        selector.click()
        # Streamlit includes a bulk "Select all" row. Choose only a real
        # player option carrying its stable ten-digit identity.
        options = page.get_by_role("option").filter(has_text=re.compile(r" · \d{10}\s*$"))
        for selected_label in selected_labels:
            # The menu can retain selected rows; clicking one again removes it.
            options = options.filter(has_not_text=re.compile(re.escape(selected_label)))
        option = options.first
        option.wait_for(state="visible", timeout=15_000)
        label = option.inner_text()
        option.click()
        page.keyboard.press("Escape")
        selected_labels.append(label)
        page.locator(".st-key-report_watchlist_打者").get_by_text(label, exact=True).wait_for(timeout=30_000)
        wait_for_app_idle(page)
        for selected_label in selected_labels:
            page.locator(".st-key-report_watchlist_打者").get_by_text(selected_label, exact=True).wait_for(timeout=30_000)
    manifest = json.loads(download_payload(page, "下載稽核 Manifest JSON", ".json"))
    verified = verify_report_manifest(manifest)
    markdown = download_payload(page, "下載球探報告 Markdown", ".md").decode("utf-8")
    csv_payload = download_payload(page, "下載球探報告 CSV", ".csv")
    rows = list(csv.DictReader(StringIO(csv_payload.decode("utf-8-sig"))))
    players = manifest["players"]
    ids = [str(player["player_id"]) for player in players]
    if verified["player_count"] != 2 or manifest["analysis"]["qualification"] != "PA ≥ 50":
        raise RuntimeError("CPBL report lost the selected threshold or watchlist")
    if ids != [label.rsplit(" · ", 1)[-1].strip() for label in selected_labels]:
        raise RuntimeError("CPBL report changed the chosen player identities or order")
    if [row["球員 ID"] for row in rows] != ids or any(float(row["資格量"]) < 50 for row in rows):
        raise RuntimeError("CPBL report CSV disagrees with the verified manifest")
    if manifest["report_id"] not in markdown or any(player_id not in markdown for player_id in ids):
        raise RuntimeError("CPBL Markdown lost its report identity or selected players")
    page.get_by_role("button", name="清除觀察名單").click()
    wait_for_app_idle(page)
    page.get_by_text("選擇候選球員後，這裡會產生可下載的球探報告。", exact=True).wait_for(timeout=30_000)
    if page.get_by_role("button", name="下載稽核 Manifest JSON").count():
        raise RuntimeError("cleared watchlist still offers a stale report download")



def run_browser_checks(
    base_url: str,
    screenshot_dir: Path,
    extended: bool = False,
    text_scale: bool = False,
    theme_mode: str | None = None,
) -> str:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("install requirements-e2e.txt before browser QA") from exc

    screenshot_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for viewport_name, width, height in viewport_matrix(extended):
            context = browser.new_context(viewport={"width": width, "height": height})
            try:
                for page_name in PAGE_CONTRACTS:
                    page = context.new_page()
                    console_errors: list[str] = []
                    page.on(
                        "console",
                        lambda message, errors=console_errors: errors.append(message.text)
                        if message.type == "error"
                        else None,
                    )
                    page.on("pageerror", lambda error, errors=console_errors: errors.append(str(error)))
                    try:
                        if theme_mode is None:
                            page.emulate_media(reduced_motion="reduce")
                        else:
                            page.emulate_media(reduced_motion="reduce", color_scheme=theme_mode)
                        url = f"{base_url.rstrip('/')}/?{urlencode({'page': page_name})}"
                        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                        page.get_by_role("heading", name=page_name, exact=True).wait_for(timeout=60_000)
                        apply_theme_mode(
                            page,
                            theme_mode,
                            selector_label="介面主題",
                            option_labels=THEME_OPTION_LABELS,
                        )
                        skip_link = page.locator('a.skip-link[href="#cpbl-main"]')
                        main_anchor = page.locator("#cpbl-main")
                        try:
                            skip_link.wait_for(state="attached", timeout=10_000)
                            main_anchor.wait_for(state="attached", timeout=10_000)
                        except PlaywrightError:
                            pass
                        if skip_link.count() != 1:
                            failures.append(f"{viewport_name}/{page_name}: missing skip link")
                        if main_anchor.count() != 1:
                            failures.append(f"{viewport_name}/{page_name}: missing main-content anchor")
                        if text_scale:
                            page.add_style_tag(content=TEXT_SCALE_CSS)
                            page.wait_for_timeout(250)
                        if page.locator(STREAMLIT_EXCEPTION_SELECTOR).count():
                            failures.append(f"{viewport_name}/{page_name}: Streamlit runtime exception")
                        overflow = page.evaluate(
                            "document.documentElement.scrollWidth - window.innerWidth"
                        )
                        if overflow > 4:
                            failures.append(
                                f"{viewport_name}/{page_name}: horizontal overflow {overflow}px"
                            )
                        for issue in layout_issues(page):
                            failures.append(f"{viewport_name}/{page_name}: {issue}")
                        for issue in focus_issues(page):
                            failures.append(f"{viewport_name}/{page_name}: {issue}")
                        page.evaluate("document.activeElement?.blur()")
                        if console_errors:
                            failures.append(
                                f"{viewport_name}/{page_name}: console errors {console_errors[:3]}"
                            )
                        suffix = "-text-200" if text_scale else ""
                        page.screenshot(
                            path=str(screenshot_dir / f"{page_name}-{viewport_name}{suffix}.png"),
                            full_page=True,
                        )
                    except PlaywrightError as exc:
                        failures.append(f"{viewport_name}/{page_name}: browser error {exc}")
                        try:
                            page.screenshot(
                                path=str(screenshot_dir / f"failure-{page_name}-{viewport_name}.png"),
                                full_page=True,
                            )
                        except PlaywrightError:
                            pass
                    finally:
                        try:
                            page.wait_for_timeout(50)
                        except PlaywrightError:
                            pass
                        page.close()
            finally:
                context.close()
        interaction_page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            interaction_page.emulate_media(reduced_motion="reduce")
            failures.extend(interaction_smoke(interaction_page, base_url))
        except PlaywrightError as exc:
            failures.append(f"interaction flow browser error: {exc}")
        finally:
            interaction_page.close()

        for flow_name, flow_width, flow_height in (
            ("desktop", 1440, 1000),
            ("mobile", 320 if extended else 375, 812),
        ):
            flow_page = browser.new_page(viewport={"width": flow_width, "height": flow_height}, accept_downloads=True)
            try:
                if theme_mode is None:
                    flow_page.emulate_media(reduced_motion="reduce")
                else:
                    flow_page.emulate_media(reduced_motion="reduce", color_scheme=theme_mode)
                functional_download_smoke(flow_page, base_url, theme_mode)
                if flow_page.locator(STREAMLIT_EXCEPTION_SELECTOR).count():
                    failures.append(f"{flow_name}/downloads: Streamlit runtime exception")
            except (PlaywrightError, RuntimeError, ValueError, OSError) as exc:
                failures.append(f"{flow_name}/downloads: {exc}")
                print(f"DOWNLOAD FAILURE DOM ({flow_name}): {flow_page.locator('body').inner_text()[-8000:]}")
                flow_page.screenshot(path=str(screenshot_dir / f"failure-downloads-{flow_name}.png"), full_page=True)
            finally:
                flow_page.close()
        browser.close()
    if failures:
        raise RuntimeError("; ".join(failures[:20]))
    text_note = ", 200% text reflow" if text_scale else ""
    return f"PASS: {len(PAGE_CONTRACTS)} routes × {len(viewport_matrix(extended))} viewports, accessibility, overflow, runtime, and console checks{text_note}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CPBL Streamlit browser QA.")
    parser.add_argument("--url", default="http://127.0.0.1:8852")
    parser.add_argument("--screenshots", default="docs/screenshots/ui-qa")
    parser.add_argument(
        "--extended",
        action="store_true",
        help="also run 320px and 414px mobile viewports",
    )
    parser.add_argument(
        "--text-scale",
        action="store_true",
        help="apply 200% root text scaling and rerun reflow checks",
    )
    parser.add_argument("--theme-mode", choices=("light", "dark"))
    args = parser.parse_args()
    screenshot_dir = Path(args.screenshots)
    (screenshot_dir / "failure-evidence.json").unlink(missing_ok=True)
    for stale in screenshot_dir.glob("failure-*.png"):
        stale.unlink(missing_ok=True)
    try:
        check_health(args.url)
        result = run_browser_checks(
            args.url,
            screenshot_dir,
            extended=args.extended,
            text_scale=args.text_scale,
            theme_mode=args.theme_mode,
        )
    except (OSError, urllib.error.URLError, RuntimeError, ValueError) as exc:
        evidence = write_failure_evidence(args.url, screenshot_dir, str(exc))
        print(f"FAIL: {exc}")
        print(f"EVIDENCE: {evidence}")
        return 1
    (screenshot_dir / "failure-evidence.json").unlink(missing_ok=True)
    print(json.dumps({"health": "PASS", "browser": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
