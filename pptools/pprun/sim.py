"""Simulation definitions and runs

A `Simulation` is one definition file `sims/<sim>.json` of a project
(DESIGN.md decision #13): the model file, the input panels and how each
maps onto a case column, the time range, the solver options, and the
outputs and recorders to write. `Simulation.check()` reports problems
before a run, `Simulation.run()` runs it with `pypower_sim` into a run
folder `outputs/<run>/` (decision #16), and `Simulation.snapshot()`
re-solves one time step of a run for the network view (decision #17).

Examples
--------

    >>> import tempfile
    >>> from pptools.project import Workspace
    >>> from ppedit.case import Case
    >>> project = Workspace(tempfile.mkdtemp()).create("demo")
    >>> Case.builtin("case9").save(project.resolve("models","case9.py"))
    >>> sim = Simulation.new(project,"base.json","case9.py",start="2020-01-01 00:00",end="2020-01-01 03:00")
    >>> sim.definition["freq"], sim.definition["opf"], len(sim.time_range())
    ('1h', 'ac', 4)
    >>> [x["message"] for x in sim.check() if x["level"] == "error"]
    []

Caveats
-------

  - `pypower` `runpf`/`runopf` ignore `dcline` rows; only ppedit's own
    solver models DC lines (the check warns).
  - Inputs are looked up by exact UTC timestamp (`pypower_sim` decision #9):
    a time step missing from a panel is an input error.
  - The initial OCE (`oce`) is experimental, and its success checks are
    inverted in `pypower_sim` (its DESIGN.md "Known issues").
"""

import os
import io
import sys
import json
import math
import time
import shutil
import logging
import datetime
import warnings
import functools
import traceback

from pptools.project import Project, ProjectError, check_name
from ppedit.case import Case, CaseError

_logger = logging.getLogger(__file__)

class SimulationError(ValueError):
    """Invalid simulation definition or run request"""

TABLES = ["bus","gen","branch","gencost","dcline","dclinecost"]
"""Case tables inputs and outputs may name (`pypower_sim` `standard_idx`)"""

OPF_MODES = {"ac":True,"dc":False,"none":None}
"""OPF mode -> `run_timeseries(use_acopf=...)`"""

INCLUSIVE = ["both","neither","left","right"]
"""`pandas.date_range` `inclusive` values"""

OUTPUT_DEFAULTS = [("bus","VM"),("bus","VA"),("gen","PG"),("gen","QG"),
    ("branch","PF"),("branch","QF"),("branch","PT"),("branch","QT")]
"""Outputs of a new simulation"""

OCE_DEFAULTS = {
    "margin": 0.15,
    "allin": False,
    "setpoints": None,
    "smallangles": None,
    "costs": {"capacitor":0.1,"condensor":1.0,"transformer":2.0,"powerline":5.0},
    "cvx": {"canon_backend":"SCIPY"},
    }
"""`pypower_sim._runoce.OceOptions` defaults (an enabled `oce` starts from these)"""

BASE_KV_DEFAULT = 230.0
"""`pypower_sim.PPModel.default_values["BASE_KV"]`"""

RUN_FILES = {"definition":"simulation.json","model":"model.json","status":"status.json",
    "profile":"profile.json","errors":"errors.txt","log":"log.txt","cancel":"cancel",
    "recorders":"recorders.csv"}
"""Fixed file names in a run folder (decision #16)"""

def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _version() -> str:
    from pptools import __version__ # pylint: disable=import-outside-toplevel
    return __version__

def headers() -> dict:
    """Column names of each case table, as `pypower_sim.PPModel.get_header`
    gives them (including the result columns)"""
    from pypower_sim.ppmodel import PPModel # pylint: disable=import-outside-toplevel
    return {table:PPModel.get_header(table) for table in TABLES}

@functools.lru_cache(maxsize=1)
def option_groups() -> list[dict]:
    """PYPOWER solver options passed through `PPModel.options`, grouped as
    in `pypower.ppoption`: `[{"group", "options": [{"name", "default",
    "pypower", "type", "doc"}]}]`; `default` is `PPModel.default_options`
    where it sets the option, else `pypower`'s default"""
    # pylint: disable=import-outside-toplevel
    from pypower import ppoption as ppo
    from pypower_sim.ppmodel import PPModel
    groups = []
    for title,items,note in (
            ("Power flow",ppo.PF_OPTIONS,""),
            ("Optimal power flow",ppo.OPF_OPTIONS,""),
            ("Interior point solver (PDIPM)",ppo.PDIPM_OPTIONS,""),
            ("Output",ppo.OUTPUT_OPTIONS,"solver text goes to the run's log.txt"),
            ("Continuation power flow",ppo.CPF_OPTIONS,"not used by time-series runs"),
            ):
        options = []
        for name,value,doc in items:
            key = name.upper()
            default = PPModel.default_options.get(key,value)
            kind = "bool" if isinstance(value,bool) else "int" if isinstance(value,int) \
                else "float" if isinstance(value,float) else "str"
            options.append({"name":key,"default":_jsonsafe(default),"pypower":_jsonsafe(value),
                "type":kind,"doc":" ".join(doc.split())})
        groups.append({"group":title,"note":note,"options":options})
    return groups

def _jsonsafe(value):
    if isinstance(value,float) and math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    return value

def _option_value(spec:dict,value):
    """Convert a stored option to the type of its `pypower` default"""
    kind = spec["type"]
    if kind == "bool":
        if isinstance(value,str):
            return value.strip().lower() in ("1","true","yes","on")
        return bool(value)
    if kind == "int":
        return int(float(value))
    if kind == "float":
        return float(value)
    return str(value)

def _float(value,what,allow_none=False):
    if value is None or value == "":
        if allow_none:
            return None
        raise SimulationError(f"{what} is required")
    try:
        return float(value)
    except (TypeError,ValueError) as err:
        raise SimulationError(f"{what} '{value}' is not a number") from err

def _bool(value):
    if isinstance(value,str):
        return value.strip().lower() in ("1","true","yes","on")
    return bool(value)

def row_labels(case:Case) -> dict:
    """Readable labels of each table's rows (row number -> text): bus number,
    generator bus, branch and DC line ends"""
    t = case.tables
    return {
        "bus": [f"bus {r[0]:g}" for r in t["bus"]],
        "gen": [f"gen {n} @ bus {r[0]:g}" for n,r in enumerate(t["gen"])],
        "gencost": [f"gencost {n}" for n in range(len(t["gencost"]))],
        "branch": [f"{r[0]:g}-{r[1]:g}" for r in t["branch"]],
        "dcline": [f"dc {r[0]:g}-{r[1]:g}" for r in t["dcline"]],
        "dclinecost": [f"dclinecost {n}" for n in range(len(t["dclinecost"]))],
        }

class Simulation:
    """One simulation definition of a project

    Arguments
    ---------

      - `project`: the `pptools.project.Project`

      - `name`: file name in `sims/` (`.json` is added when missing)

      - `definition`: the definition (missing fields get defaults; see
        `normalize`), or `None` to read the file

    Exceptions
    ----------

      - `SimulationError`: invalid definition, or the file cannot be read
      - `pptools.project.ProjectError`: invalid name
    """

    def __init__(self,project:Project,name:str,definition:dict|None=None):
        if not name.endswith(".json"):
            name += ".json"
        self.project = project
        """The project"""
        self.name = check_name(name,"simulation name")
        """File name in `sims/`"""
        self.path = project.resolve("sims",self.name)
        """Path of the definition file"""
        if definition is None:
            try:
                with open(self.path,encoding="utf-8") as fh:
                    definition = json.load(fh)
            except FileNotFoundError as err:
                raise SimulationError(f"'sims/{self.name}' not found") from err
            except (OSError,ValueError) as err:
                raise SimulationError(f"cannot read 'sims/{self.name}': {err}") from err
        self.definition = self.normalize(definition)
        """The definition with defaults filled in (see the DESIGN.md schema)"""

    @property
    def stem(self) -> str:
        """Simulation name without `.json`"""
        return self.name[:-5]

    # ----- definitions -----

    @staticmethod
    def defaults(model:str="",start:str="",end:str="") -> dict:
        """A new definition for `model` from `start` to `end`"""
        return {
            "model": model,
            "start": start,
            "end": end,
            "freq": "1h",
            "tz": "UTC",
            "inclusive": "both",
            "opf": "ac",
            "stop_on_fail": True,
            "violations": False,
            "abs_err": None,
            "rel_err": None,
            "oce": None,
            "base_kv": BASE_KV_DEFAULT,
            "options": {},
            "inputs": [],
            "outputs": [{"table":t,"column":c,"scale":1.0,"offset":0.0,"format":"g"}
                for t,c in OUTPUT_DEFAULTS],
            "recorders": [{"name":"cost","target":["cost"],"scale":1.0,"offset":0.0,"format":"g"}],
            }

    @classmethod
    def normalize(cls,definition:dict) -> dict:
        """Return `definition` with defaults filled in and values converted;
        raises `SimulationError` for values of the wrong kind (references to
        files, tables and columns are left to `check`)"""
        # pylint: disable=too-many-branches,too-many-statements
        if not isinstance(definition,dict):
            raise SimulationError("a simulation definition must be a JSON object")
        d = cls.defaults()
        d.update({k:v for k,v in definition.items() if k in d})
        for key in ("model","start","end","freq","tz","inclusive","opf"):
            d[key] = "" if d[key] is None else str(d[key]).strip()
        d["freq"] = d["freq"] or "1h"
        d["tz"] = d["tz"] or "UTC"
        if d["inclusive"] not in INCLUSIVE:
            raise SimulationError(f"inclusive must be one of {', '.join(INCLUSIVE)}")
        if d["opf"] not in OPF_MODES:
            raise SimulationError(f"opf must be one of {', '.join(OPF_MODES)}")
        d["stop_on_fail"] = _bool(d["stop_on_fail"])
        d["violations"] = _bool(d["violations"])
        d["abs_err"] = _float(d["abs_err"],"abs_err",True)
        d["rel_err"] = _float(d["rel_err"],"rel_err",True)
        d["base_kv"] = _float(d["base_kv"],"base_kv",True)
        if d["oce"] is not None and d["oce"] is not False:
            if d["oce"] is True:
                d["oce"] = {}
            if not isinstance(d["oce"],dict):
                raise SimulationError("oce must be null or an object")
            oce = json.loads(json.dumps(OCE_DEFAULTS))
            for key,value in d["oce"].items():
                if key not in oce:
                    raise SimulationError(f"unknown oce option '{key}'")
                if key in ("costs","cvx"):
                    if not isinstance(value,dict):
                        raise SimulationError(f"oce {key} must be an object")
                    oce[key].update(value)
                else:
                    oce[key] = value
            oce["margin"] = _float(oce["margin"],"oce margin")
            oce["allin"] = _bool(oce["allin"])
            oce["costs"] = {k:_float(v,f"oce cost {k}") for k,v in oce["costs"].items()}
            if oce["setpoints"] not in (None,True,False):
                oce["setpoints"] = _float(oce["setpoints"],"oce setpoints")
            if isinstance(oce["smallangles"],list):
                oce["smallangles"] = [_float(x,"oce smallangles") for x in oce["smallangles"]]
            elif oce["smallangles"] is not None:
                oce["smallangles"] = _float(oce["smallangles"],"oce smallangles",True)
            d["oce"] = oce
        else:
            d["oce"] = None
        if not isinstance(d["options"],dict):
            raise SimulationError("options must be an object")
        specs = {o["name"]:o for g in option_groups() for o in g["options"]}
        options = {}
        for key,value in d["options"].items():
            key = str(key).upper()
            if key not in specs:
                raise SimulationError(f"unknown PYPOWER option '{key}'")
            if value is None or value == "":
                continue
            try:
                options[key] = _option_value(specs[key],value)
            except (TypeError,ValueError) as err:
                raise SimulationError(f"option {key}: '{value}' is not a {specs[key]['type']}") from err
        d["options"] = options
        for key,fields in (("inputs",("file","table","column")),("outputs",("table","column")),
                ("recorders",("name",))):
            if not isinstance(d[key],list):
                raise SimulationError(f"{key} must be a list")
            items = []
            for n,item in enumerate(d[key]):
                if not isinstance(item,dict):
                    raise SimulationError(f"{key}[{n}] must be an object")
                out = {f:str(item.get(f,"")).strip() for f in fields}
                out["scale"] = _float(item.get("scale",1.0),f"{key}[{n}] scale")
                out["offset"] = _float(item.get("offset",0.0),f"{key}[{n}] offset")
                if key == "inputs":
                    out["mapping"] = str(item.get("mapping") or "").strip()
                else:
                    out["format"] = str(item.get("format") or "g").strip() or "g"
                if key == "recorders":
                    target = item.get("target",[])
                    if isinstance(target,str):
                        target = [x for x in target.replace(","," ").split() if x]
                    out["target"] = [str(x) for x in target]
                items.append(out)
            d[key] = items
        return d

    @classmethod
    def new(cls,project:Project,name:str,model:str,start:str="",end:str="", # pylint: disable=too-many-arguments,too-many-positional-arguments
            overwrite:bool=False) -> "Simulation":
        """Create and save a new definition for model file `model`; when
        `start`/`end` are blank the range is the first day of the first input
        found later, or today (UTC)"""
        if not start:
            day = datetime.datetime.now(datetime.timezone.utc).date()
            start,end = f"{day} 00:00",f"{day + datetime.timedelta(days=1)} 00:00"
        sim = cls(project,name,cls.defaults(model,start,end))
        if os.path.exists(sim.path) and not overwrite:
            raise SimulationError(f"'sims/{sim.name}' already exists")
        sim.save()
        return sim

    def save(self):
        """Write the definition to `sims/<name>`"""
        data = {"application":"pptools","tool":"pprun","version":_version(),**self.definition}
        os.makedirs(os.path.dirname(self.path),exist_ok=True)
        with open(self.path,"w",encoding="utf-8") as fh:
            json.dump(data,fh,indent=2)
            fh.write("\n")
        self.project.update()

    # ----- inputs -----

    def time_range(self):
        """The time steps (`pandas.DatetimeIndex`, UTC)

        Exceptions
        ----------

          - `SimulationError`: missing or invalid `start`, `end`, `freq`, `tz`
        """
        import pandas as pd # pylint: disable=import-outside-toplevel
        d = self.definition
        if not d["start"] or not d["end"]:
            raise SimulationError("start and end are required")
        try:
            ends = []
            for value in (d["start"],d["end"]):
                ts = pd.Timestamp(value)
                ends.append(ts.tz_localize(d["tz"]) if ts.tzinfo is None else ts)
            index = pd.date_range(ends[0],ends[1],freq=d["freq"],inclusive=d["inclusive"])
        except Exception as err: # pandas raises many kinds
            raise SimulationError(f"invalid time range: {err}") from err
        return index.tz_convert("UTC")

    def load_case(self) -> Case:
        """Read the model file (`models/<model>`)"""
        if not self.definition["model"]:
            raise SimulationError("no model chosen")
        path = self.project.resolve("models",self.definition["model"])
        if not os.path.isfile(path):
            raise SimulationError(f"model 'models/{self.definition['model']}' not found")
        try:
            return Case.load(path)
        except (CaseError,OSError) as err:
            raise SimulationError(f"cannot read model '{self.definition['model']}': {err}") from err

    def input_path(self,item:dict) -> str:
        """Path of an input panel (`data/<file>`)"""
        return self.project.resolve("data",item["file"])

    @staticmethod
    def read_panel(path:str):
        """Read a panel or output CSV (first column the timestamps) as a
        frame with a UTC index (naive timestamps are UTC); cached by file
        modification time"""
        stat = os.stat(path)
        return _read_csv(path,stat.st_mtime_ns,stat.st_size).copy()

    # ----- checks -----

    def check(self,case:Case|None=None) -> list[dict]:
        """Problems that would stop or spoil a run: `[{"level": "error" |
        "warning", "where", "message"}]`; errors block `run`"""
        # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        issues = []
        def add(level,where,message):
            issues.append({"level":level,"where":where,"message":message})
        d = self.definition
        try:
            case = case or self.load_case()
        except (SimulationError,ProjectError) as err:
            add("error","model",str(err))
            case = None
        try:
            index = self.time_range()
            if len(index) < 2:
                add("error","time",f"the time range has {len(index)} step(s); pypower_sim needs at least two")
            elif len(index) > 200000:
                add("warning","time",f"the time range has {len(index)} steps")
        except SimulationError as err:
            add("error","time",str(err))
            index = None
        if case is not None:
            if not case.tables["bus"]:
                add("error","model","the model has no buses")
            if d["opf"] != "none" and not case.tables["gencost"]:
                add("warning","solver","the model has no gencost rows: pypower_sim skips OPF (PF only)")
            if case.tables["dcline"]:
                add("warning","model",f"the model has {len(case.tables['dcline'])} DC line(s): "
                    "pypower's PF and OPF ignore them in time-series runs")
        if d["oce"] is not None:
            add("warning","solver","initial OCE is experimental, and pypower_sim records "
                "its success as failure (pypower_sim DESIGN.md Known issues)")
            if d["opf"] == "none":
                add("warning","solver","initial OCE solves AC OPF even when OPF is off")
        cols = headers()
        sizes = {t:len(case.tables[t]) for t in TABLES} if case is not None else {}
        seen = set()
        for n,item in enumerate(d["inputs"]):
            where = f"input {n+1}"
            if (item["table"],item["column"]) in seen:
                add("error",where,f"{item['table']}.{item['column']} has more than one input")
            seen.add((item["table"],item["column"]))
            if item["table"] not in cols or item["column"] not in cols.get(item["table"],[]):
                add("error",where,f"unknown case column {item['table']}.{item['column']}")
                continue
            try:
                path = self.input_path(item)
            except ProjectError as err:
                add("error",where,str(err))
                continue
            if not os.path.isfile(path):
                add("error",where,f"'data/{item['file']}' not found")
                continue
            try:
                data = self.read_panel(path)
            except Exception as err: # pylint: disable=broad-except
                add("error",where,f"cannot read 'data/{item['file']}': {err}")
                continue
            if case is not None:
                rows = sizes[item["table"]]
                if item["mapping"]:
                    if item["mapping"] not in cols[item["table"]][:len(_case_columns(item["table"]))]:
                        add("error",where,f"mapping column '{item['mapping']}' is not a {item['table']} column")
                    else:
                        k = cols[item["table"]].index(item["mapping"])
                        keys = {_key(r[k]) for r in case.tables[item["table"]]}
                        missing = [c for c in data.columns if _key(c) not in keys]
                        if missing:
                            add("error",where,f"{len(missing)} column(s) match no {item['table']} "
                                f"{item['mapping']}: {', '.join(map(str,missing[:5]))}")
                else:
                    bad = [c for c in data.columns if not _is_row(c,rows)]
                    if bad:
                        add("error",where,f"{len(bad)} column(s) are not {item['table']} row numbers "
                            f"0..{rows-1}: {', '.join(map(str,bad[:5]))} (set a mapping column)")
            if index is not None and len(index):
                missing = index.difference(data.index)
                if len(missing):
                    add("error" if d["stop_on_fail"] else "warning",where,
                        f"'data/{item['file']}' lacks {len(missing)} of {len(index)} time steps "
                        f"(first {missing[0].strftime('%Y-%m-%d %H:%M:%S')} UTC)")
        names = set()
        for n,item in enumerate(d["outputs"]):
            where = f"output {n+1}"
            if item["table"] not in cols or item["column"] not in cols.get(item["table"],[]):
                add("error",where,f"unknown case column {item['table']}.{item['column']}")
                continue
            if (item["table"],item["column"]) in names:
                add("error",where,f"{item['table']}.{item['column']} is output more than once")
            names.add((item["table"],item["column"]))
            if case is not None and not sizes[item["table"]]:
                add("error",where,f"the model has no {item['table']} rows")
            if d["opf"] == "none" and (item["column"].startswith("MU_") or item["column"].startswith("LAM_")):
                add("warning",where,f"{item['column']} is an OPF result; OPF is off")
        recs = set()
        for n,item in enumerate(d["recorders"]):
            where = f"recorder {n+1}"
            if not item["name"] or not item["target"]:
                add("error",where,"a recorder needs a name and a target")
            if item["name"] in recs:
                add("error",where,f"recorder name '{item['name']}' is used twice")
            recs.add(item["name"])
            if item["target"][:1] == ["cost"] and (d["opf"] == "none" or
                    (case is not None and not case.tables["gencost"])):
                add("error" if d["stop_on_fail"] else "warning",where,
                    "'cost' exists only after OPF, which will not run")
        return issues

    # ----- running -----

    def _build(self,case:Case,folder:str|None):
        """`(PPModel, PPSolver)` for `case` with the inputs, options and (when
        `folder` is given) the outputs and recorders set"""
        # pylint: disable=import-outside-toplevel
        from pypower_sim.ppmodel import PPModel
        from pypower_sim.ppdata import PPData
        from pypower_sim.ppsolver import PPSolver
        class _Model(PPModel): # pylint: disable=too-few-public-methods
            default_values = {"BASE_KV":None} # applied below (decision #18)
        d = self.definition
        ppc = case.to_ppc(arrays=True)
        if d["base_kv"] is not None and len(ppc["bus"]):
            zero = ppc["bus"][:,9] == 0
            ppc["bus"][zero,9] = d["base_kv"]
        model = _Model(name=case.name,case=ppc)
        model.options = {**PPModel.default_options,**d["options"]}
        if d["abs_err"] is not None or d["rel_err"] is not None:
            model.get_violations = functools.partial(PPModel.get_violations,model,
                abs_err=d["abs_err"],rel_err=d["rel_err"])
        data = PPData(model)
        for item in d["inputs"]:
            mapping = item["mapping"] or None
            if mapping:
                mapping = (mapping,float) # case columns are numeric
            data.set_input(item["table"],item["column"],self.input_path(item),
                scale=item["scale"],offset=item["offset"],mapping=mapping)
            spec = model.inputs[(item["table"],item["column"])]
            spec["data"] = _utc(spec["data"])
        if folder:
            for item in d["outputs"]:
                data.set_output(item["table"],item["column"],
                    os.path.join(folder,output_file(item)),
                    scale=item["scale"],offset=item["offset"],formatting=item["format"])
            for item in d["recorders"]:
                data.set_recorder(os.path.join(folder,RUN_FILES["recorders"]),item["name"],item["target"],
                    scale=item["scale"],offset=item["offset"],formatting=item["format"])
        return model,PPSolver(model)

    def _oce(self):
        if self.definition["oce"] is None:
            return None
        from pypower_sim._runoce import OceOptions # pylint: disable=import-outside-toplevel
        return OceOptions(**json.loads(json.dumps(self.definition["oce"])))

    def run(self,folder:str,case:Case|None=None) -> dict:
        """Run the simulation into run folder `folder` (normally in a separate
        process: `python -m pptools.pprun run`); returns the final status

        Writes the files of decision #16. A `cancel` file appearing in
        `folder` stops the run at the next time step.
        """
        # pylint: disable=too-many-locals,too-many-statements,too-many-branches
        os.makedirs(folder,exist_ok=True)
        def path(key):
            return os.path.join(folder,RUN_FILES[key])
        status = {"state":"running","event":"starting","progress":0.0,"timestamp":None,
            "steps":0,"total":0,"errors":0,"started":_now(),"finished":None,"pid":os.getpid(),
            "simulation":self.name,"message":""}
        notes = []
        last = [0.0]
        def write(force=False):
            if force or time.monotonic() - last[0] >= 0.5:
                last[0] = time.monotonic()
                _write_json(path("status"),status)
        log = open(path("log"),"a",encoding="utf-8") # pylint: disable=consider-using-with
        stdout,stderr,showwarning = sys.stdout,sys.stderr,warnings.showwarning
        sys.stdout = sys.stderr = log
        def on_warning(message,category,filename,lineno,file=None,line=None): # pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments
            text = f"{category.__name__}: {message}"
            notes.append(f"{status['timestamp'] or ''} {text}".strip())
            print(text,file=log,flush=True)
        warnings.showwarning = on_warning
        model = None
        try:
            with open(path("definition"),"w",encoding="utf-8") as fh:
                json.dump({"application":"pptools","tool":"pprun","version":_version(),
                    **self.definition},fh,indent=2)
            case = case or self.load_case()
            case.save(path("model"))
            index = self.time_range()
            status["total"] = len(index)
            write(True)
            model,solver = self._build(case,folder)
            cancel = path("cancel")
            started = [0]
            def progress(timestamp=None,event=None,errors=None,progress=None): # pylint: disable=redefined-outer-name
                status["event"] = event
                status["timestamp"] = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if timestamp is not None else None
                status["errors"] = len(errors or []) + len(notes)
                if progress is not None and not math.isnan(float(progress)):
                    status["progress"] = round(float(progress),6)
                if event == "timestep":
                    status["steps"] = started[0] # steps finished before this one
                    started[0] += 1
                    write()
                else:
                    write(True)
                return os.path.exists(cancel)
            def on_fail(message):
                notes.append(f"{status['timestamp']} {message}")
            d = self.definition
            result = solver.run_timeseries(start=index[0],end=index[-1],freq=d["freq"],
                inclusive="both",progress=progress,call_on_fail=on_fail,
                stop_on_fail=d["stop_on_fail"],use_acopf=OPF_MODES[d["opf"]],
                with_oce=self._oce(),violations=d["violations"])
            done = (model.profile or {}).get("Completed iterations")
            if done is not None:
                status["steps"] = done
            event = status["event"]
            if event == "completed":
                status["state"] = "done"
            elif event == "interrupted" or (event == "initialization" and os.path.exists(cancel)):
                status["state"] = "cancelled"
            else:
                status["state"] = "failed"
                if event in ("initialization","initial_oce","peaktime_ok"):
                    status["message"] = "stopped during initial OCE"
            if isinstance(result,list) and result and status["state"] == "done" and d["stop_on_fail"]:
                status["state"] = "failed"
        except Exception as err: # pylint: disable=broad-except
            status["state"] = "failed"
            status["message"] = f"{type(err).__name__}: {err}"
            traceback.print_exc(file=log)
        finally:
            sys.stdout,sys.stderr,warnings.showwarning = stdout,stderr,showwarning
            errors = list(model.errors) if model is not None else []
            if model is not None:
                for spec in list(model.outputs.values()) + list(model.recorders.values()):
                    if spec.get("fh"):
                        spec["fh"].close()
                        spec["fh"] = None
                _write_json(path("profile"),model.profile or {})
            with open(path("errors"),"w",encoding="utf-8") as fh:
                for line in errors + notes + ([status["message"]] if status["message"] else []):
                    print(line,file=fh)
            status["errors"] = len(errors) + len(notes)
            status["finished"] = _now()
            if os.path.exists(path("cancel")):
                os.remove(path("cancel"))
            _write_json(path("status"),status)
            log.close()
        return status

    @classmethod
    def from_run(cls,project:Project,run:str) -> tuple["Simulation",Case]:
        """The simulation and model as run in `outputs/<run>/`"""
        folder = project.run_path(run)
        try:
            with open(os.path.join(folder,RUN_FILES["definition"]),encoding="utf-8") as fh:
                definition = json.load(fh)
            case = Case.load(os.path.join(folder,RUN_FILES["model"]))
        except (OSError,ValueError,CaseError) as err:
            raise SimulationError(f"cannot read run '{run}': {err}") from err
        status = run_status(folder)
        return cls(project,status.get("simulation") or run.rsplit("_",1)[0],definition),case

    def snapshot(self,run:str,when:str,case:Case) -> dict:
        """Re-solve the time step of run `run` nearest to `when` (UTC unless an
        offset is given) from `case` (the model as run) and the inputs, as the
        run did (inputs, OPF per the settings, then PF), and write the solved
        case to `outputs/<run>/snapshot_<YYYYMMDDTHHMMSSZ>.json`, replacing
        earlier snapshots of the run (decision #17)

        Returns
        -------

          - `dict`: `file` (in the run folder), `time` (ISO 8601 UTC),
            `opf` (success, or `None` when not run), `pf` (success), `notes`
        """
        # pylint: disable=too-many-locals
        import pandas as pd # pylint: disable=import-outside-toplevel
        index = self.time_range()
        try:
            t = pd.Timestamp(when)
        except ValueError as err:
            raise SimulationError(f"invalid time '{when}'") from err
        t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
        t = index[min(index.get_indexer([t],method="nearest")[0],len(index)-1)]
        notes = []
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                model,solver = self._build(case,None)
                if solver.update_inputs(t):
                    notes.append("some inputs have no value at this time step")
                opf = None
                if self.definition["opf"] != "none" and case.tables["gencost"]:
                    opf = bool(solver.solve_opf(use_acopf=OPF_MODES[self.definition["opf"]]))
                    if not opf:
                        notes.append("OPF failed at this time step; PF uses the input dispatch")
                pf = bool(solver.solve_pf())
                if not pf:
                    notes.append("PF failed at this time step")
            finally:
                sys.stdout = stdout
        notes += [str(w.message) for w in caught]
        solved = Case({k:v for k,v in model.case.items() if k != "gis"},name=case.name)
        solved.tables["areas"] = [list(r) for r in case.tables["areas"]]
        solved.geodata,solved.geotags = case.geodata,case.geotags
        stamp = t.strftime("%Y%m%dT%H%M%SZ")
        for name in os.listdir(self.project.run_path(run)):
            if name.startswith("snapshot_") and name.endswith(".json"):
                os.remove(self.project.run_path(run,name))
        file = f"snapshot_{stamp}.json"
        solved.save(self.project.run_path(run,file))
        return {"file":file,"time":t.strftime("%Y-%m-%dT%H:%M:%SZ"),"opf":opf,"pf":pf,"notes":notes}

def output_file(item:dict) -> str:
    """Run-folder file name of an output: `<table>_<column>.csv`"""
    return f"{item['table']}_{item['column']}.csv"

def _case_columns(table):
    from ppedit.case import COLUMNS # pylint: disable=import-outside-toplevel
    return COLUMNS.get(table,[])

def _key(value) -> str:
    try:
        f = float(value)
        return f"{f:g}"
    except (TypeError,ValueError):
        return str(value).strip()

def _is_row(name,rows:int) -> bool:
    try:
        n = float(name)
    except (TypeError,ValueError):
        return False
    return n == int(n) and 0 <= int(n) < rows

def _utc(frame):
    import pandas as pd # pylint: disable=import-outside-toplevel
    index = frame.index
    if not isinstance(index,pd.DatetimeIndex):
        index = pd.to_datetime(index.astype(str).str.replace(" UTC","",regex=False),utc=True)
    elif index.tz is None:
        index = index.tz_localize("UTC")
    else:
        index = index.tz_convert("UTC")
    frame.index = index
    frame.index.name = "datetime"
    return frame

@functools.lru_cache(maxsize=8)
def _read_csv(path,mtime,size): # pylint: disable=unused-argument
    import pandas as pd # pylint: disable=import-outside-toplevel
    frame = pd.read_csv(path,index_col=0)
    frame.index = pd.to_datetime(frame.index.astype(str).str.replace(" UTC","",regex=False),utc=False)
    return _utc(frame)

def _write_json(path,data):
    tmp = path + ".tmp"
    with open(tmp,"w",encoding="utf-8") as fh:
        json.dump(data,fh,indent=2,default=str)
    os.replace(tmp,path)

def run_status(folder:str) -> dict:
    """The run's `status.json` (an empty dict when missing or unreadable)"""
    try:
        with open(os.path.join(folder,RUN_FILES["status"]),encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError,ValueError):
        return {}

def delete_run(project:Project,run:str):
    """Delete run folder `outputs/<run>/` and everything in it (permanent)"""
    folder = project.run_path(run)
    if not os.path.isdir(folder):
        raise SimulationError(f"run '{run}' not found")
    shutil.rmtree(folder)
    project.update()
