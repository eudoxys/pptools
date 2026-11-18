"""pprun page and API

`blueprint` is mounted at `/pprun/` by `pptools.server.create_app`, so it
shares the front server's workspace, its `POST` guard (`X-PPTools: 1`,
JSON bodies), its loopback-only rule, and its ppedit launcher
(`app.config["MODELS"]`). Runs are managed by one
`pptools.pprun.runner.Runs` per application (`app.config["RUNS"]`).

API
---

Routes take the project as `?project=NAME` (`GET`) or `"project"` (`POST`).
Errors return `{"error": message}` with status 400 (404 for missing files).

  - `GET  /pprun/`: the page (`?project=NAME&sim=FILE`)
  - `GET  /pprun/api/status`: `{"tool", "status", "folder"}`
  - `GET  /pprun/api/meta`: `version`, `tables` (case table -> column
    names), `options` (`pptools.pprun.sim.option_groups`), `oce`
    (`OCE_DEFAULTS`), `defaults` (a new definition), `opf_modes`, `inclusive`
  - `GET  /pprun/api/project`: `name`, `models`, `data`, `sims` (`name`,
    `model`, `error`?), `runs` (statuses, newest first)
  - `GET  /pprun/api/sim?sim=`: `name`, `definition`, `check`, `labels`
    (`pptools.pprun.sim.row_labels` of the model, or `{}`), `steps` (number
    of time steps, or `null`)
  - `POST /pprun/api/sim/new`: `{"sim", "model", "start"?, "end"?}` -> sim
  - `POST /pprun/api/sim/save`: `{"sim", "definition"}` -> sim
  - `POST /pprun/api/sim/delete`: `{"sim"}` -> project
  - `POST /pprun/api/run`: `{"sim"}` -> `{"run", "status"}`
  - `POST /pprun/api/cancel`: `{"run"}` -> status
  - `GET  /pprun/api/run?run=`: `status`, `definition`, `files` (run
    folder), `outputs` (output and recorder files with their table), `profile`,
    `errors` (first 1000 lines), `log` (last 20 kB), `times` (ISO 8601 UTC
    time steps), `labels`
  - `POST /pprun/api/run/delete`: `{"run"}` -> project (not while running)
  - `GET  /pprun/api/table?file=&run=`: a panel (`data/<file>`, or
    `outputs/<run>/<file>`) as JSON. With `head=1`: `columns`, `rows`,
    `first`, `last`. With `points=N` (and `columns=a,b,...`): `time` (ms
    since the epoch) and per column `min`/`max` over N buckets (decision #20).
    Otherwise rows `offset`..`offset+limit` (default 0..200): `time` (ISO
    8601), `columns`, `values` (row-major, `null` for NaN).
  - `POST /pprun/api/snapshot`: `{"run", "time"}` -> the snapshot
    (`Simulation.snapshot`) plus `url`, the ppedit page showing it
  - `GET  /pprun/api/file?file=&run=`: download a run file

Models open in ppedit through the front server's `POST /api/ppedit/open`.
"""

import os
import json
import math

from flask import Blueprint, current_app, jsonify, request, send_from_directory, abort

from pptools.project import ProjectError
from pptools.pprun.sim import Simulation, SimulationError, option_groups, headers, row_labels, \
    output_file, delete_run, OCE_DEFAULTS, OPF_MODES, INCLUSIVE, RUN_FILES
from pptools.pprun.runner import Runs

STATIC = os.path.join(os.path.dirname(__file__),"static")
"""Folder of the pprun page files"""

ERRORS_MAX = 1000
"""Lines of `errors.txt` returned by `GET /pprun/api/run`"""

LOG_MAX = 20000
"""Characters of the end of `log.txt` returned by `GET /pprun/api/run`"""

blueprint = Blueprint("pprun",__name__)
"""Flask blueprint mounted at `/pprun/` by `pptools.server.create_app`"""

@blueprint.record_once
def _setup(state):
    state.app.config.setdefault("RUNS",Runs())

@blueprint.errorhandler(SimulationError)
def _sim_error(err):
    return jsonify(error=str(err)),400

def _runs() -> Runs:
    return current_app.config["RUNS"]

def _body() -> dict:
    return request.get_json(silent=True) or {}

def _project(name=None):
    name = name if name is not None else (request.args.get("project") or _body().get("project"))
    if not name:
        raise ProjectError("no project given")
    return current_app.config["WORKSPACE"].get(name)

def _labels(case) -> dict:
    return row_labels(case) if case is not None else {}

def _sim_state(project,sim:Simulation) -> dict:
    case = None
    try:
        case = sim.load_case()
    except (SimulationError,ProjectError):
        pass
    try:
        steps = len(sim.time_range())
    except SimulationError:
        steps = None
    return {"name":sim.name,"definition":sim.definition,"check":sim.check(case),
        "labels":_labels(case),"steps":steps,"project":project.name}

def _project_state(project) -> dict:
    sims = []
    for item in project.files("sims"):
        if item["ext"] != "json":
            continue
        try:
            sim = Simulation(project,item["name"])
            sims.append({"name":item["name"],"model":sim.definition["model"]})
        except (SimulationError,ProjectError) as err:
            sims.append({"name":item["name"],"model":"","error":str(err)})
    runs = [_runs().status(project,run) for run in project.runs()]
    runs.sort(key=lambda x:x.get("started") or "",reverse=True)
    return {"name":project.name,"models":[x["name"] for x in project.files("models")],
        "data":[x["name"] for x in project.files("data") if x["ext"] == "csv"],
        "sims":sims,"runs":runs}

@blueprint.get("/")
def index():
    return send_from_directory(STATIC,"index.html")

@blueprint.get("/static/<path:name>")
def static_file(name):
    return send_from_directory(STATIC,name)

@blueprint.get("/api/status")
def status():
    return jsonify(tool="pprun",status="available",folder="sims")

@blueprint.get("/api/meta")
def meta():
    from pptools import __version__ # pylint: disable=import-outside-toplevel
    return jsonify(version=__version__,tables=headers(),options=option_groups(),oce=OCE_DEFAULTS,
        defaults=Simulation.defaults(),opf_modes=list(OPF_MODES),inclusive=INCLUSIVE)

@blueprint.get("/api/project")
def project_state():
    return jsonify(_project_state(_project()))

@blueprint.get("/api/sim")
def get_sim():
    project = _project()
    return jsonify(_sim_state(project,Simulation(project,request.args.get("sim",""))))

@blueprint.post("/api/sim/new")
def new_sim():
    data = _body()
    project = _project()
    sim = Simulation.new(project,data["sim"],data["model"],data.get("start",""),data.get("end",""))
    return jsonify(_sim_state(project,sim))

@blueprint.post("/api/sim/save")
def save_sim():
    data = _body()
    project = _project()
    sim = Simulation(project,data["sim"],data["definition"])
    sim.save()
    return jsonify(_sim_state(project,sim))

@blueprint.post("/api/sim/delete")
def delete_sim():
    data = _body()
    project = _project()
    name = data["sim"] if data["sim"].endswith(".json") else data["sim"] + ".json"
    project.delete("sims",name)
    return jsonify(_project_state(project))

@blueprint.post("/api/run")
def start_run():
    data = _body()
    project = _project()
    sim = Simulation(project,data["sim"])
    run = _runs().start(project,sim)
    return jsonify(run=run,status=_runs().status(project,run))

@blueprint.post("/api/cancel")
def cancel_run():
    project = _project()
    return jsonify(_runs().cancel(project,_body()["run"]))

def _read_text(path,head=None,tail=None):
    try:
        with open(path,encoding="utf-8",errors="replace") as fh:
            if head:
                return [line.rstrip("\n") for _,line in zip(range(head),fh)]
            text = fh.read()
            return text[-tail:] if tail else text
    except OSError:
        return [] if head else ""

@blueprint.get("/api/run")
def get_run():
    project = _project()
    run = request.args.get("run","")
    folder = project.run_path(run)
    if not os.path.isdir(folder):
        raise SimulationError(f"run '{run}' not found")
    result = {"status":_runs().status(project,run),"files":project.files("outputs",run=run),
        "errors":_read_text(os.path.join(folder,RUN_FILES["errors"]),head=ERRORS_MAX),
        "log":_read_text(os.path.join(folder,RUN_FILES["log"]),tail=LOG_MAX),
        "profile":{},"definition":None,"outputs":[],"times":[],"labels":{}}
    try:
        with open(os.path.join(folder,RUN_FILES["profile"]),encoding="utf-8") as fh:
            result["profile"] = json.load(fh)
    except (OSError,ValueError):
        pass
    try:
        sim,case = Simulation.from_run(project,run)
        result["definition"] = sim.definition
        result["labels"] = _labels(case)
        result["times"] = [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in sim.time_range()]
        names = {x["name"] for x in result["files"]}
        for item in sim.definition["outputs"]:
            if output_file(item) in names:
                result["outputs"].append({"file":output_file(item),"table":item["table"],
                    "column":item["column"],"title":f"{item['table']}.{item['column']}"})
        if RUN_FILES["recorders"] in names:
            result["outputs"].append({"file":RUN_FILES["recorders"],"table":"","column":"",
                "title":"recorders"})
    except SimulationError as err:
        result["errors"].insert(0,str(err))
    return jsonify(result)

@blueprint.post("/api/run/delete")
def remove_run():
    project = _project()
    run = _body()["run"]
    if _runs().status(project,run).get("alive"):
        raise SimulationError(f"run '{run}' is still running; cancel it first")
    models = current_app.config.get("MODELS")
    if models:
        for item in models.running():
            if os.path.dirname(item["path"]) == project.run_path(run):
                models.stop(item["path"])
    delete_run(project,run)
    return jsonify(_project_state(project))

def _panel_path(project):
    file = request.args.get("file","")
    run = request.args.get("run")
    path = project.run_path(run,file) if run else project.resolve("data",file)
    if not os.path.isfile(path):
        abort(404)
    return path

def _num(value):
    value = float(value)
    return None if math.isnan(value) or math.isinf(value) else value

@blueprint.get("/api/table")
def table():
    # pylint: disable=too-many-locals
    import numpy as np # pylint: disable=import-outside-toplevel
    import pandas as pd # pylint: disable=import-outside-toplevel
    project = _project()
    path = _panel_path(project)
    try:
        frame = Simulation.read_panel(path)
    except Exception as err: # pylint: disable=broad-except
        raise SimulationError(f"cannot read {os.path.basename(path)}: {err}") from err
    columns = [str(c) for c in frame.columns]
    frame.columns = columns
    iso = lambda index: [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in index]
    if request.args.get("head"):
        return jsonify(columns=columns,rows=len(frame),
            first=iso(frame.index[:1])[0] if len(frame) else None,
            last=iso(frame.index[-1:])[0] if len(frame) else None)
    if request.args.get("points"):
        points = max(10,min(int(request.args["points"]),5000))
        want = [c for c in request.args.get("columns","").split(",") if c in columns] or columns[:8]
        sub = frame[want].apply(lambda c: pd.to_numeric(c,errors="coerce"))
        n = len(sub)
        # milliseconds since the epoch, whatever the index resolution (pandas may use us or ns)
        ms = ((sub.index.tz_convert(None) - pd.Timestamp(0)) // pd.Timedelta(milliseconds=1)).to_numpy() \
            if n else np.array([])
        if n > points:
            bucket = (np.arange(n) * points // n)
            grouped = sub.groupby(bucket)
            lo,hi = grouped.min(),grouped.max()
            times = [int(ms[i]) for i in np.searchsorted(bucket,lo.index.to_numpy())]
        else:
            lo = hi = sub
            times = [int(x) for x in ms]
        return jsonify(time=times,columns=want,
            min={c:[_num(v) for v in lo[c]] for c in want},
            max={c:[_num(v) for v in hi[c]] for c in want})
    offset = max(0,int(request.args.get("offset",0)))
    limit = max(1,min(int(request.args.get("limit",200)),5000))
    part = frame.iloc[offset:offset+limit]
    values = [[_num(v) if isinstance(v,(int,float,np.floating,np.integer)) else str(v) for v in row]
        for row in part.itertuples(index=False)]
    return jsonify(time=iso(part.index),columns=columns,values=values,offset=offset,rows=len(frame))

@blueprint.post("/api/snapshot")
def snapshot():
    data = _body()
    project = _project()
    run = data["run"]
    sim,case = Simulation.from_run(project,run)
    models = current_app.config.get("MODELS")
    folder = project.run_path(run)
    if models:
        for item in models.running():
            if os.path.dirname(item["path"]) == folder:
                models.stop(item["path"])
    result = sim.snapshot(run,data["time"],case)
    if models:
        try:
            port = models.open(project.run_path(run,result["file"]))
        except RuntimeError as err:
            raise SimulationError(f"ppedit failed to start: {err}") from err
        host = request.host.rsplit(":",1)[0] if not request.host.startswith("[") \
            else request.host.split("]")[0]+"]"
        result["url"] = f"http://{host}:{port}/?solve=pf&view=network"
    return jsonify(result)

@blueprint.get("/api/file")
def download():
    project = _project()
    path = _panel_path(project)
    return send_from_directory(os.path.dirname(path),os.path.basename(path),as_attachment=True)

