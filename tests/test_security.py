import csv
from io import StringIO
from pathlib import Path
import subprocess
import tomllib

import pandas as pd

from app import dataframe_to_csv_bytes
from src.fetch_cpbl_data import absolute_url


def test_csv_export_neutralizes_spreadsheet_formulas():
    source = pd.DataFrame(
        {
            "內容": [
                "=HYPERLINK(\"https://example.invalid\")",
                "+SUM(1,2)",
                "-2+3",
                "@SUM(1,2)",
                "\t=1+1",
                "一般文字",
                "-",
                7,
            ]
        }
    )

    exported = dataframe_to_csv_bytes(source).decode("utf-8-sig")
    values = [row["內容"] for row in csv.DictReader(StringIO(exported))]

    assert all(value.startswith("'") for value in values[:5])
    assert values[5:] == ["一般文字", "-", "7"]


def test_cpbl_profile_urls_are_restricted_to_https_official_host():
    assert absolute_url("/team/person?acnt=0000000001") == (
        "https://www.cpbl.com.tw/team/person?acnt=0000000001"
    )
    assert absolute_url("https://www.cpbl.com.tw/team/person?acnt=0000000001") == (
        "https://www.cpbl.com.tw/team/person?acnt=0000000001"
    )
    assert absolute_url("http://www.cpbl.com.tw/team/person?acnt=1") == ""
    assert absolute_url("https://example.invalid/team/person?acnt=1") == ""
    assert absolute_url("//example.invalid/team/person?acnt=1") == ""


def test_repository_ignores_common_secret_and_internal_artifacts():
    ignore_text = Path(".gitignore").read_text(encoding="utf-8-sig")

    for entry in [
        ".env",
        ".streamlit/secrets.toml",
        "*.pem",
        "*.key",
        "*.p12",
        "*.pfx",
        "data/raw/",
        "notes/source_prompt.txt",
    ]:
        assert entry in ignore_text


def test_launcher_enforces_secure_dependency_floors_and_loopback_binding():
    requirements = Path("requirements.txt").read_text(encoding="utf-8-sig").lower()
    launcher = Path("run_project.bat").read_text(encoding="utf-8-sig").lower()

    for requirement in [
        "streamlit>=1.58.0",
        "pandas>=3.0.5",
        "numpy>=2.5.1",
        "plotly>=6.9.0",
        "requests>=2.34.2",
        "pytest>=9.1.1",
        "lxml>=6.1.1",
        "gitpython>=3.1.57",
        "pillow>=12.3.0",
    ]:
        assert requirement in requirements
    assert "pip>=26.1.2" in launcher
    assert "packaging.requirements import requirement" in launcher
    assert "--server.address 127.0.0.1" in launcher


def test_csv_export_neutralizes_headers_and_whitespace_bypasses():
    source = pd.DataFrame(
        {
            "=FORMULA": [
                " =1+1",
                "\n@SUM(1,2)",
                "\v-2+3",
                "\f+1",
                " normal text",
            ]
        }
    )

    exported = dataframe_to_csv_bytes(source).decode("utf-8-sig")
    rows = list(csv.reader(StringIO(exported)))

    assert rows[0] == ["'=FORMULA"]
    assert all(row[0].startswith("'") for row in rows[1:5])
    assert rows[5] == [" normal text"]


def test_cpbl_profile_url_rejects_path_query_and_markdown_bypasses():
    rejected = [
        "https://www.cpbl.com.tw/news?acnt=0000000001",
        "https://www.cpbl.com.tw/team/person?acnt=0000000001&next=x",
        "https://www.cpbl.com.tw/team/person?acnt=0000000001#fragment",
        "https://www.cpbl.com.tw/team/person?acnt=0000000001)",
        "https://www.cpbl.com.tw/team/person?acnt=1",
    ]

    assert all(absolute_url(url) == "" for url in rejected)


def test_secret_artifacts_are_effectively_ignored_by_git():
    candidates = [
        ".env",
        ".streamlit/secrets.toml",
        "example.pem",
        "example.key",
        "example.p12",
        "example.pfx",
        "data/raw/example.html",
        "notes/source_prompt.txt",
    ]

    for candidate in candidates:
        subprocess.run(
            ["git", "check-ignore", "--no-index", "--quiet", "--", candidate],
            check=True,
        )


def test_streamlit_defaults_to_loopback_and_ci_runs_tests():
    config = tomllib.loads(Path(".streamlit/config.toml").read_text(encoding="utf-8-sig"))
    assert config["server"]["address"] == "127.0.0.1"

    workflow = Path(".github/workflows/security.yml").read_text(encoding="utf-8-sig")
