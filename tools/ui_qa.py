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
                if (rect.width < 24 || rect.height < 24) {
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


def focus_issues(page) -> list[str]:
    """Verify a keyboard-focus target remains visible and unobscured."""
    return page.evaluate(
        """() => {
            const visible = (element) => {
                const rect = element.getBoundingClientRect();
                const style = getComputedStyle(element);
                return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                    && style.visibility !== 'hidden';
            };
            const inViewportTarget = (element) => {
                const rect = element.getBoundingClientRect();
                return rect.right > 0 && rect.left < window.innerWidth
                    && rect.bottom > 0 && rect.top < window.innerHeight;
            };
            const target = [...document.querySelectorAll('button, [role="button"], select, textarea')]
                .find((element) => visible(element) && inViewportTarget(element));
            if (!target) {
                const skipLink = document.querySelector('a.skip-link');
                if (!skipLink) return ['no keyboard-focus target'];
                skipLink.focus({preventScroll: true});
                return document.activeElement === skipLink ? [] : ['focus did not move to skip link'];
            }
            target.focus({preventScroll: true});
            if (document.activeElement !== target) return ['focus did not move to target'];
            const rect = target.getBoundingClientRect();
            const inViewport = rect.right > 0 && rect.left < window.innerWidth
                && rect.bottom > 0 && rect.top < window.innerHeight;
            if (!inViewport) return ['focused target is outside viewport'];
            const x = Math.min(window.innerWidth - 1, Math.max(1, rect.left + rect.width / 2));
            const y = Math.min(window.innerHeight - 1, Math.max(1, rect.top + rect.height / 2));
            const top = document.elementFromPoint(x, y);
            if (!top || (!target.contains(top) && !top.contains(target))) {
                return ['focused target is obscured'];
            }
            return [];
        }"""
    )


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


def run_browser_checks(
    base_url: str,
    screenshot_dir: Path,
    extended: bool = False,
    text_scale: bool = False,
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
                        page.emulate_media(reduced_motion="reduce")
                        url = f"{base_url.rstrip('/')}/?{urlencode({'page': page_name})}"
                        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                        page.get_by_role("heading", name=page_name, exact=True).wait_for(timeout=60_000)
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
