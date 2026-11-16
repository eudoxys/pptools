# eudoxys/pptools — package design (draft 2)

Status: draft 1 started 2026-11-16 with the repository scaffold; draft 2,
2026-11-16: simulator tool named `pprun` (decision #7b) and commands for
`ppdata`, `pprun`, `ppoutput` (decision #7, reversed). Not yet agreed with
the maintainer: decisions 1–12 describe the scaffold as built and need
confirmation; the planned tools (`ppdata`, `pprun`, `ppoutput`) are stubs
whose design is still open.

The model editor has its own design record, inherited from
`dchassin/ppedit`: [`pptools/ppmodel/DESIGN.md`](pptools/ppmodel/DESIGN.md).
Cite its decisions as "ppmodel decision #N" and this file's as
"decision #N".

## Purpose

**Objective: release a suite of browser tools to edit, provision, and run
time-series simulations of power systems using
[`eudoxys/pypower_sim`](https://github.com/eudoxys/pypower_sim).**

`pypower_sim` runs quasi-steady time-series (QSTS) simulations of
`pypower` cases from Python: a case, input CSV files mapped to case
columns, a time range, and output/recorder CSV files. Setting those up by
hand means writing case files, building CSV panels whose columns match case
rows, and writing a script per study. `pptools` puts each step in a local
browser tool and keeps the files of one study together in a project
folder:

| Step | Tool | Status | Works on |
|---|---|---|---|
| Edit the network model | `ppmodel` (from `dchassin/ppedit`) | available | `models/` |
| Provision time-series data for model objects | `ppdata` | planned (stub) | `data/` |
| Set up and run simulations | `pprun` | planned (stub) | `sims/` → `outputs/` |
| Manage and view outputs | `ppoutput` | planned (stub) | `outputs/` |
| Manage projects and open the tools | front page (`pptools serve`) | available | the projects folder |

In scope:

- transmission and sub-transmission models in the formats ppmodel reads
  (PYPOWER `.py`/`.json`, GridLAB-D `module pypower` `.glm`, PSS/E `.raw`
  input);
- time-series inputs for case columns (loads, generation limits and
  dispatch, ratings, costs) and the simulation outputs `pypower_sim`
  writes;
- one user on the local machine, working in a folder of projects.

Excluded (and where it lives instead):

- PF/OPF solvers: `eudoxys/pypower`; the time-series loop, OCE, and the
  model/data classes: `eudoxys/pypower_sim`. `pptools` calls them and does
  not reimplement them.
- Distribution models and GridLAB-D simulation itself: Arras Energy
  GridLAB-D (`ppmodel` only reads and writes the `module pypower` layer).
- Data acquisition from external services (EIA, NSRDB, ISO feeds):
  separate Eudoxys packages; `ppdata` imports their CSV output.
- Multi-user and hosted use: no authentication, accounts, or locking.

## Decisions settled

Numbers are permanent: add `Nb` rows for related later decisions; edit a
reversed decision in place and note the date.

| # | Decision |
|---|---|
| 1 | One repository and one Python package, `pptools`; each tool is a subpackage (`pptools.ppmodel`, `pptools.ppdata`, `pptools.pprun`, `pptools.ppoutput`) and the front tool is the top-level package. One install, one version, one docs site. |
| 2 | `ppmodel` is `dchassin/ppedit` 0.3.1 (commit `305c858`) moved in and renamed: module paths `ppedit.*` → `pptools.ppmodel.*`, CLI and page name `ppmodel`, POST guard header `X-PPModel`, browser storage keys `ppmodel.*`, environment variable `PPMODEL_CLAUDE_MODEL`. Its design decisions carry over unchanged in `pptools/ppmodel/DESIGN.md`; its tests in `pptools/ppmodel/_test/`; its examples in `examples/ppmodel/`. The history stays in `dchassin/ppedit`. |
| 3 | Every tool is a local Flask server with a plain HTML/CSS/JS page, no build step and no JS dependencies (as ppmodel decision #2), the same palette and type, and the same local-server guard: loopback `Host` only unless remote access is asked for, and `POST` requests must carry a tool header (`X-PPTools` for the front server; ppmodel decision #29). |
| 4 | `pptools serve` is the single front tool: it lists, creates, describes, and deletes projects; creates, uploads, downloads, renames, and deletes files in them; and opens each tool on the project's files. Default port 8040 (ppmodel keeps 8050 when run alone). |
| 5 | A project is a folder `ROOT/NAME/` holding `pptools.json` (`application`, `version`, `name`, `description`, `created`, `modified`, UTC ISO 8601) and the subfolders `models/`, `data/`, `sims/`, `outputs/`. The projects folder `ROOT` is `~/pptools` unless `--root` or `PPTOOLS_ROOT` says otherwise. Folders without `pptools.json` are ignored and never changed. |
| 6 | Project and file names match `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`; the front server reads and writes only files directly inside the four subfolders (`Project.resolve`), so nothing outside a project can be reached through its API. |
| 7 | Every tool has a command: `pptools`, `ppmodel`, `ppdata`, `pprun`, `ppoutput`. `ppdata`, `pprun`, and `ppoutput` open their page (`/<tool>/`, optionally `-P PROJECT`) on the pptools server, starting it if none is running on the port (default 8040) and reusing it otherwise (`pptools.cli.tool_main`), so every tool works on the same projects folder through one server; they take the options of `pptools serve`. `ppmodel` keeps its own server (decision #8). *Reversed 2026-11-16:* draft 1 installed only `pptools` and `ppmodel`. |
| 7b | The simulation runner is named `pprun` (subpackage `pptools.pprun`, page `/pprun/`, command `pprun`), not `ppsim`, because `pypower_sim` already installs a `ppsim` command and both packages are meant to share an environment (2026-11-16). |
| 8 | The front server starts one `ppmodel serve` process per open model file (ppmodel holds one case per process, ppmodel decision #1) on a free loopback port, opens it in a new browser tab, reuses it when the same file is opened again, stops it when the file is renamed or deleted, and stops all of them when the front server exits. |
| 9 | Planned tools are Flask blueprints mounted in the front server at `/<tool>/`, sharing its workspace; until implemented each shows its planned features and the files in its project folder (`pptools/_stub.py`). |
| 10 | Files in the project folders are the only state: no database, and no server-side record of which data panels or simulations use which model beyond the files themselves. Every file a tool writes is in a format `pypower_sim` (or ppmodel) reads directly, so a project can be used from Python or the command line without `pptools`. |
| 11 | `pypower_sim` is the simulation engine: `ppdata` writes its input CSV format (`PPData.set_input`), `pprun` drives `PPModel`/`PPData`/`PPSolver.run_timeseries`, and `ppoutput` reads its output and recorder CSV files and `PPModel.profile`. It becomes a dependency when `pprun` is implemented (not before, to keep the install light while the tools are stubs). |
| 12 | Sibling Eudoxys packages are dependencies by `git+` URL, never from PyPI: `pypower @ git+https://github.com/eudoxys/pypower`, the same `pypower` that `pypower_sim` uses (ppedit used PyPI `pypower`; all ppmodel tests pass with the Eudoxys build). |

## Conventions inherited

From the `eudoxys-package` skill (https://github.com/eudoxys/claude) and
sibling packages, not re-argued here:

- repository layout, `pyproject.toml` with dependencies from
  `requirements.txt`, pdoc docs published to https://www.eudoxys.com/pptools,
  `MANIFEST.md` checked by `.github/check_manifest.py`, approved-issue and
  issue-assignment workflows, versions `YEAR.MONTH.SEQUENCE` without `v`;
- from ppmodel: house style (no spaces after commas in calls and
  signatures, 4-space indent), vanilla JS with a small `h()` DOM helper,
  every mutating API call returns the full state the page renders from,
  JSON errors as `{"error": message}`;
- from `pypower_sim`: the `pypower` version 2 case dict, row-number column
  mapping of input/output CSV files, UTC timestamps, `pandas.date_range`
  arguments for time ranges.

## Module layout

```
pptools/
  __init__.py       package docs (spec, limits); re-exports Workspace, Project,
                    ProjectError, FOLDERS, TOOLS, create_app, main
  cli.py            main(argv): serve, new, list, --version; tool_main(tool,argv),
                    serve(root,host,port,tool,project,browser): start or reuse the server
  project.py        Workspace(root): projects; Project(path): record, folders, files
  tools.py          TOOLS registry; ModelServers(host): ppmodel process per model file
  server.py         create_app(root,allow_remote,shutdown,models): front page, API, blueprints
  _stub.py          stub_blueprint(name,folder,title,summary,planned): placeholder pages
  static/           front page (index.html, style.css, app.js)
  _test/            front tool tests (fast, no network)
  ppmodel/          model editor (from dchassin/ppedit; see pptools/ppmodel/DESIGN.md)
  ppdata/           __init__.py: stub blueprint at /ppdata/; cli.py: `ppdata` command
  pprun/            __init__.py: stub blueprint at /pprun/; cli.py: `pprun` command
  ppoutput/         __init__.py: stub blueprint at /ppoutput/; cli.py: `ppoutput` command
  # planned
  ppdata/panel.py   Panel(model,index): time-series panel for case rows; CSV I/O
  ppdata/server.py  blueprint: panel builder page and API
  pprun/sim.py      Simulation(project,definition): load, check, run with pypower_sim
  pprun/server.py   blueprint: simulation setup, run, progress, cancel
  ppoutput/run.py   Run(path): one run folder in outputs/; series, profile, comparison
  ppoutput/server.py blueprint: run list, plots, diagram view
```

## Contracts

### Project folder

| path | holds | written by |
|---|---|---|
| `pptools.json` | project record (decision #5) | front server |
| `models/*.{py,json,glm,raw}` | network models | ppmodel, uploads |
| `data/*.csv` | time-series panels in `pypower_sim` input format | ppdata (planned), uploads |
| `sims/*.json` | simulation definitions | pprun (planned) |
| `outputs/<run>/` | one folder per simulation run | pprun (planned) |

### Tools

`pptools.tools.TOOLS` lists each tool's `name`, `folder`, `status`
(`available`/`planned`), `kind` (`process`: separate server per file;
`blueprint`: mounted at `/<name>/`), `title`, and `summary`; the front page
draws its tool cards from it, so adding a tool means adding a subpackage,
a `TOOLS` row, and (for a blueprint) registering it in `create_app`.

### Front server API

Listed in the `pptools.server` docstring, which is authoritative. Every
project route returns the full project (`Project.to_dict`: record fields,
`path`, and `folders` → file lists), and the page re-renders from it.

## Data sources and method

| input | primary source | fallback |
|---|---|---|
| network model | `models/` file edited in ppmodel | upload, PYPOWER built-in case |
| time-series inputs | `data/` panels built in ppdata (planned) | uploaded CSV in `pypower_sim` input format |
| simulation setup | `sims/` definition built in pprun (planned) | none |
| results | `outputs/` run folders written by pprun (planned) | none |

Workflow, as the front page presents it:

1. **Create a project** (front page or `pptools new NAME`).
2. **Model.** Create a model (empty or from a PYPOWER built-in case),
   upload one, or convert one; edit, check, and solve PF/OPF in ppmodel,
   which saves to the file in `models/`.
3. **Provision data (planned).** In ppdata, choose a model, pick objects
   and the case columns that vary in time, and build panels with a UTC
   index and one column per case row; save to `data/`.
4. **Simulate (planned).** In pprun, combine a model and panels with a time
   range and solver options into a definition in `sims/`; run it with
   `pypower_sim` in a background process; each run writes its own folder
   in `outputs/`.
5. **Review (planned).** In ppoutput, list runs, plot series and
   violations, view a time step on the network diagram, compare runs.

Discrepancies (solver failures, missing input steps, unmapped rows) are
reported to the user, never forced to succeed (as in `pypower_sim`
decision #6 and ppmodel).

## Outputs

### `pptools.json`

| field | type | notes |
|---|---|---|
| `application` | str | always `pptools` |
| `version` | str | pptools version that created the project |
| `name` | str | equals the folder name |
| `description` | str | free text |
| `created`, `modified` | str | UTC ISO 8601 (`2026-11-16T14:32:00Z`); `modified` changes on any file change made through pptools |

Example (illustrative only):

```json
{
  "application": "pptools",
  "version": "0.0.0",
  "name": "wecc240",
  "description": "WECC 240-bus summer peak study",
  "created": "2026-11-16T14:32:00Z",
  "modified": "2026-11-16T14:40:12Z"
}
```

### Planned (illustrative only, see Open questions)

- `data/<panel>.csv`: `timestamp` (UTC) first, then one column per case row
  of one table/column, as `PPData.set_input` reads.
- `sims/<sim>.json`: model file, input panels with table/column/scale/offset,
  `date_range` arguments, solver options, outputs and recorders.
- `outputs/<sim>_<UTC timestamp>/`: the definition as run, the model as
  run, output and recorder CSV files, `profile.json`, `errors.txt`.

## Files and formats

- Models: ppmodel formats (`.py`, `.json`, `.glm`; `.raw` input only).
- Panels, outputs, recorders: CSV, UTC timestamps, as `pypower_sim` writes.
- Records and definitions: JSON, 2-space indent.
- Size estimate to confirm: an hourly year for 240 buses is 8 760 rows ×
  240 columns ≈ 15–20 MB of CSV per panel or output.

## Dependencies and gaps in sibling packages

| need | status |
|---|---|
| PF/OPF solvers | `eudoxys/pypower` ✔ |
| model editor | `pptools.ppmodel` (from `dchassin/ppedit`) ✔ |
| time-series loop, inputs, outputs, recorders | `pypower_sim.PPSolver.run_timeseries`, `PPData` ✔ |
| players (`PPData.set_player`) | broken in `pypower_sim` (fails before storing anything; its DESIGN.md "Known issues"); needed only if pprun uses players |
| GLM/JSON models in `pypower_sim` | `PPModel` reads Python case files, functions, and dicts; pprun will convert with `pptools.ppmodel.Case` to the case dict |
| initial OCE in `run_timeseries` | success/failure conditions appear inverted (`pypower_sim` DESIGN.md "Known issues"); avoid `with_oce` until fixed |
| progress and cancel for long runs | `run_timeseries` `progress` and `stop_test` callbacks ✔ |
| `ppsim` command name | taken by `pypower_sim`; the runner is `pprun` (decision #7b) |

## Known issues to handle

- Two browser tabs on the same project see each other's changes only
  when the page reloads the project (on focus, and after each action).
- A model open in ppmodel and changed on disk by another tool (or an
  upload over it) is not reloaded by ppmodel; uploading over an open model
  should stop or warn first (not yet done).
- ppmodel's own Open/Save as dialogs accept any path on the machine, so a
  model can be saved outside the project; the front page lists only files
  in `models/`.
- Deleting files and projects is permanent (projects need the name typed
  to confirm).
- Uploads are limited to 512 MB per request (`MAX_UPLOAD`).

## Open questions

- **Fate of `dchassin/ppedit`.** Archive it with a pointer to
  `eudoxys/pptools`; keep it as the standalone editor and sync changes
  in one direction; or keep both and let them diverge. Its open issues
  (dchassin/ppedit#11, #12, #13, #16, #17, #24, #25, #33, #54) would move
  or be cross-referenced.
- **Simulation definition format.** A pptools JSON in `sims/` that pprun
  turns into `pypower_sim` calls; or `pypower_sim`'s own `PPModel.save()`
  JSON (which already holds `inputs`, `outputs`, `recorders`, `options`),
  so a definition is a saved `PPModel`.
- **Where the panel-to-case mapping lives.** In the panel file (a header
  or a sidecar JSON) so a panel is self-describing; or in the simulation
  definition, so one panel can feed several models.
- **ppmodel inside the front server.** Keep one process per model file
  (decision #8); or mount ppmodel under `/ppmodel/<file>/` in the front
  server, which needs ppmodel's page to use relative URLs and one `Editor`
  per file.
- **Run execution.** Background process per run started by the front
  server (simple, local); or a queue that can run several at once.
- **Trash.** Keep deletion permanent; or move deleted files to
  `ROOT/.trash/`.
- **Model dependencies.** GLM models that `#include` other files
  (ppmodel decision #19) and models with separate geodata CSV files:
  whether `models/` may hold subfolders or companion files.
- **First release version.** pptools starts at `0.0.0`; ppedit was at
  0.3.1. First release `26.11.0` per the Eudoxys versioning, or later
  when pprun works.
