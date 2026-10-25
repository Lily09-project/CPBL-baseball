# Security Policy

## Reporting a Vulnerability

Please use GitHub's private vulnerability reporting or a private security advisory for this repository. Do not publish credentials, exploit details, or personal information in a public issue.

Include the affected file or feature, reproduction steps, impact, and any suggested mitigation. Public CPBL statistics and player profile identifiers in `data/processed/` are sourced from the official CPBL website and are not application credentials.

Official-page ingestion requires HTTPS CPBL hosts, rejects redirects, and reads responses through an 8 MiB bounded stream before parsing. The verification token used by the official statistics form is never sent to a redirected origin.

The static web app declares a strict Content-Security-Policy (no inline or third-party scripts, `connect-src 'self'`), verifies every data file against the SHA-256 manifest with Web Crypto before use, makes no runtime requests to third-party hosts, and neutralises spreadsheet formulas in CSV exports.

## Supported Version

Security fixes are applied to the latest commit on `main`.
