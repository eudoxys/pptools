"""Simulation runner (planned)

`pprun` will be a browser tool to set up and run quasi-steady time-series
(QSTS) simulations with `pypower_sim`. It is a stub: the front server
mounts a placeholder page at `/pprun/` that lists the planned features and
the files in the project's `sims/` folder.

Run it with the `pprun` command (`pptools.pprun.cli`) or from the front
page. It is named `pprun`, not `ppsim`, because `pypower_sim` already
installs a `ppsim` command (DESIGN.md decision #7b).

Planned features
----------------

  - Define a simulation in `sims/`: a model from `models/`, input panels
    from `data/` with their case-column mappings, the time range
    (`pandas.date_range` arguments, UTC), solver options (OPF on/off, AC or
    DC OPF, `update` policy, stop on failure), and the outputs and
    recorders to write.
  - Run the simulation with `pypower_sim.PPSolver.run_timeseries` in a
    background process, with progress, cancel, and the error list.
  - Write each run to its own folder in `outputs/` with the simulation
    definition, the model as run, the output and recorder CSV files, and
    `PPModel.profile`.

What is not promised
--------------------

  - Nothing is implemented yet beyond the placeholder page.
"""

from pptools._stub import stub_blueprint

PLANNED = [
    "Define a simulation in sims/: model, input panels and mappings, UTC time range, solver options, outputs and recorders",
    "Run it with pypower_sim (PPSolver.run_timeseries) in a background process, with progress and cancel",
    "Report convergence failures and limit violations per time step",
    "Write each run to its own folder in outputs/ with its definition, the model as run, CSV outputs, and the run profile",
    ]
"""Planned features shown on the placeholder page"""

blueprint = stub_blueprint("pprun","sims","Simulation runner",
    "Set up and run quasi-steady time-series simulations of a model and data panels with pypower_sim.",PLANNED)
"""Flask blueprint mounted at `/pprun/` by `pptools.server.create_app`"""
