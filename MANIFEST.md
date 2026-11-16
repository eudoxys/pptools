# MANIFEST

Map of the `eudoxys/pptools` repository. Every tracked file is covered by
one row or glob below; check with `python .github/check_manifest.py`.
Update this file in the same PR that adds, moves, or deletes a file.

## Start here

1. `CLAUDE.md` — conventions, rough edges, working rules
2. `DESIGN.md` — suite objective, decisions, planned tools, open questions
3. `pptools/__init__.py` — package docs (spec, limits) and public API
4. `pptools/server.py` — front server and its API list
5. `pptools/ppmodel/DESIGN.md` and `pptools/ppmodel/case.py` — for model editor work

## Task index

- Change the project layout or record: `FOLDERS`/`Project`/`Workspace` in `pptools/project.py`; `DESIGN.md` decision #5 and Outputs; `pptools/_test/test_project.py`
- Add a front API route: `pptools/server.py` (and its docstring API list); `pptools/_test/test_server.py`; call it from `pptools/static/app.js`
- Change the front page: `pptools/static/{index.html,style.css,app.js}`
- Add a tool or implement a planned one: subpackage `pptools/<tool>/`; row in `TOOLS` (`pptools/tools.py`); register its blueprint in `create_app`; replace `stub_blueprint`; `DESIGN.md` module layout; tests in `pptools/<tool>/_test/`
- Change how ppmodel is launched: `ModelServers` in `pptools/tools.py`; `/api/ppmodel*` routes in `pptools/server.py`; `test_ppmodel_launch`
- Add a CLI option: `_common_options` in `pptools/cli.py` (shared by `pptools`, `ppdata`, `pprun`, `ppoutput`), `pptools/__init__.py` Syntax section, `README.md`
- ppmodel: Add or change a table column: `COLUMNS` (and `GLM_UNITS`) in `pptools/ppmodel/case.py`; validation in `Case.validate`; `pptools/ppmodel/_test/test_case.py`
- ppmodel: Add a validation rule: `Case.validate`; test in `test_validate_finds_errors`
- ppmodel: Support another GLM object: `_parse_glm`/`_dump_glm` in `pptools/ppmodel/case.py`; add it to `pptools/ppmodel/_test/data/case3.glm` and its README
- ppmodel: Change area handling: `COLUMNS["areas"]`, `Case.validate` and `Case._area_summary` in `pptools/ppmodel/case.py`; `areaRegions`, area grouping in `layout`/`onelineLayout` in `pptools/ppmodel/static/app.js`; `pptools/ppmodel/_test/test_areas.py`
- ppmodel: Change DC line handling: `COLUMNS["dcline"]`, `COST_TABLES` and `Case.solve` in `pptools/ppmodel/case.py`; solver callbacks in `pptools/ppmodel/_dcline.py`; `pptools/ppmodel/_test/test_dcline.py`
- ppmodel: Change WECC 240 generator costs: `examples/ppmodel/wecc240_gentypes.csv` (or rederive it with `examples/ppmodel/wecc240_gentypes.py`), then `python3 examples/ppmodel/build_wecc240_2018.py`; see `examples/ppmodel/README.md`
- ppmodel: Change PSS/E `.raw` input: `pptools/ppmodel/_psse.py` (conversion), `INPUT_FORMATS`/`Case.load` in `pptools/ppmodel/case.py`; `pptools/ppmodel/_test/test_psse.py` and `pptools/ppmodel/_test/data/psse_v*.raw`
- ppmodel: Add an API route: `pptools/ppmodel/server.py` (and its docstring API list); `pptools/ppmodel/_test/test_server.py`; call it from `pptools/ppmodel/static/app.js`
- ppmodel: Change the UI: `pptools/ppmodel/static/{index.html,style.css,app.js}`
- ppmodel: Change geodata handling or map layers: `Case.load_geodata`/`_geo_*` helpers in `pptools/ppmodel/case.py`; `geoLayout`/`renderMap` in `pptools/ppmodel/static/app.js`; `pptools/ppmodel/_test/test_geodata.py`
- ppmodel: Add a CLI command or option: `pptools/ppmodel/cli.py`, `pptools/ppmodel/__init__.py` Syntax section, `README.md`
- ppmodel: Refresh the PYPOWER example cases: `python3 examples/ppmodel/import_pypower_cases.py` (after upgrading `pypower`)
- ppmodel: Change the Claude sessions (tools, data sources, models): `pptools/ppmodel/claude.py`; `/api/claude*` routes in `pptools/ppmodel/server.py`; Claude section of `pptools/ppmodel/static/app.js`; `pptools/ppmodel/_test/test_claude.py`
- ppmodel: Change a design decision or resolve an open question: `DESIGN.md` (never renumber decisions)
- ppmodel: Release: `pyproject.toml` version; see the eudoxys-package skill checklist
- Release: `pyproject.toml` version; see the eudoxys-package skill checklist

## Front tool

| Path | Purpose | Notes |
|---|---|---|
| `pptools/__init__.py` | package docs, re-exports | pdoc landing page |
| `pptools/cli.py` | CLI `main()`: serve, new, list; `tool_main()` and `serve()` shared by the tool commands | entry point `pptools`; tested by `_test/test_cli.py` |
| `pptools/project.py` | `Workspace`, `Project`: project folders, record, files | tested by `_test/test_project.py` and its doctest |
| `pptools/tools.py` | `TOOLS` registry; `ModelServers`: one ppmodel process per model file | tested by `_test/test_server.py` and its doctest |
| `pptools/server.py` | `create_app()`: front page, project API, ppmodel launcher, tool blueprints | tested by `_test/test_server.py` |
| `pptools/_stub.py` | placeholder blueprint for planned tools | private; tested by `_test/test_server.py` |
| `pptools/static/index.html` | front page layout | |
| `pptools/static/style.css` | front page and stub page styles | |
| `pptools/static/app.js` | front page logic: projects, folders, uploads, tool cards, running editors | checked by hand |
| `pptools/.gitignore` | generated-output ignores | |
| `pptools/ppdata/__init__.py` | ppdata stub: docs and blueprint at `/ppdata/` | planned tool |
| `pptools/pprun/__init__.py` | pprun stub: docs and blueprint at `/pprun/` | planned tool |
| `pptools/ppdata/cli.py` | `ppdata` command (calls `tool_main`) | entry point; tested by `_test/test_cli.py` |
| `pptools/pprun/cli.py` | `pprun` command (calls `tool_main`) | entry point; tested by `_test/test_cli.py` |
| `pptools/ppoutput/cli.py` | `ppoutput` command (calls `tool_main`) | entry point; tested by `_test/test_cli.py` |
| `pptools/ppoutput/__init__.py` | ppoutput stub: docs and blueprint at `/ppoutput/` | planned tool |

## Front tool tests

| Path | Purpose | Notes |
|---|---|---|
| `pptools/_test/README.md` | how to run tests | |
| `pptools/_test/conftest.py` | `app`, `client`, `post` fixtures | |
| `pptools/_test/test_*.py` | tests | fast; `test_ppmodel_launch` starts a real ppmodel process |

## ppmodel (model editor)

| Path | Purpose | Notes |
|---|---|---|
| `pptools/ppmodel/__init__.py` | ppmodel docs (spec, limits), re-exports | pdoc page `pptools.ppmodel` |
| `pptools/ppmodel/__main__.py` | `python3 -m pptools.ppmodel` | how the front server starts ppmodel |
| `pptools/ppmodel/DESIGN.md` | ppmodel design decisions (from ppedit) | cite as "ppmodel decision #N" |
| `pptools/ppmodel/cli.py` | CLI `main()`: serve, convert, check | entry point `ppmodel`; tested by `_test/test_cli.py` |
| `pptools/ppmodel/case.py` | `Case`: tables, `.py`/`.json`/`.glm` I/O (and `.raw` input), edits, validation, PF/OPF | tested by `_test/test_case.py` and its doctest |
| `pptools/ppmodel/_psse.py` | PSS/E RAW reader (revisions 23–35), after MATPOWER `psse2mpc` | private; read only; tested by `_test/test_psse.py` |
| `pptools/ppmodel/_dcline.py` | DC line model for the PYPOWER solver (`userfcn` callbacks, as `pypower.toggle_dcline`) | private; tested by `_test/test_dcline.py` |
| `pptools/ppmodel/claude.py` | `Sessions`: Claude API conversations with tools that edit the case, web and local data sources | tested by `_test/test_claude.py` with a fake client |
| `pptools/ppmodel/server.py` | `create_app()`, `Editor` (undo/redo), JSON API | tested by `_test/test_server.py` |
| `pptools/ppmodel/static/index.html` | editor page layout | |
| `pptools/ppmodel/static/style.css` | editor styles | |
| `pptools/ppmodel/static/app.js` | editor logic: tables, network diagram (simple, classic and one-line styles; force and geodata layouts with map layers; labels menu), results, issues, Claude sessions | checked by hand (see `CLAUDE.md`) |
| `pptools/ppmodel/.gitignore` | generated-output ignores | |

## ppmodel tests

| Path | Purpose | Notes |
|---|---|---|
| `pptools/ppmodel/_test/README.md` | how to run tests | |
| `pptools/ppmodel/_test/conftest.py` | `client` and `post` fixtures | |
| `pptools/ppmodel/_test/test_*.py` | tests | all fast, no network |
| `pptools/ppmodel/_test/data/README.md` | test data provenance | |
| `pptools/ppmodel/_test/test_examples.py` | checks `examples/ppmodel/pypower/` | each `.glm` matches its `.py` |
| `pptools/ppmodel/_test/data/case3.glm` | 3-bus GLM test model | curated, hand-written |
| `pptools/ppmodel/_test/data/psse_v33.raw` | 4-bus PSS/E revision 33 test case (loads, shunts, 2- and 3-winding transformers, DC line) | curated, hand-written; used by `test_psse.py` |
| `pptools/ppmodel/_test/data/psse_v35.raw` | 3-bus PSS/E revision 35 test case (system-wide data, `@!` headers, switching devices) | curated, hand-written; used by `test_psse.py` |
| `pptools/ppmodel/_test/data/IEEE_*_bus.raw` | IEEE 14, 24, 30, 39, 57, 118 and 300-bus cases as PSS/E revision 33 | added by the maintainer; used by `test_psse.py`; IEEE_300 ~135 kB |
| `pptools/ppmodel/_test/data/case9_geodata.csv` | synthetic `case9` bus locations | curated, hand-written; used by `test_geodata.py` |

## ppmodel examples

| Path | Purpose | Notes |
|---|---|---|
| `examples/ppmodel/import_pypower_cases.py` | regenerates `examples/ppmodel/pypower/` | maintenance script |
| `examples/ppmodel/pypower/README.md` | provenance, conversion notes, case table | table generated by the script |
| `examples/ppmodel/pypower/LICENSE` | PYPOWER BSD license | copied from the `pypower` package |
| `examples/ppmodel/pypower/AUTHORS` | PYPOWER authors | copied from the `pypower` package |
| `examples/ppmodel/pypower/case*.py` | PYPOWER built-in cases, unchanged | copied; don't edit; case300.py ~60 kB |
| `examples/ppmodel/pypower/case*.glm` | the same cases as `module pypower` GLM models | generated; don't edit; case300.glm ~250 kB, use `head` |
| `examples/ppmodel/README.md` | provenance of the WECC 240 examples | |
| `examples/ppmodel/wecc240_case.raw` | WECC 240-bus case as PSS/E revision 34 (see `examples/ppmodel/README.md`) | from NREL (see file header); ~220 kB, use `head`; tested by `_test/test_psse.py` |
| `examples/ppmodel/wecc240_bus.csv` | WECC 240 bus index: row, PSS/E bus number, name, PYPOWER `bus_i` | from NREL |
| `examples/ppmodel/wecc240_cost.csv` | per-generator cost rows (`id` = bus name + PSS/E ID; `model,startup,shutdown,cost`) | costs copied from `wecc240_gentypes.csv` by type |
| `examples/ppmodel/wecc240_gentypes.csv` | polynomial costs (`c2,c1,c0`) by generator type (the PSS/E generator ID) | written by `wecc240_gentypes.py` |
| `examples/ppmodel/wecc240_gentypes.py` | derives `wecc240_gentypes.csv` from NREL's WECC 240 scheduling workbook | maintenance script; needs `openpyxl` |
| `examples/ppmodel/wecc240_2011.py` | the 2011 WECC 240-bus case (`wecc240_case.raw` converted by ppedit) with geodata; the Pacific DC Intertie and Intermountain HVDC lines as `dcline` rows (3.5% losses, zero `dclinecost`) | written by ppedit, DC lines edited (see `examples/ppmodel/README.md`); ~90 kB, use `head` |
| `examples/ppmodel/wecc240_2018.py` | `wecc240_2011.py` with generator costs by type from `wecc240_gentypes.csv`, branch `rateA` from `rateB`/`rateC`, voltage fixes (`Vg` 1.08 pu at five generator buses, shunt reactors at eight buses) and `rateA` raised to a 20% margin on the 13 most loaded branches | written by `build_wecc240_2018.py`; don't edit; ~95 kB, use `head` |
| `examples/ppmodel/build_wecc240_2018.py` | builds `wecc240_2018.py` from `wecc240_2011.py`, `wecc240_gentypes.csv`, `wecc240_cost.csv` (generator types) and `wecc240_bus.csv` | maintenance script |
| `examples/ppmodel/wecc240_case.py` | WECC 240-bus case without geodata | written by ppedit; ~70 kB, use `head` |
| `examples/ppmodel/wecc240_geodata.csv` | bus locations for the WECC 240-bus case (`BUS_I,LAT,LON` plus `GEOHASH,NAME,GEN,LOAD,BA,COUNTY`) | for `--geodata` or **Map ▸ Load CSV…** |
| `examples/ppmodel/wecc240_map.py` | WECC 240-bus case with its `geodata` and `geotags` | written by ppedit; ~105 kB, use `head` |
| `examples/ppmodel/wecc240_map.json` | the same case as JSON | written by ppedit; ~230 kB, use `head` |
| `examples/ppmodel/wecc240_map.glm` | the same case as a `module pypower` GLM model (keeps bus latitude/longitude) | written by ppedit; ~380 kB, use `head` |

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
| `requirements.txt` | dependencies | `pypower` from `eudoxys/pypower` |
| `Makefile` | `make docs`, `make test` | |
| `LICENSE` | MIT | |
| `.gitignore` | | |
| `.gitattributes` | | |
| `.github/workflows/*.yaml` | CI: tests, docs, approved-issue check, issue assignment | |
| `.github/check_manifest.py` | checks this file | |

## Don't read

`docs/` (generated), `.venv/`, `*.egg-info/`, large examples (see sizes above).
