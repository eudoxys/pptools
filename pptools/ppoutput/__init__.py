"""Output manager (planned)

`ppoutput` will be a browser tool to manage and view the outputs of
simulation runs. It is a stub: the front server mounts a placeholder page
at `/ppoutput/` that lists the planned features and the files in the
project's `outputs/` folder.

Planned features
----------------

  - List runs in `outputs/` with their simulation definition, model,
    time range, status, and run profile; rename, annotate, and delete runs.
  - Plot output and recorder series (per object and aggregated, e.g. by
    area), duration curves, and limit violations over time.
  - Show a time step on the network diagram (reusing the ppmodel diagram)
    with voltages, flows, and loading.
  - Compare runs (differences between outputs of two runs).
  - Export selected series as CSV.

What is not promised
--------------------

  - Nothing is implemented yet beyond the placeholder page.
"""

from pptools._stub import stub_blueprint

PLANNED = [
    "List runs in outputs/ with their definition, model, time range, status, and profile; rename, annotate, delete",
    "Plot output and recorder series, duration curves, and limit violations over time",
    "Show a time step on the network diagram with voltages, flows, and loading",
    "Compare two runs and export selected series as CSV",
    ]
"""Planned features shown on the placeholder page"""

blueprint = stub_blueprint("ppoutput","outputs","Output manager",
    "Manage, view, and compare the outputs of simulation runs.",PLANNED)
"""Flask blueprint mounted at `/ppoutput/` by `pptools.server.create_app`"""
