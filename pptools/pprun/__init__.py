"""Simulation runner

`pprun` is the browser tool that sets up and runs quasi-steady time-series
(QSTS) simulations of a project's models with `pypower_sim`. The front
server mounts it at `/pprun/`; open it from the front page or with the
`pprun` command (`pptools.pprun.cli`). It is named `pprun`, not `ppsim`,
because `pypower_sim` already installs a `ppsim` command (DESIGN.md
decision #7b).

Syntax
------

    pprun [serve] [-P PROJECT] [-r ROOT] [-p PORT] [--host HOST] [--no-browser] [-d] [-v] [-w] [--version]

Description
-----------

Given a project with a model in `models/` and, optionally, time-series
panels in `data/` (CSV, timestamp first, then one column per case row or
per value of a mapping column), `pprun` is expected to:

1. keep each simulation as a JSON definition in `sims/<sim>.json`
   (`pptools.pprun.sim.Simulation`, schema in DESIGN.md): the model, the
   inputs and how each maps onto a case column, the time range from a
   start to an end date with a time step (`freq`, default `1h`), and every
   option `pypower_sim` takes for a time-series run (Settings tab);
2. check a definition before running it and list the problems (missing
   files, unknown columns, rows out of range, time steps missing from an
   input);
3. run it with `pypower_sim.PPSolver.run_timeseries` in a background
   process, one per run, with progress and Cancel
   (`pptools.pprun.runner.Runs`), into its own folder
   `outputs/<sim>_<UTC timestamp>/` holding the definition and model as
   run, one CSV per output, `recorders.csv`, `status.json`, `profile.json`,
   `errors.txt` and `log.txt`;
4. show the network in ppmodel's own views (Network tab): the model before
   a run, or a chosen time step of a run re-solved as a snapshot;
5. plot and tabulate every input panel (Inputs tab) and every output and
   recorder file of a run (Outputs tab), and list runs with their status,
   profile, errors and log (Runs tab).

The page tabs are Settings, Network, Inputs, Outputs, and Runs.

What is not promised
--------------------

  - Players (`PPData.set_player`) are not offered: they are broken in
    `pypower_sim`.
  - DC lines are passed to `pypower_sim`, but `pypower`'s PF and OPF ignore
    them in time-series runs (the check warns).
  - Inputs are not interpolated: every time step must be in every input
    (as in `pypower_sim`).
  - The initial OCE is experimental and its success checks are inverted in
    `pypower_sim`.
  - A snapshot re-solves the step from the current input files; if a panel
    changed after the run, the snapshot follows the new data.
  - Runs are not queued; each starts at once in its own process, and runs
    still going are terminated when the server exits.
"""

from pptools.pprun.sim import Simulation, SimulationError
from pptools.pprun.runner import Runs
from pptools.pprun.server import blueprint
