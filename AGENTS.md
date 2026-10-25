# Repository guidelines

- Code: `src/omada_api/` (`spec.py` reads the controller's API description, `client.py` is the session on top of `tplink-omada-client`, `config.py` the saved login, `mask.py` hides secrets, `syslog.py` the UDP syslog receiver, `cli.py` the commands). Tests in `tests/`, run with `pytest`; they use a small fake spec and a fake session, no controller needed.
- Writes must stay dry-run unless `--yes` is given, and output must go through `mask()`. Never print or log the password.
- Do not commit logins, specs or any output from a real controller. `~/.omada.cfg` holds a plain-text password.
- Anything in `docs/recipes.md` should have been run against a real controller; mark what was not.
