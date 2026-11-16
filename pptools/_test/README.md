# Tests (front tool)

Run from the repository root (this also runs the ppmodel tests in
`pptools/ppmodel/_test/`):

    pip install -e . pytest
    pytest

All tests are fast (a few seconds) and need no network or credentials.
`test_server.py::test_ppmodel_launch` starts a real `ppmodel serve`
process on a free loopback port and stops it.

| File | Checks |
|---|---|
| `conftest.py` | `app` (front app on an empty projects folder in `tmp_path`), `client`, and `post` fixtures |
| `test_project.py` | project layout and record, name and path confinement, file write/rename/delete, run folders, project delete |
| `test_server.py` | API guard (header, JSON, host), project lifecycle, upload/rename/remove/download, new models from built-in cases, ppmodel launch/reuse/stop, stub pages (ppdata, ppoutput), exit |
| `test_cli.py` | `new`, `list`, `--version`, error exit codes; `ppdata`, `pprun`, `ppoutput` start a server or reuse a running one (real servers on free ports) |
| `test_doctest.py` | examples in the `pptools.project` and `pptools.tools` docstrings |
