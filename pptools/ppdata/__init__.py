"""Time-series data panels (planned)

`ppdata` will be a browser tool to construct time-series panels of data for
objects in a model, for use as `pypower_sim` inputs. It is a stub: the
front server mounts a placeholder page at `/ppdata/` that lists the planned
features and the files in the project's `data/` folder.

Planned features
----------------

  - Pick a model in the project's `models/` folder and list its objects
    (buses, generators, branches, DC lines) with the case columns that can
    vary in time (e.g. bus `PD`/`QD`, generator `PMAX`/`PG`, branch
    `RATE_A`, cost coefficients).
  - Build a panel: a tz-aware UTC timestamp index and one column per
    object row, from uploaded CSV files, built-in shapes (constant, daily
    and weekly profiles, scaling of the case value), or other panels.
  - Map external identifiers (bus names, plant IDs, geodata tags) to case
    rows, and check coverage (rows with no data, steps with missing values).
  - Preview panels as plots and summary statistics.
  - Save panels to `data/` as CSV files in the `pypower_sim` input format
    (`PPData.set_input`: timestamp first column, one column per case row,
    `scale` and `offset` recorded alongside).

What is not promised
--------------------

  - Nothing is implemented yet beyond the placeholder page.
"""

from pptools._stub import stub_blueprint

PLANNED = [
    "Choose a model in models/ and list its objects and the case columns that can vary in time",
    "Build panels (UTC timestamp index, one column per object row) from uploaded CSV, profiles, or other panels",
    "Map external identifiers (names, plant IDs, geodata tags) to case rows and check coverage",
    "Preview panels as plots and summary statistics",
    "Save panels to data/ as pypower_sim input CSV files",
    ]
"""Planned features shown on the placeholder page"""

blueprint = stub_blueprint("ppdata","data","Time-series data panels",
    "Construct time-series panels of data for objects in a model, as pypower_sim inputs.",PLANNED)
"""Flask blueprint mounted at `/ppdata/` by `pptools.server.create_app`"""
