# eudoxys/pptools — package design (draft 4)

Status: draft 1 started 2026-11-16 with the repository scaffold; draft 2,
2026-11-16: simulator tool named `pprun` (decision #7b) and commands for
`ppdata`, `pprun`, `ppoutput` (decision #7, reversed); draft 3,
2026-11-16: `pprun` implemented at the maintainer's request (decisions
13–21; resolves the open questions on the simulation definition format,
the panel mapping, and run execution); draft 4, 2026-11-17: the model
editor is the `eudoxys/ppedit` package instead of a copy in
`pptools.ppmodel` (decisions #1, #2, #7 revised; resolves the open
question on the fate of `dchassin/ppedit`). Not yet agreed with the maintainer:
decisions 1–12 describe the scaffold as built and need confirmation;
`ppdata` and `ppoutput` are stubs whose design is still open.

The model editor is the separate package
[`eudoxys/ppedit`](https://github.com/eudoxys/ppedit) with its own design
record (its `DESIGN.md`). Cite its decisions as "ppedit decision #N" and
this file's as "decision #N".

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
| Edit the network model | `ppedit` (package `eudoxys/ppedit`) | available | `models/` |
| Provision time-series data for model objects | `ppdata` | planned (stub) | `data/` |
| Set up and run simulations | `pprun` | available | `sims/` → `outputs/` |
| Manage and view outputs | `ppoutput` | planned (stub) | `outputs/` |
| Manage projects and open the tools | front page (`pptools serve`) | available | the projects folder |

In scope:

- transmission and sub-transmission models in the formats ppedit reads
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
  GridLAB-D (`ppedit` only reads and writes the `module pypower` layer).
- Data acquisition from external services (EIA, NSRDB, ISO feeds):
  separate Eudoxys packages; `ppdata` imports their CSV output.
- Multi-user and hosted use: no authentication, accounts, or locking.

## Decisions settled

Numbers are permanent: add `Nb` rows for related later decisions; edit a
reversed decision in place and note the date.

| # | Decision |
|---|---|
| 1 | One repository and one Python package, `pptools`; each tool is a subpackage (`pptools.ppdata`, `pptools.pprun`, `pptools.ppoutput`) and the front tool is the top-level package. One install, one version, one docs site. The model editor is the exception: it is the separate package `ppedit` (decision #2; revised 2026-11-17, `pptools.ppmodel` removed). |
| 2 | The model editor is the separate Eudoxys package `eudoxys/ppedit` (formerly `dchassin/ppedit`), a dependency in `requirements.txt` (`ppedit @ git+https://github.com/eudoxys/ppedit`) installed with `epm install ppedit`; pptools keeps no copy of it. The front tool calls it `ppedit` (tool card, `/api/ppedit*` routes, `python -m ppedit.cli serve`). Its design decisions are in ppedit's `DESIGN.md` (cite as "ppedit decision #N"); its tests and examples are in that repository. Reversed 2026-11-17: until then `dchassin/ppedit` 0.3.1 (commit `305c858`) was copied in and renamed `pptools.ppmodel` (command, page, header `X-PPModel`, storage keys `ppmodel.*`), with its examples in `examples/ppmodel/`. |
| 3 | Every tool is a local Flask server with a plain HTML/CSS/JS page, no build step and no JS dependencies (as ppedit decision #2), the same palette and type, and the same local-server guard: loopback `Host` only unless remote access is asked for, and `POST` requests must carry a tool header (`X-PPTools` for the front server; ppedit decision #29). |
| 4 | `pptools serve` is the single front tool: it lists, creates, describes, and deletes projects; creates, uploads, downloads, renames, and deletes files in them; and opens each tool on the project's files. Default port 8040 (ppedit keeps 8050 when run alone). |
| 5 | A project is a folder `ROOT/NAME/` holding `pptools.json` (`application`, `version`, `name`, `description`, `created`, `modified`, UTC ISO 8601) and the subfolders `models/`, `data/`, `sims/`, `outputs/`. The projects folder `ROOT` is `~/pptools` unless `--root` or `PPTOOLS_ROOT` says otherwise. Folders without `pptools.json` are ignored and never changed. |
| 6 | Project and file names match `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`; the front server reads and writes only files directly inside the four subfolders (`Project.resolve`), so nothing outside a project can be reached through its API. |
| 6b | Each simulation run writes one folder `outputs/<run>/` (run name checked like a file name); `Project.run_path(run,name)` reaches the files directly inside it, `Project.runs()` lists them, and nothing deeper is reachable (2026-11-16, with pprun; decision #6 otherwise unchanged). |
| 7 | Every tool has a command: `pptools`, `ppdata`, `pprun`, `ppoutput` (the model editor's `ppedit` command comes with the `ppedit` package; `ppmodel` removed 2026-11-17, decision #2). `ppdata`, `pprun`, and `ppoutput` open their page (`/<tool>/`, optionally `-P PROJECT`) on the pptools server, starting it if none is running on the port (default 8040) and reusing it otherwise (`pptools.cli.tool_main`), so every tool works on the same projects folder through one server; they take the options of `pptools serve`. `ppmodel` keeps its own server (decision #8). *Reversed 2026-11-16:* draft 1 installed only `pptools` and `ppmodel`. |
| 7b | The simulation runner is named `pprun` (subpackage `pptools.pprun`, page `/pprun/`, command `pprun`), not `ppsim`, because `pypower_sim` already installs a `ppsim` command and both packages are meant to share an environment (2026-11-16). |
| 8 | The front server starts one `ppedit serve` process per open model file (ppedit holds one case per process, ppedit decision #1) on a free loopback port, opens it in a new browser tab, reuses it when the same file is opened again, stops it when the file is renamed or deleted, and stops all of them when the front server exits. |
| 9 | Planned tools are Flask blueprints mounted in the front server at `/<tool>/`, sharing its workspace; until implemented each shows its planned features and the files in its project folder (`pptools/_stub.py`). |
| 10 | Files in the project folders are the only state: no database, and no server-side record of which data panels or simulations use which model beyond the files themselves. Every file a tool writes is in a format `pypower_sim` (or ppedit) reads directly, so a project can be used from Python or the command line without `pptools`. |
| 11 | `pypower_sim` is the simulation engine: `ppdata` writes its input CSV format (`PPData.set_input`), `pprun` drives `PPModel`/`PPData`/`PPSolver.run_timeseries`, and `ppoutput` reads its output and recorder CSV files and `PPModel.profile`. It becomes a dependency when `pprun` is implemented (not before, to keep the install light while the tools are stubs). |
| 12 | Sibling Eudoxys packages are dependencies by `git+` URL, never from PyPI: `pypower @ git+https://github.com/eudoxys/pypower`, the same `pypower` that `pypower_sim` uses (ppedit's own `requirements.txt` names PyPI `pypower`; pptools's `git+` requirement replaces it when pptools is installed after ppedit, and ppedit's tests passed with the Eudoxys build when it was copied here). |
| 13 | A simulation definition is a pptools JSON file `sims/<sim>.json` (schema under Contracts), not a saved `PPModel`: it names the model file and the input panels instead of embedding the case and the data, so editing a model or a panel changes the next run. The panel-to-case mapping (`table`, `column`, `scale`, `offset`, optional `mapping` column) lives in the definition, so one panel can feed several simulations and models (2026-11-16). |
| 14 | pprun loads every model with `ppedit.Case` (all ppedit formats, `.py` parsed without executing it, ppedit Core conventions) and passes `Case.to_ppc(arrays=True)` to `pypower_sim.PPModel`; geodata and `areas` are not passed to `pypower_sim`. |
| 15 | Each run is one background process (`python -m pptools.pprun run SIM RUNDIR`) started by the server that serves `/pprun/` (`pptools.pprun.runner.Runs`); several runs may go at once. The process writes `status.json` (state, progress, current time step, error count) at least every second and at each event; Cancel creates a `cancel` file that the `progress` callback sees at the next time step (`run_timeseries` event `interrupted`), and the server terminates the process if it has not stopped 10 s later. A run left `running` with no live process (server restart, crash) is reported as `lost`. |
| 16 | A run folder holds `simulation.json` (the definition as run), `model.json` (the model as run, ppedit JSON), one output CSV per output (`<table>_<column>.csv`), `recorders.csv` (when there are recorders), `status.json`, `profile.json` (`PPModel.profile`), `errors.txt` (`PPModel.errors`, failures and warnings), and `log.txt` (solver output). Runs are named `<sim>_<UTC YYYYMMDDTHHMMSSZ>`. |
| 17 | The Network tab shows ppedit's own page (decision #8 process, in an `<iframe>`), so pprun has the same simple, classic, and one-line views, layouts, labels, and map layers without copying them. Before a run it opens the simulation's model file; for a run it opens a *snapshot* of a chosen time step: pprun re-solves that step from `model.json` and the inputs (as in the run: inputs, OPF per the settings, then PF), writes the solved case to `outputs/<run>/snapshot_<YYYYMMDDTHHMMSSZ>.json`, and opens it with ppedit, which runs PF on load (`?solve=pf`, a small addition to ppedit's page) so flows and loadings show. A new snapshot replaces the run's previous one (file and process). The `?solve=pf|opf` and `?view=NAME` page parameters it uses were added to the copy in `pptools.ppmodel`; since decision #2 was revised (2026-11-17) they must come from `eudoxys/ppedit`. |
| 18 | The Settings tab exposes every option `pypower_sim` takes for a time-series run: the time range (`pandas.date_range` `start`, `end`, `freq` (default `1h`), `tz` (default `UTC`), `inclusive`); `run_timeseries` `use_acopf` (as OPF mode `ac`, `dc`, or `none` = PF only), `stop_on_fail`, `violations` with the `get_violations` tolerances `abs_err`/`rel_err`, and `with_oce` with every `OceOptions` field; every PYPOWER `ppoption` key passed through `PPModel.options` (defaults: `PPModel.default_options` over `ppoption`'s, only overrides stored); `PPModel.default_values["BASE_KV"]`; and the `PPData` arguments of each input (`set_input`), output (`set_output`), and recorder (`set_recorder`). Not exposed: the callbacks (`progress`, `call_on_fail`, `stop_test`; pprun uses them itself), players (`set_player` is broken in `pypower_sim`), the per-solve `update` policy and output timestamp format (not `run_timeseries` arguments). |
| 19 | Input panels are CSV files in `data/` in `pypower_sim` input format; pprun converts their index to UTC before a run (naive timestamps are taken as UTC) because `run_timeseries` looks rows up by UTC timestamp. Checks before a run report missing files, unknown columns, mapped rows out of range, and time steps missing from an input; a run needs at least two time steps (`run_timeseries` divides by the range's span). |
| 20 | The Inputs and Outputs tabs plot (SVG line chart, chosen columns, min/max-bucketed to the plot width) and tabulate (paged) every input panel of the simulation and every output and recorder file of a run; columns that are case rows are labeled with the row's id (bus number, generator bus, branch ends). |
| 21 | `pypower_sim` (`git+https://github.com/eudoxys/pypower_sim`) is a dependency from pprun on (decision #11), and `requires-python` becomes `>=3.12` with it. |

## Conventions inherited

From the `eudoxys-package` skill (https://github.com/eudoxys/claude) and
sibling packages, not re-argued here:

- repository layout, `pyproject.toml` with dependencies from
  `requirements.txt`, pdoc docs published to https://www.eudoxys.com/pptools,
  `MANIFEST.md` checked by `.github/check_manifest.py`, approved-issue and
  issue-assignment workflows, versions `YEAR.MONTH.SEQUENCE` without `v`;
- from ppedit: house style (no spaces after commas in calls and
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
  tools.py          TOOLS registry; ModelServers(host): ppedit process per model file
  server.py         create_app(root,allow_remote,shutdown,models): front page, API, blueprints
  _stub.py          stub_blueprint(name,folder,title,summary,planned): placeholder pages
  static/           front page (index.html, style.css, app.js)
  _test/            front tool tests (fast, no network)
  ppdata/           __init__.py: stub blueprint at /ppdata/; cli.py: `ppdata` command
  pprun/            simulation runner (decisions 13-21)
    __init__.py     docs; re-exports Simulation, SimulationError, Runs, blueprint
    __main__.py     python3 -m pptools.pprun run SIM RUNDIR | snapshot RUNDIR TIME
    cli.py          `pprun` command (calls tool_main)
    sim.py          Simulation(project,name,definition): defaults, check, model, run, snapshot;
                    OPTION_GROUPS (ppoption metadata), OCE_DEFAULTS
    runner.py       Runs(): run processes, status, cancel; run_status(path)
    server.py       blueprint at /pprun/: page and API
    static/         page (index.html, style.css, app.js)
    _test/          tests (fast; one short case9 run)
  ppoutput/         __init__.py: stub blueprint at /ppoutput/; cli.py: `ppoutput` command
  # planned
  ppdata/panel.py   Panel(model,index): time-series panel for case rows; CSV I/O
  ppdata/server.py  blueprint: panel builder page and API
  ppoutput/run.py   Run(path): one run folder in outputs/; series, profile, comparison
  ppoutput/server.py blueprint: run list, plots, diagram view
```

## Contracts

### Project folder

| path | holds | written by |
|---|---|---|
| `pptools.json` | project record (decision #5) | front server |
| `models/*.{py,json,glm,raw}` | network models | ppedit, uploads |
| `data/*.csv` | time-series panels in `pypower_sim` input format | ppdata (planned), uploads |
| `sims/*.json` | simulation definitions (decision #13) | pprun |
| `outputs/<run>/` | one folder per simulation run (decision #16) | pprun |

### Tools

`pptools.tools.TOOLS` lists each tool's `name`, `folder`, `status`
(`available`/`planned`), `kind` (`process`: separate server per file;
`blueprint`: mounted at `/<name>/`), `title`, and `summary`; the front page
draws its tool cards from it, so adding a tool means adding a subpackage,
a `TOOLS` row, and (for a blueprint) registering it in `create_app`.

### Simulation definition (`sims/<sim>.json`)

| field | type | default | notes |
|---|---|---|---|
| `application`, `tool`, `version` | str | `pptools`, `pprun`, pptools version | written on save |
| `model` | str | — | file in `models/` |
| `start`, `end` | str | — | `pandas.date_range` arguments; offsets allowed (`2020-08-01 00:00-07:00`) |
| `freq` | str | `1h` | pandas frequency |
| `tz` | str | `UTC` | time zone of naive `start`/`end` |
| `inclusive` | str | `both` | `both`, `neither`, `left`, `right` |
| `opf` | str | `ac` | `ac`, `dc`, `none` (PF only); OPF is skipped by `pypower_sim` when the model has no `gencost` |
| `stop_on_fail` | bool | `true` | |
| `violations` | bool | `false` | check limits after each step |
| `abs_err`, `rel_err` | float/null | `null` | violation tolerances |
| `oce` | object/null | `null` | `OceOptions` fields: `margin`, `allin`, `setpoints`, `smallangles`, `costs`, `cvx` |
| `base_kv` | float/null | `230` | replaces zero bus `BASE_KV`; `null` leaves zeros |
| `options` | object | `{}` | `ppoption` overrides, upper-case keys |
| `inputs` | list | `[]` | `{file, table, column, scale, offset, mapping}` (`mapping`: column of `table` whose values match the panel's column names, `""` = row numbers) |
| `outputs` | list | bus `VM`, `VA`; gen `PG`, `QG`; branch `PF`, `QF`, `PT`, `QT` | `{table, column, scale, offset, format}` |
| `recorders` | list | `cost` when OPF is on | `{name, target (list of case keys), scale, offset, format}` |

### Front server API

Listed in the `pptools.server` docstring, which is authoritative. Every
project route returns the full project (`Project.to_dict`: record fields,
`path`, and `folders` → file lists), and the page re-renders from it.

## Data sources and method

| input | primary source | fallback |
|---|---|---|
| network model | `models/` file edited in ppedit | upload, PYPOWER built-in case |
| time-series inputs | `data/` panels built in ppdata (planned) | uploaded CSV in `pypower_sim` input format |
| simulation setup | `sims/` definition built in pprun | none |
| results | `outputs/` run folders written by pprun | none |

Workflow, as the front page presents it:

1. **Create a project** (front page or `pptools new NAME`).
2. **Model.** Create a model (empty or from a PYPOWER built-in case),
   upload one, or convert one; edit, check, and solve PF/OPF in ppedit,
   which saves to the file in `models/`.
3. **Provision data (planned).** In ppdata, choose a model, pick objects
   and the case columns that vary in time, and build panels with a UTC
   index and one column per case row; save to `data/`.
4. **Simulate.** In pprun, combine a model and panels with a time
   range and solver options into a definition in `sims/`; run it with
   `pypower_sim` in a background process; each run writes its own folder
   in `outputs/`.
5. **Review (planned).** In ppoutput, list runs, plot series and
   violations, view a time step on the network diagram, compare runs.

Discrepancies (solver failures, missing input steps, unmapped rows) are
reported to the user, never forced to succeed (as in `pypower_sim`
decision #6 and ppedit).

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

### Run folder (`outputs/<sim>_<UTC timestamp>/`, decision #16)

`status.json` (illustrative only):

```json
{"state": "done", "event": "completed", "progress": 1.0,
 "timestamp": "2020-01-02T00:00:00Z", "steps": 25, "errors": 0,
 "started": "2026-11-16T17:02:11Z", "finished": "2026-11-16T17:02:17Z",
 "pid": 41233}
```

`state` is `running`, `done` (all steps run; with `stop_on_fail` off,
`errors` counts the failures and warnings recorded), `failed` (stopped by
a failure or an exception; `message` says which), `cancelled`, or `lost`
(decision #15). Output CSV files are as `pypower_sim` writes them:
`timestamp` (`YYYY-MM-DD HH:MM:SS UTC`) then one column per case row.

### Planned (illustrative only, see Open questions)

- `data/<panel>.csv`: `timestamp` (UTC) first, then one column per case row
  of one table/column, as `PPData.set_input` reads.

## Files and formats

- Models: ppedit formats (`.py`, `.json`, `.glm`; `.raw` input only).
- Panels, outputs, recorders: CSV, UTC timestamps, as `pypower_sim` writes.
- Records and definitions: JSON, 2-space indent.
- Size estimate to confirm: an hourly year for 240 buses is 8 760 rows ×
  240 columns ≈ 15–20 MB of CSV per panel or output.

## Dependencies and gaps in sibling packages

| need | status |
|---|---|
| PF/OPF solvers | `eudoxys/pypower` ✔ |
| model editor | `eudoxys/ppedit` package (decision #2) ✔ |
| `?solve=`/`?view=` page parameters for the pprun Network tab | eudoxys/ppedit#78 (decision #17) |
| time-series loop, inputs, outputs, recorders | `pypower_sim.PPSolver.run_timeseries`, `PPData` ✔ |
| violation tolerances in `run_timeseries` | none: it calls `get_violations()` without `abs_err`/`rel_err`; pprun binds them on the model instance |
| DC lines in time-series runs | `pypower` `runpf`/`runopf` ignore `dcline` rows (only ppedit's own solver models them); pprun passes them and reports this in the check |
| players (`PPData.set_player`) | broken in `pypower_sim` (fails before storing anything; its DESIGN.md "Known issues"); needed only if pprun uses players |
| GLM/JSON models in `pypower_sim` | `PPModel` reads Python case files, functions, and dicts; pprun converts with `ppedit.Case` (decision #14) ✔ |
| initial OCE in `run_timeseries` | success/failure conditions appear inverted (`pypower_sim` DESIGN.md "Known issues"); avoid `with_oce` until fixed |
| progress and cancel for long runs | `run_timeseries` `progress` and `stop_test` callbacks ✔ |
| `ppsim` command name | taken by `pypower_sim`; the runner is `pprun` (decision #7b) |

## Known issues to handle

- Two browser tabs on the same project see each other's changes only
  when the page reloads the project (on focus, and after each action).
- A model open in ppedit and changed on disk by another tool (or an
  upload over it) is not reloaded by ppedit; uploading over an open model
  should stop or warn first (not yet done).
- ppedit's own Open/Save as dialogs accept any path on the machine, so a
  model can be saved outside the project; the front page lists only files
  in `models/`.
- Deleting files and projects is permanent (projects need the name typed
  to confirm).
- Uploads are limited to 512 MB per request (`MAX_UPLOAD`).

## Open questions

- **ppedit inside the front server.** Keep one process per model file
  (decision #8); or mount ppedit under `/ppedit/<file>/` in the front
  server, which needs ppedit's page to use relative URLs and one `Editor`
  per file.
- **Run queue.** Runs start at once, each in its own process (decision
  #15); a queue limiting concurrent runs may be needed for large studies.
- **Run folders on the front page.** The front page lists files only, so
  `outputs/` shows no runs until ppoutput (or a front-page change) lists
  `Project.runs()`.
- **Trash.** Keep deletion permanent; or move deleted files to
  `ROOT/.trash/`.
- **Model dependencies.** GLM models that `#include` other files
  (ppedit decision #19) and models with separate geodata CSV files:
  whether `models/` may hold subfolders or companion files.
- **First release version.** pptools starts at `0.0.0`; ppedit is at
  0.3.1. First release `26.11.0` per the Eudoxys versioning, or later
  when pprun works.
