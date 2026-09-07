## Change Summary

<!-- Explain the product or data-contract change in 2-4 sentences. -->

## Change Type

- [ ] Application / UI
- [ ] Analytics method
- [ ] Data pipeline
- [ ] Public processed data refresh
- [ ] Security / dependency
- [ ] Documentation

## Verification

- [ ] `run_project.bat --runtime-check`
- [ ] `run_project.bat --check` or equivalent locked-environment checks
- [ ] `python -m pytest -q`
- [ ] `python -m src.release_gate`
- [ ] `python -m pip check`
- [ ] `python -m bandit -r app.py src run_all.py -ll`
- [ ] `python -m pip_audit --local --strict`
- [ ] `git diff --check`

## Data Review

- [ ] Official CPBL source and `mode=api` confirmed
- [ ] Quality report is `pass` or warning is explained
- [ ] Snapshot ID and analysis validation report are aligned
- [ ] Player counts and data changes are explained
- [ ] No raw HTML, local path, secret, token, or temporary file is included

## UX / Reviewer Review

- [ ] Main user flow was tested from the home page
- [ ] Empty, error, loading, and disabled states were checked
- [ ] Desktop and mobile layout were checked
- [ ] README and supporting docs match the implementation
- [ ] Public deployment was not bundled into this change
