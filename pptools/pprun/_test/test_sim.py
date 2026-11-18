"""Tests for `pptools.pprun.sim` (fast; one six-step case9 run in-process)"""

import os
import json

import pytest

from ppedit.case import Case
from pptools.pprun.sim import Simulation, SimulationError, option_groups, headers, row_labels, \
    OUTPUT_DEFAULTS, RUN_FILES, delete_run

START,END = "2020-01-01 00:00","2020-01-01 05:00"

def errors(sim):
    return [x["message"] for x in sim.check() if x["level"] == "error"]

def test_defaults(project):
    sim = Simulation.new(project,"x","case9.py",START,END)
    d = sim.definition
    assert d["freq"] == "1h" and d["tz"] == "UTC" and d["opf"] == "ac" and d["stop_on_fail"] is True
    assert [(o["table"],o["column"]) for o in d["outputs"]] == OUTPUT_DEFAULTS
    assert d["recorders"][0]["target"] == ["cost"] and d["oce"] is None and d["base_kv"] == 230.0
    assert os.path.isfile(project.resolve("sims","x.json"))
    with pytest.raises(SimulationError,match="already exists"):
        Simulation.new(project,"x","case9.py")
    saved = json.load(open(project.resolve("sims","x.json"),encoding="utf-8"))
    assert saved["application"] == "pptools" and saved["tool"] == "pprun"

def test_time_range(project):
    sim = Simulation(project,"t",Simulation.defaults("case9.py",START,END))
    index = sim.time_range()
    assert len(index) == 6 and str(index.tz) == "UTC"
    sim.definition.update(start="2020-01-01 00:00-07:00",end="2020-01-01 01:00-07:00",freq="15min")
    index = sim.time_range()
    assert len(index) == 5 and index[0].hour == 7
    sim.definition.update(start="2020-01-01 00:00",end="2020-01-01 01:00",tz="US/Pacific",freq="1h")
    assert sim.time_range()[0].hour == 8
    sim.definition.update(inclusive="left")
    assert len(sim.time_range()) == 1
    sim.definition.update(freq="bogus")
    with pytest.raises(SimulationError,match="invalid time range"):
        sim.time_range()

def test_normalize_rejects(project):
    for bad,match in [({"opf":"xx"},"opf"),({"inclusive":"some"},"inclusive"),({"options":{"NOPE":1}},"unknown PYPOWER"),
            ({"options":{"PF_TOL":"abc"}},"not a float"),({"oce":{"bogus":1}},"unknown oce"),({"inputs":"x"},"must be a list"),
            ({"abs_err":"x"},"not a number")]:
        with pytest.raises(SimulationError,match=match):
            Simulation.normalize(bad)
    d = Simulation.normalize({"options":{"pf_tol":"1e-6","enforce_q_lims":"true","pf_max_it":"20","VERBOSE":""},"oce":True,
        "recorders":[{"name":"c","target":"cost, baseMVA"}]})
    assert d["options"] == {"PF_TOL":1e-6,"ENFORCE_Q_LIMS":True,"PF_MAX_IT":20}
    assert d["oce"]["margin"] == 0.15 and d["oce"]["costs"]["powerline"] == 5.0
    assert d["recorders"][0]["target"] == ["cost","baseMVA"]

def test_option_groups():
    groups = option_groups()
    names = {o["name"]:o for g in groups for o in g["options"]}
    assert {"PF_ALG","PF_TOL","OPF_ALG","PDIPM_MAX_IT","VERBOSE","CPF_STEP"} <= set(names)
    assert names["VERBOSE"]["default"] == 0 and names["VERBOSE"]["pypower"] == 1 # PPModel.default_options wins
    assert names["ENFORCE_Q_LIMS"]["type"] == "bool"

def test_headers_and_labels():
    cols = headers()
    assert cols["bus"][:3] == ["BUS_I","BUS_TYPE","PD"] and "PF" in cols["branch"] and "LAM_P" in cols["bus"]
    labels = row_labels(Case.builtin("case9"))
    assert labels["bus"][0] == "bus 1" and labels["branch"][0] == "1-4" and labels["gen"][1] == "gen 1 @ bus 2"

def test_check_ok(sim):
    assert errors(sim) == []

def test_check_finds_problems(project,sim):
    d = sim.definition
    d["inputs"].append({"file":"nothere.csv","table":"bus","column":"QD","scale":1,"offset":0,"mapping":""})
    d["inputs"].append({"file":"load.csv","table":"bus","column":"PD","scale":1,"offset":0,"mapping":""})
    d["outputs"].append({"table":"bus","column":"NOPE","scale":1,"offset":0,"format":"g"})
    d["recorders"].append({"name":"cost","target":["cost"],"scale":1,"offset":0,"format":"g"})
    msgs = " | ".join(errors(sim))
    assert "nothere.csv' not found" in msgs and "more than one input" in msgs
    assert "unknown case column bus.NOPE" in msgs and "used twice" in msgs
    sim2 = Simulation(project,"y",Simulation.defaults("missing.py",START,START))
    msgs = " | ".join(errors(sim2))
    assert "not found" in msgs and "needs at least two" in msgs

def test_check_panel_columns_and_coverage(project,sim,write_panel):
    case = Case.builtin("case9")
    write_panel(project.resolve("data","gap.csv"),case,skip=3)
    sim.definition["inputs"] = [{"file":"gap.csv","table":"bus","column":"PD","scale":1,"offset":0,"mapping":""}]
    assert any("lacks 1 of 6" in m for m in errors(sim))
    sim.definition["stop_on_fail"] = False
    assert errors(sim) == [] and any("lacks 1 of 6" in x["message"] for x in sim.check())
    with open(project.resolve("data","bad.csv"),"w",encoding="utf-8") as fh:
        fh.write("timestamp,0,42\n2020-01-01 00:00:00,1,2\n")
    sim.definition["inputs"] = [{"file":"bad.csv","table":"bus","column":"PD","scale":1,"offset":0,"mapping":""}]
    assert any("not bus row numbers" in m for m in errors(sim))
    with open(project.resolve("data","bybus.csv"),"w",encoding="utf-8") as fh:
        fh.write("timestamp,5,7\n" + "".join(f"2020-01-01 {h:02d}:00:00,90,100\n" for h in range(6)))
    sim.definition["inputs"] = [{"file":"bybus.csv","table":"bus","column":"PD","scale":1,"offset":0,"mapping":"BUS_I"}]
    assert errors(sim) == []
    sim.definition["inputs"][0]["mapping"] = "ZONE"
    assert any("match no bus ZONE" in m for m in errors(sim))

def test_check_warns(project,sim):
    sim.definition["opf"] = "none"
    sim.definition["oce"] = Simulation.normalize({"oce":True})["oce"]
    msgs = [x for x in sim.check()]
    assert any("'cost' exists only after OPF" in x["message"] for x in msgs if x["level"] == "error")
    assert any("experimental" in x["message"] for x in msgs if x["level"] == "warning")

def test_run(project,sim):
    run = "base_test"
    folder = project.run_path(run)
    status = sim.run(folder)
    assert status["state"] == "done" and status["steps"] == 6 and status["total"] == 6 and status["errors"] == 0
    names = set(os.listdir(folder))
    assert {RUN_FILES[k] for k in ("definition","model","status","profile","errors","log","recorders")} <= names
    assert {f"{t}_{c}.csv" for t,c in OUTPUT_DEFAULTS} <= names
    pg = Simulation.read_panel(os.path.join(folder,"gen_PG.csv"))
    pd_ = Simulation.read_panel(project.resolve("data","load.csv"))
    assert len(pg) == 6 and list(pg.columns) == ["0","1","2"] and str(pg.index.tz) == "UTC"
    # generation follows the load panel and covers it (losses are positive)
    total = pg.sum(axis=1).to_numpy()
    load = pd_.sum(axis=1).to_numpy()
    assert all(total > load) and all(total[1:] > total[:-1])
    cost = Simulation.read_panel(os.path.join(folder,"recorders.csv"))
    assert list(cost.columns) == ["cost"] and cost["cost"].is_monotonic_increasing
    assert project.runs() == [run]
    assert json.load(open(os.path.join(folder,"profile.json"),encoding="utf-8"))["Completed iterations"] == 6
    snap = Simulation.from_run(project,run)[0].snapshot(run,"2020-01-01T03:10:00Z",Case.load(os.path.join(folder,"model.json")))
    assert snap["time"] == "2020-01-01T03:00:00Z" and snap["opf"] is True and snap["pf"] is True
    solved = Case.load(project.run_path(run,snap["file"]))
    pg3 = sum(row[1] for row in solved.tables["gen"])
    assert abs(pg3 - total[3]) < 0.01 # the snapshot reproduces the run's dispatch
    assert solved.tables["areas"]
    snap2 = Simulation.from_run(project,run)[0].snapshot(run,"2020-01-01 01:00",Case.load(os.path.join(folder,"model.json")))
    assert [x for x in os.listdir(folder) if x.startswith("snapshot_")] == [snap2["file"]]
    delete_run(project,run)
    assert project.runs() == []

def test_run_failure_and_cancel(project,sim,write_panel):
    case = Case.builtin("case9")
    write_panel(project.resolve("data","gap.csv"),case,skip=2)
    sim.definition["inputs"][0]["file"] = "gap.csv"
    status = sim.run(project.run_path("gap"))
    assert status["state"] == "failed" and status["steps"] == 2
    assert "Input error" in open(project.run_path("gap","errors.txt"),encoding="utf-8").read()
    folder = project.run_path("cancelled")
    os.makedirs(folder)
    open(os.path.join(folder,"cancel"),"w",encoding="utf-8").close()
    sim.definition["inputs"][0]["file"] = "load.csv"
    status = sim.run(folder)
    assert status["state"] == "cancelled" and status["steps"] == 0 and not os.path.exists(os.path.join(folder,"cancel"))

def test_run_model_error(project):
    sim = Simulation(project,"bad",Simulation.defaults("missing.py",START,END))
    status = sim.run(project.run_path("bad"))
    assert status["state"] == "failed" and "not found" in status["message"]
