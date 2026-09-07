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
VIEWPORTS = (
    ("desktop", 1440, 1000),
    ("small-mobile", 375, 812),
    ("landscape", 844, 390),
)
STREAMLIT_EXCEPTION_SELECTOR = '[data-testid="stException"]'


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


def run_browser_checks(base_url: str, screenshot_dir: Path) -> str:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("install requirements-e2e.txt before browser QA") from exc

    screenshot_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for viewport_name, width, height in VIEWPORTS:
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
                        if page.locator(STREAMLIT_EXCEPTION_SELECTOR).count():
                            failures.append(f"{viewport_name}/{page_name}: Streamlit runtime exception")
                        overflow = page.evaluate(
                            "document.documentElement.scrollWidth - window.innerWidth"
                        )
                        if overflow > 4:
                            failures.append(
                                f"{viewport_name}/{page_name}: horizontal overflow {overflow}px"
                            )
                        if console_errors:
                            failures.append(
                                f"{viewport_name}/{page_name}: console errors {console_errors[:3]}"
                            )
                        page.screenshot(
                            path=str(screenshot_dir / f"{page_name}-{viewport_name}.png"),
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
    return "PASS: 10 routes × 3 viewports, accessibility, overflow, runtime, and console checks"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CPBL Streamlit browser QA.")
    parser.add_argument("--url", default="http://127.0.0.1:8852")
    parser.add_argument("--screenshots", default="docs/screenshots/ui-qa")
    args = parser.parse_args()
    screenshot_dir = Path(args.screenshots)
    (screenshot_dir / "failure-evidence.json").unlink(missing_ok=True)
    for stale in screenshot_dir.glob("failure-*.png"):
        stale.unlink(missing_ok=True)
    try:
        check_health(args.url)
        result = run_browser_checks(args.url, screenshot_dir)
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
