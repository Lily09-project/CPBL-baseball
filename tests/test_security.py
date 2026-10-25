import re
import subprocess
from pathlib import Path

from src.fetch_cpbl_data import absolute_url


ROOT = Path(__file__).resolve().parents[1]


def test_cpbl_profile_urls_are_restricted_to_https_official_host():
    assert absolute_url("/team/person?acnt=0000000001") == (
        "https://cpbl.com.tw/team/person?acnt=0000000001"
    )
    assert absolute_url("https://cpbl.com.tw/team/person?acnt=0000000001") == (
        "https://cpbl.com.tw/team/person?acnt=0000000001"
    )
    assert absolute_url("http://cpbl.com.tw/team/person?acnt=1") == ""
    assert absolute_url("https://example.invalid/team/person?acnt=1") == ""
    assert absolute_url("//example.invalid/team/person?acnt=1") == ""


def test_cpbl_profile_url_rejects_path_query_and_markdown_bypasses():
    rejected = [
        "https://cpbl.com.tw/news?acnt=0000000001",
        "https://cpbl.com.tw/team/person?acnt=0000000001&next=x",
        "https://cpbl.com.tw/team/person?acnt=0000000001#fragment",
        "https://cpbl.com.tw/team/person?acnt=0000000001)",
        "https://cpbl.com.tw/team/person?acnt=1",
    ]

    assert all(absolute_url(url) == "" for url in rejected)


def test_public_quality_report_does_not_expose_local_paths():
    report = Path("reports/metrics/data_quality_report.json").read_text(encoding="utf-8-sig")

    assert "C:\\\\Users\\\\" not in report
    assert "output_path" not in report


def test_repository_ignores_common_secret_and_internal_artifacts():
    ignore_text = Path(".gitignore").read_text(encoding="utf-8-sig")

    for entry in [".env", "*.pem", "*.key", "*.p12", "*.pfx", "data/raw/", "notes/", "web/node_modules/", "web/public/data/"]:
        assert entry in ignore_text


def test_secret_artifacts_are_effectively_ignored_by_git():
    candidates = [
        ".env",
        "example.pem",
        "example.key",
        "example.p12",
        "example.pfx",
        "data/raw/example.html",
        "notes/private-review.md",
        "web/node_modules/x/index.js",
        "web/dist/index.html",
    ]

    for candidate in candidates:
        subprocess.run(
            ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT), "check-ignore", "--no-index", "--quiet", "--", candidate],
            check=True,
        )


def test_dependency_floors_and_launcher_binding():
    requirements = Path("requirements.txt").read_text(encoding="utf-8-sig").lower()
    launcher = Path("run_project.bat").read_text(encoding="utf-8-sig").lower()

    for requirement in ["pandas>=3.0.5", "numpy>=2.5.2", "requests>=2.34.2", "lxml>=6.1.3", "urllib3>=2.8.0,<3", "certifi>=2026.10.19"]:
        assert requirement in requirements
    assert "streamlit" not in requirements
    assert "pip>=26.1.2" in launcher
    assert "packaging.requirements import requirement" in launcher
    assert "--host 127.0.0.1" in launcher
    assert "npm ci" in launcher


def test_web_app_declares_a_strict_content_security_policy():
    html = Path("web/index.html").read_text(encoding="utf-8")
    csp = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)
    assert csp, "web/index.html must declare a CSP"
    policy = csp.group(1)
    for directive in ["default-src 'self'", "script-src 'self'", "connect-src 'self'", "object-src 'none'", "base-uri 'self'"]:
        assert directive in policy
    assert "unsafe-eval" not in policy
    assert "<script>" not in html  # no inline scripts


def test_web_source_never_calls_third_party_hosts():
    allowed = {"www.cpbl.com.tw", "nodejs.org"}
    for path in Path("web/src").rglob("*.ts*"):
        if ".test." in path.name:
            continue  # tests deliberately contain attack strings such as example.invalid
        for host in re.findall(r"https?://([\w.-]+)", path.read_text(encoding="utf-8")):
            assert host in allowed, f"{path} references {host}"


def test_scheduled_data_health_check_is_read_only():
    workflow = Path(".github/workflows/data-health.yml").read_text(encoding="utf-8-sig")

    for required in [
        "schedule:",
        "workflow_dispatch:",
        "contents: read",
        "python -m src.verified_pipeline --mode api",
        "python -m pytest -q",
        "quality_status",
        "player_movements.csv",
    ]:
        assert required in workflow
    assert "contents: write" not in workflow
    assert "git push" not in workflow
    assert "git add" not in workflow


def test_security_workflow_scans_secrets_and_audits_both_ecosystems():
    workflow = Path(".github/workflows/security.yml").read_text(encoding="utf-8-sig")

    for required in [
        "contents: read",
        "gitleaks/gitleaks-action@",
        '"detect-secrets==1.5.0"',
        "git ls-files -z",
        "snapshot_id|previous_snapshot_id|relative_path",
        "python -m pip_audit --local --strict",
        "python -m bandit -r src run_all.py -ll",
        "npm audit --audit-level=low",
        "python -m pytest -q",
    ]:
        assert required in workflow
