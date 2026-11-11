# Repository guidelines

- Code: `src/omada_api/` (`spec.py` reads the controller's API description, `client.py` is the session on top of `tplink-omada-client`, `config.py` the saved login, `mask.py` hides secrets, `syslog.py` the UDP syslog receiver, `cli.py` the commands). Tests in `tests/`, run with `uv run pytest`; they use a small fake spec and a fake session, no controller needed.
- Writes must stay dry-run unless `--yes` is given, and output must go through `mask()`. Never print or log the password.
- Do not commit logins, specs or any output from a real controller. `~/.omada.cfg` holds a plain-text password.
- Anything in `docs/recipes.md` should have been run against a real controller; mark what was not.
- Tooling is uv: `uv sync` builds `.venv` from the committed `uv.lock` (`uv add <pkg>` / `uv add --group dev <pkg>`; commit `pyproject.toml` and `uv.lock` together). **Run `scripts/check` before every commit** (`--fast` skips the tests, `--fix` applies ruff): `uv run --locked strata-check` from [strata-python](https://github.com/jburnhams/strata-python). Python 3.13 or newer (`tplink-omada-client` requires it). Style is `ruff format` at 120; pyright is strict for files listed under `strict` in `pyproject.toml` (a ratchet, never remove one); `pytest.importorskip` is banned. The coverage floor (`fail_under`) only ratchets up.
- Changes go in `CHANGELOG.md` in the same commit. CI is `.github/workflows/unit.yml`; `upgrade-strata-python.yml` moves the gate's pin weekly and Dependabot keeps the rest current (daily, no ignores).
