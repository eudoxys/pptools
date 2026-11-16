"""Simulation run processes

`Runs` starts each simulation run in its own process (`python -m
pptools.pprun run PROJECT RUN`, DESIGN.md decision #15), reports its status
from the run folder's `status.json`, and cancels it: a `cancel` file stops
the run at its next time step, and the process is terminated if it is
still alive `CANCEL_TIMEOUT` seconds later.

Examples
--------

    >>> Runs.run_name("base.json","2026-11-16T17:02:11Z")
    'base_20261116T170211Z'
"""

import os
import sys
import json
import atexit
import logging
import threading
import subprocess

from pptools.project import Project
from pptools.pprun.sim import Simulation, SimulationError, RUN_FILES, run_status, _write_json, _now

_logger = logging.getLogger(__file__)

def _pid_alive(pid) -> bool:
    try:
        os.kill(int(pid),0)
    except (OSError,TypeError,ValueError):
        return False
    return True

class Runs:
    """Simulation run processes started by one server"""

    CANCEL_TIMEOUT = 10.0
    """Seconds between Cancel and terminating a run that has not stopped"""

    def __init__(self):
        self._lock = threading.Lock()
        self._procs = {} # run folder -> Popen
        atexit.register(self.stop_all)

    @staticmethod
    def run_name(sim:str,when:str|None=None) -> str:
        """Run folder name `<sim>_<UTC YYYYMMDDTHHMMSSZ>` (decision #16)"""
        when = when or _now()
        return f"{sim[:-5] if sim.endswith('.json') else sim}_" + when.replace("-","").replace(":","")

    def start(self,project:Project,sim:Simulation) -> str:
        """Start a run of `sim`; returns the run name

        Exceptions
        ----------

          - `SimulationError`: the check found errors, or the run folder exists
        """
        errors = [x for x in sim.check() if x["level"] == "error"]
        if errors:
            raise SimulationError("cannot run: " + "; ".join(f"{x['where']}: {x['message']}" for x in errors))
        run = self.run_name(sim.name)
        folder = project.run_path(run)
        if os.path.exists(folder):
            raise SimulationError(f"run '{run}' already exists; try again in a second")
        os.makedirs(folder)
        with open(os.path.join(folder,RUN_FILES["definition"]),"w",encoding="utf-8") as fh:
            json.dump(sim.definition,fh,indent=2)
        _write_json(os.path.join(folder,RUN_FILES["status"]),{"state":"running","event":"starting",
            "progress":0.0,"timestamp":None,"steps":0,"total":len(sim.time_range()),"errors":0,
            "started":_now(),"finished":None,"pid":None,"simulation":sim.name,"message":""})
        cmd = [sys.executable,"-m","pptools.pprun","run",project.path,run]
        _logger.info("starting %s",' '.join(cmd))
        with open(os.path.join(folder,RUN_FILES["log"]),"a",encoding="utf-8") as log:
            proc = subprocess.Popen(cmd,stdout=log,stderr=log,stdin=subprocess.DEVNULL) # pylint: disable=consider-using-with
        with self._lock:
            self._procs[folder] = proc
        project.update()
        return run

    def _proc(self,folder):
        with self._lock:
            return self._procs.get(folder)

    def status(self,project:Project,run:str) -> dict:
        """Status of run `run` (`status.json`, see DESIGN.md), with `state`
        `lost` when it says `running` but no process is alive, `name`, and
        `alive` (running with a live process)"""
        folder = project.run_path(run)
        status = run_status(folder)
        if not status:
            status = {"state":"unknown"}
        status["name"] = run
        proc = self._proc(folder)
        alive = proc.poll() is None if proc else _pid_alive(status.get("pid"))
        if status.get("state") == "running" and not alive:
            if proc and proc.poll() is not None:
                # exited without a final status (e.g. killed): read again, it may have just finished
                status = {**status,**run_status(folder)}
            if status.get("state") == "running":
                status["state"] = "lost"
        status["alive"] = bool(alive) and status.get("state") == "running"
        return status

    def cancel(self,project:Project,run:str) -> dict:
        """Ask run `run` to stop; returns its status"""
        folder = project.run_path(run)
        if not os.path.isdir(folder):
            raise SimulationError(f"run '{run}' not found")
        status = self.status(project,run)
        if not status["alive"]:
            return status
        with open(os.path.join(folder,RUN_FILES["cancel"]),"w",encoding="utf-8") as fh:
            fh.write(_now()+"\n")
        def kill():
            proc = self._proc(folder)
            if proc and proc.poll() is None:
                proc.terminate()
                self._mark_cancelled(folder)
        timer = threading.Timer(self.CANCEL_TIMEOUT,kill)
        timer.daemon = True
        timer.start()
        return status

    @staticmethod
    def _mark_cancelled(folder):
        status = run_status(folder)
        if status.get("state") == "running":
            status.update(state="cancelled",event="terminated",finished=_now())
            _write_json(os.path.join(folder,RUN_FILES["status"]),status)

    def running(self) -> list[str]:
        """Folders of runs whose process is alive"""
        with self._lock:
            return [f for f,p in self._procs.items() if p.poll() is None]

    def stop_all(self):
        """Terminate every live run (called when the server exits)"""
        for folder in self.running():
            proc = self._proc(folder)
            proc.terminate()
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                proc.kill()
            self._mark_cancelled(folder)

def main(argv:list[str]) -> int:
    """`python -m pptools.pprun run PROJECT RUN`: run the definition saved in
    `PROJECT/outputs/RUN/simulation.json` (written by `Runs.start`)"""
    if len(argv) != 3 or argv[0] != "run":
        print("usage: python -m pptools.pprun run PROJECT RUN",file=sys.stderr)
        return 2
    project = Project(argv[1])
    folder = project.run_path(argv[2])
    status = run_status(folder)
    with open(os.path.join(folder,RUN_FILES["definition"]),encoding="utf-8") as fh:
        definition = json.load(fh)
    sim = Simulation(project,status.get("simulation") or "simulation",definition)
    result = sim.run(folder)
    return 0 if result["state"] in ("done","cancelled") else 1

