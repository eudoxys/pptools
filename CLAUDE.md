# CLAUDE.md

Guidance for Claude when working in the `eudoxys/pptools` repository.
General Eudoxys package conventions are in the `eudoxys-package` skill
(https://github.com/eudoxys/claude); this file records only what is
specific to this package.

## What this is

A suite of local browser tools to edit, provision, and run time-series
simulations of power systems with `eudoxys/pypower_sim`. A front server
(`pptools serve`, `pptools/server.py`) manages project folders
(`pptools/project.py`) and opens the tools: `ppedit` (model editor, the
separate package `eudoxys/ppedit` installed with `epm install ppedit`; one
`ppedit serve` process per open model, `pptools/tools.py`), `pprun` (simulation runner, a blueprint at `/pprun/`,
`pptools/pprun/`), and the planned `ppdata`, `ppoutput` (stub Flask
blueprints from `pptools/_stub.py`). Python 3.12+ (for `pypower_sim`),
pre-alpha.

- Docs site: https://www.eudoxys.com/pptools (pdoc from docstrings)
- Maintainer: David P. Chassin
- CLI entry points: `pptools` -> `pptools.cli:main`,
  `ppdata`/`pprun`/`ppoutput` -> `pptools.<tool>.cli:main` (all three call `pptools.cli.tool_main`)

## Where things are

- `MANIFEST.md`: map of every file, a task index, and what not to read.
  Read it first instead of listing folders.
- `DESIGN.md`: suite objective, numbered decisions, planned modules, open
  questions (cite as "decision #N"). Read it before working on the front
  tool or a planned tool, follow its decisions, and ask before departing
  from one.
- The model editor's code, design (`DESIGN.md`, cite as "ppedit decision
  #N"), tests, and examples are in `eudoxys/ppedit` (DESIGN.md decision
  #2). Don't copy ppedit code into pptools; change it in that repository.

Sibling Eudoxys dependencies: `pypower` (PF/OPF solvers, from GitHub, not
PyPI; decision #12), `ppedit` (model editor; decision #2) and `pypower_sim` (time-series simulation, used by
pprun; decisions #11, #21). `pypower_sim` installs a `ppsim` command, so the
simulation runner is named `pprun` (decision #7b); don't add a `ppsim`
command or module.

Upstream references (read-only; use sparse checkout of
`arras-energy/gridlabd`): `module/pypower/{bus,gen,branch,gencost,dcline}.cpp` for
GLM property names, units and keywords; `converters/py2glm.py` for the
`gridlabd convert -t pypower` output ppedit should stay compatible with.
`eudoxys/pypower_sim` `DESIGN.md` for the input/output CSV formats the
planned tools must read and write.

## Core conventions (front tool and planned tools)

- Files in project folders are the only state (decision #10); every route
  that changes a project returns the full `Project.to_dict()` and the page
  re-renders from it.
- All file access goes through `Project.resolve` (names checked by
  `check_name`; only the four standard subfolders). Never build project
  paths by string concatenation.
- POST requests need `X-PPTools: 1` and JSON (uploads: multipart); loopback
  `Host` only unless `allow_remote`. Keep the same guard in new tools.
- New tools: subpackage + `TOOLS` row + blueprint registered in
  `create_app` + `cli.py` calling `tool_main` (add the tool to
  `TOOL_TITLES` and `[project.scripts]`); replace the `stub_blueprint`
  when implementing.
- Front page: vanilla JS in `pptools/static/app.js` with the `h()` helper;
  modal `<dialog>` forms instead of `alert`/`confirm`.

## Style

House style (shared with ppedit): no spaces after commas in calls and
signatures, 4-space indent.

## Build, test, docs

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install --upgrade pip eudoxys
epm install ppedit                  # model editor (needs Python 3.12; see rough edges)
pip install -e . pytest
pytest            # front tool and pprun (runs case9 a few times)
make docs
pptools serve --root /tmp/pptools-demo     # manual UI check
ppedit serve case9.glm   # a model written by the front page or ppedit
```

Tests need no network or credentials.

## Known rough edges (front tool; don't "fix" silently; mention or ask)

- ppedit opened from the front page is a separate process; its own
  Open/Save as dialogs can reach any path, and it does not notice a model
  file changed on disk (e.g. an upload over it).
- Deleting files and projects is permanent (DESIGN.md open question "Trash").
- `ppedit` declares `requires-python = "== 3.12.*"` and lists PyPI
  `pypower`; install it before pptools so pptools's `git+` `pypower`
  requirement wins (decision #12), and use a Python 3.12 environment.
- `ppdata`, `ppoutput` are placeholders; don't add behavior to them
  without agreeing the design in DESIGN.md first.

## pprun (known rough edges; don't "fix" silently; mention or ask)

- Design: DESIGN.md decisions 13–21 (cite them). Runs go through
  `Runs.start` (a `python -m pptools.pprun run PROJECT RUN` process per
  run) and are files only: `status.json` is the progress channel, a
  `cancel` file the stop request.
- The first `/pprun/api/meta` request is slow (seconds): importing
  `pypower_sim` imports cvxpy.
- `pypower_sim` workarounds live in `Simulation._build`: input indexes made
  UTC, zero `BASE_KV` replaced here (a `PPModel` subclass disables its own),
  violation tolerances bound onto the instance's `get_violations`. A run
  cancelled before its first step returns from `run_timeseries` with event
  `initialization`; `run` treats that as cancelled when the `cancel` file
  exists.
- The Network tab is ppedit in an iframe (`?solve=pf&view=network`).
  `eudoxys/ppedit` 0.3.1 ignores those parameters (they were a patch in
  the removed `pptools.ppmodel` copy), so the tab shows the model unsolved
  in its default view until eudoxys/ppedit#78 is merged (DESIGN.md decision #17).
  Snapshots re-solve a step from the current `data/` panels, not a copy
  taken at run time.
- `pypower` PF/OPF ignore `dcline` rows in runs; the check warns.
- Pages poll `GET /pprun/api/project` each second while a run is going.
- Chart colors are the dataviz reference palette (`--series-1..8` in
  `pptools/pprun/static/style.css`); at most 8 series per plot, and a
  series' color follows its column position in the file.

## Working rules

- Don't commit generated output.
- When a public signature, column, API route, or project layout changes,
  update the module docstring, the package docstring, `README.md`, the
  server API list, and `DESIGN.md`.
- Update `MANIFEST.md` when adding, moving, or deleting files; run
  `python .github/check_manifest.py`.
- Conventional small test case: `case9` (built-in).
