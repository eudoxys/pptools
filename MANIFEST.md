# MANIFEST

Map of the `eudoxys/pptools` repository. Every tracked file is covered by
one row or glob below; check with `python .github/check_manifest.py`.
Update this file in the same PR that adds, moves, or deletes a file.

## Start here

1. `CLAUDE.md` — conventions, rough edges, working rules
2. `DESIGN.md` — suite objective, decisions, planned tools, open questions
3. `pptools/__init__.py` — package docs (spec, limits) and public API
4. `pptools/server.py` — front server and its API list
5. `pptools/pprun/__init__.py` and `pptools/pprun/sim.py` — for simulation runner work (DESIGN.md decisions 13–21)

## Task index

- Change the project layout or record: `FOLDERS`/`Project`/`Workspace` in `pptools/project.py`; `DESIGN.md` decision #5 and Outputs; `pptools/_test/test_project.py`
- Add a front API route: `pptools/server.py` (and its docstring API list); `pptools/_test/test_server.py`; call it from `pptools/static/app.js`
- Change the front page: `pptools/static/{index.html,style.css,app.js}`
- Add a tool or implement a planned one: subpackage `pptools/<tool>/`; row in `TOOLS` (`pptools/tools.py`); register its blueprint in `create_app`; replace `stub_blueprint`; `DESIGN.md` module layout; tests in `pptools/<tool>/_test/`
- Change how ppedit is launched: `ModelServers` in `pptools/tools.py`; `/api/ppedit*` routes in `pptools/server.py`; `test_ppedit_launch`
- Change the model editor itself (tables, diagram, GLM/PSS/E I/O, PF/OPF, Claude tab): the separate package [`eudoxys/ppedit`](https://github.com/eudoxys/ppedit), installed with `epm install ppedit` (DESIGN.md decision #2)
- Add a CLI option: `_common_options` in `pptools/cli.py` (shared by `pptools`, `ppdata`, `pprun`, `ppoutput`), `pptools/__init__.py` Syntax section, `README.md`
- pprun: Add a simulation setting: `Simulation.defaults`/`normalize`/`check`/`_build` in `pptools/pprun/sim.py`; Settings section in `renderSettings` (`pptools/pprun/static/app.js`); DESIGN.md definition schema and decision #18; `pptools/pprun/_test/test_sim.py`
- pprun: Change what a run writes or how it reports progress: `Simulation.run` (`pptools/pprun/sim.py`), `Runs` (`pptools/pprun/runner.py`); DESIGN.md decisions #15, #16
- pprun: Add an API route: `pptools/pprun/server.py` (and its docstring API list); `pptools/pprun/_test/test_server.py`; call it from `pptools/pprun/static/app.js`
- pprun: Change the network view: `Simulation.snapshot`, `/pprun/api/snapshot`, `renderNetwork`/`showSnapshot` in `pptools/pprun/static/app.js`; the `?solve=`/`?view=` query parameters of the ppedit page (in `eudoxys/ppedit`)
- pprun: Change plots or tables: `/pprun/api/table` in `pptools/pprun/server.py`; `lineChart`/`drawTable` in `pptools/pprun/static/app.js`
- Release: `pyproject.toml` version; see the eudoxys-package skill checklist

## Front tool

| Path | Purpose | Notes |
|---|---|---|
| `pptools/__init__.py` | package docs, re-exports | pdoc landing page |
| `pptools/cli.py` | CLI `main()`: serve, new, list; `tool_main()` and `serve()` shared by the tool commands | entry point `pptools`; tested by `_test/test_cli.py` |
| `pptools/project.py` | `Workspace`, `Project`: project folders, record, files | tested by `_test/test_project.py` and its doctest |
| `pptools/tools.py` | `TOOLS` registry; `ModelServers`: one ppedit process per model file | tested by `_test/test_server.py` and its doctest |
| `pptools/server.py` | `create_app()`: front page, project API, ppedit launcher, tool blueprints | tested by `_test/test_server.py` |
| `pptools/_stub.py` | placeholder blueprint for planned tools | private; tested by `_test/test_server.py` |
| `pptools/static/index.html` | front page layout | |
| `pptools/static/style.css` | front page and stub page styles | |
| `pptools/static/app.js` | front page logic: projects, folders, uploads, tool cards, running editors | checked by hand |
| `pptools/.gitignore` | generated-output ignores | |
| `pptools/ppdata/__init__.py` | ppdata stub: docs and blueprint at `/ppdata/` | planned tool |
| `pptools/ppdata/cli.py` | `ppdata` command (calls `tool_main`) | entry point; tested by `_test/test_cli.py` |
| `pptools/ppoutput/cli.py` | `ppoutput` command (calls `tool_main`) | entry point; tested by `_test/test_cli.py` |
| `pptools/ppoutput/__init__.py` | ppoutput stub: docs and blueprint at `/ppoutput/` | planned tool |

## pprun (simulation runner)

| Path | Purpose | Notes |
|---|---|---|
| `pptools/pprun/__init__.py` | pprun docs (spec, limits), re-exports | pdoc page `pptools.pprun` |
| `pptools/pprun/__main__.py` | `python3 -m pptools.pprun run PROJECT RUN` | how `Runs` starts a run process |
| `pptools/pprun/cli.py` | `pprun` command (calls `tool_main`) | entry point; tested by `pptools/_test/test_cli.py` |
| `pptools/pprun/sim.py` | `Simulation`: definitions, check, run with `pypower_sim`, snapshot; option metadata | tested by `_test/test_sim.py` and its doctest |
| `pptools/pprun/runner.py` | `Runs`: run processes, status, cancel; `main` of `__main__` | tested by `_test/test_server.py` and its doctest |
| `pptools/pprun/server.py` | blueprint at `/pprun/`: page and JSON API | tested by `_test/test_server.py` |
| `pptools/pprun/static/index.html` | page layout (tabs: Settings, Network, Inputs, Outputs, Runs) | |
| `pptools/pprun/static/style.css` | page styles (after `/static/style.css`); chart palette | |
| `pptools/pprun/static/app.js` | page logic: settings form, ppedit iframe, SVG line charts, data tables, runs | checked by hand (see `CLAUDE.md`) |

## pprun tests

| Path | Purpose | Notes |
|---|---|---|
| `pptools/pprun/_test/README.md` | how to run tests | |
| `pptools/pprun/_test/conftest.py` | `project`, `sim`, `write_panel`, `app`, `client`, `post` fixtures | |
| `pptools/pprun/_test/test_*.py` | tests | ~10 s; real run processes on case9 |

## Front tool tests

| Path | Purpose | Notes |
|---|---|---|
| `pptools/_test/README.md` | how to run tests | |
| `pptools/_test/conftest.py` | `app`, `client`, `post` fixtures | |
| `pptools/_test/test_*.py` | tests | fast; `test_ppedit_launch` starts a real ppedit process |

## Repository

| Path | Purpose | Notes |
|---|---|---|
| `README.md` | user overview | |
| `CLAUDE.md` | assistant guidance | |
| `DESIGN.md` | suite design: objective, decisions, open questions | update with any decision change |
| `MANIFEST.md` | this file | |
| `CONTRIBUTING.md` | contributor guide | approved-issue rule |
| `TODO.md` | roadmap | |
| `pyproject.toml` | packaging | version here; static files in package-data |
| `requirements.txt` | dependencies | `pypower`, `pypower_sim`, `ppedit` from `eudoxys` GitHub |
| `Makefile` | `make docs`, `make test` | |
| `LICENSE` | MIT | |
| `.gitignore` | | |
| `.gitattributes` | | |
| `.github/workflows/*.yaml` | CI: tests, docs, approved-issue check, issue assignment | |
| `.github/check_manifest.py` | checks this file | |

## Don't read

`docs/` (generated), `.venv/`, `*.egg-info/`.
