# Changelog

## 2026-11-11

**Adopt the shared Python tooling (branch `claude/project-thread-iw7199`)**

Asked for as part of rolling the same Python stack out to every project.

- `pyproject.toml`: dev dependency group (pytest, coverage, ruff, pyright, ty, strata-python) replaces the `test` extra; ruff, pyright, coverage (`fail_under = 75`) and `strata-check` settings; Python floor raised to 3.13 because `tplink-omada-client` 1.5.13 and later need it (correction: it claimed 3.11).
- `uv.lock` (**new**), `scripts/check` (**new**), `.github/workflows/unit.yml` and `upgrade-strata-python.yml` (**new**); `.github/dependabot.yml` now uses the `uv` ecosystem.
- `src/` and `tests/`: formatted with `ruff format`; `raise ... from e` in `cli.py`; `noqa` with reasons on the self-signed-certificate opt-in (`spec.py`) and the all-interfaces syslog bind (`syslog.py`).
- `.gitignore`, README and AGENTS.md: coverage files ignored, commands updated.
