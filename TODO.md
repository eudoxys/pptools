# Suite

- [x] Repository scaffold and suite design (see `DESIGN.md`)
- [x] Front page: projects (create, describe, delete), project folders (upload, download, rename, delete), tool launcher (see `pptools.server`)
- [x] `pptools serve/new/list` CLI (see `pptools.cli`)
- [ ] Agree DESIGN.md draft 1 with the maintainer (decisions 1–12, open questions)
- [ ] Warn before uploading over a model that is open in ppmodel
- [ ] Decide the fate of `dchassin/ppedit` and move or cross-reference its open issues

# ppmodel (model editor, from `dchassin/ppedit`)

- [x] Move `dchassin/ppedit` 0.3.1 into `pptools.ppmodel` and rename (DESIGN.md decision #2)
- [x] Open models from the front page, one `ppmodel serve` process per file (decision #8)
- [x] Use `eudoxys/pypower` instead of PyPI `pypower` (decision #12)
- [ ] Preserve non-solver GLM objects (`load`, `powerplant`, `powerline`, `shunt`, ...) on round trip, ideally by editing them too
- [ ] Label overlap avoidance in the classic style on dense networks
- [ ] One-line style: shorter bus bars and fewer crossings on large meshed cases (dchassin/ppedit#24, #25)
- [ ] Edit geodata in the editor (drag buses in the geodata layout, a geodata table)
- [ ] Persist force-layout positions
- [ ] Keep PSS/E bus names and revision 35 substation locations as geodata (dchassin/ppedit#54)
- [ ] Copy/paste of cell ranges to and from spreadsheets
- [ ] Claude sessions: stream responses, persist conversations, show a diff of each session's edits

# ppdata (time-series data panels)

- [x] Stub page at `/ppdata/` (see `pptools.ppdata`)
- [ ] Settle the panel format and where the panel-to-case mapping lives (DESIGN.md open questions)
- [ ] Panel builder: model objects, case columns, CSV import, profiles, coverage checks, preview
- [ ] Save panels in the `pypower_sim` input format

# ppsim (simulation runner)

- [x] Stub page at `/ppsim/` (see `pptools.ppsim`)
- [ ] Settle the simulation definition format (DESIGN.md open questions)
- [ ] Add `pypower_sim` as a dependency (decision #11)
- [ ] Run simulations in a background process with progress and cancel; write run folders to `outputs/`

# ppoutput (output manager)

- [x] Stub page at `/ppoutput/` (see `pptools.ppoutput`)
- [ ] Run list, series plots, violations, diagram view of a time step, run comparison

# Release

- [x] Create `eudoxys/pptools`
- [ ] Enable Pages (source: GitHub Actions)
- [ ] First release `26.11.0` (or when ppsim works; DESIGN.md open question)
