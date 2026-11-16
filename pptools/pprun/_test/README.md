# Tests (pprun)

Run from the repository root (with the other tests):

    pip install -e . pytest
    pytest pptools/pprun

No network or credentials are needed. The tests run the PYPOWER `case9`
model over six hourly steps with a synthetic load panel, in-process and
as real background processes; the whole folder takes about 10 s (the
first `pypower_sim` import, which loads cvxpy, takes a few seconds).

| File | Checks |
|---|---|
| `conftest.py` | `project` (case9 and a six-hour bus `PD` panel), `sim` (`base.json` over those six hours), `write_panel` helper, and `app`, `client`, `post` on the same projects folder |
| `test_sim.py` | definition defaults and validation, time ranges (offsets, time zones, `inclusive`), PYPOWER option metadata, checks (missing files, unknown columns, row numbers, mapping columns, missing time steps, OPF-only recorders), an in-process run (files, dispatch follows load, recorder), snapshots (nearest step, dispatch reproduced, replaced), input-gap failure, cancel before the first step, model errors |
| `test_doctest.py` | examples in the `pptools.pprun.sim` and `pptools.pprun.runner` docstrings |
| `test_server.py` | page, static files, meta; simulation new/save/delete and the check; guard; panel head, page and bucketed plot data; a run in a background process with run details, output data, download, a snapshot opened in ppmodel, and deletion (which stops that ppmodel); cancel of a 49-step run |
