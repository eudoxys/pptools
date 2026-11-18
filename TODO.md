# Suite

- [x] Repository scaffold and suite design (see `DESIGN.md`)
- [x] Front page: projects (create, describe, delete), project folders (upload, download, rename, delete), tool launcher (see `pptools.server`)
- [x] `pptools serve/new/list` CLI (see `pptools.cli`)
- [x] `ppdata`, `pprun`, `ppoutput` commands that start or reuse the pptools server (DESIGN.md decision #7)
- [x] Name the simulation runner `pprun` (DESIGN.md decision #7b)
- [ ] Agree DESIGN.md draft 1 with the maintainer (decisions 1–12, open questions)
- [ ] Warn before uploading over a model that is open in ppedit
- [x] Decide the fate of `dchassin/ppedit`: it moved to `eudoxys/ppedit` and is used as a dependency instead of a copy (DESIGN.md decision #2, revised 2026-11-17)

# Model editor (`eudoxys/ppedit`)

- [x] Open models from the front page, one `ppedit serve` process per file (decision #8)
- [x] Use the `eudoxys/ppedit` package (installed with `epm install ppedit`) instead of the copy in `pptools.ppmodel` (decision #2, revised 2026-11-17)
- [ ] Merge the `?solve=`/`?view=` query parameters into `eudoxys/ppedit` (eudoxys/ppedit#78; pprun's Network tab needs them, decision #17)
- Editor features (GLM round trip, layouts, geodata editing, Claude sessions, ...) are tracked in `eudoxys/ppedit`

# ppdata (time-series data panels)

- [x] Stub page at `/ppdata/` (see `pptools.ppdata`)
- [ ] Settle the panel format and where the panel-to-case mapping lives (DESIGN.md open questions)
- [ ] Panel builder: model objects, case columns, CSV import, profiles, coverage checks, preview
- [ ] Save panels in the `pypower_sim` input format

# pprun (simulation runner)

- [x] Stub page at `/pprun/` (see `pptools.pprun`)
- [x] Settle the simulation definition format (DESIGN.md decision #13)
- [x] Add `pypower_sim` as a dependency (decisions #11, #21)
- [x] Run simulations in a background process with progress and cancel; write run folders to `outputs/` (decisions #15, #16; `pptools.pprun.runner`)
- [x] Settings for every `pypower_sim` time-series option (decision #18)
- [x] Network tab with ppedit's views of the model or a re-solved time step (decision #17)
- [x] Plots and tables of every input panel and output file (decision #20)
- [ ] Agree decisions 13–21 with the maintainer
- [ ] List run folders on the front page (DESIGN.md open question)
- [ ] Run queue for large studies (DESIGN.md open question)

# ppoutput (output manager)

- [x] Stub page at `/ppoutput/` (see `pptools.ppoutput`)
- [ ] Run list, series plots, violations, diagram view of a time step, run comparison

# Release

- [x] Create `eudoxys/pptools`
- [ ] Enable Pages (source: GitHub Actions)
- [ ] First release `26.11.0` (or when pprun works; DESIGN.md open question)
