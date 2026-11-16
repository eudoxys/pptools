"""Tests for `pptools.pprun.server` and `pptools.pprun.runner` (real run processes on case9)"""

import time

def wait(client,run,timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = client.get(f"/pprun/api/run?project=demo&run={run}").get_json()["status"]
        if status["state"] != "running":
            return status
        time.sleep(0.3)
    raise AssertionError(f"run {run} did not finish")

def test_page_and_meta(client):
    assert b"pprun" in client.get("/pprun/?project=demo").data
    assert client.get("/pprun/static/app.js").status_code == 200
    assert client.get("/pprun/api/status").get_json() == {"tool":"pprun","status":"available","folder":"sims"}
    meta = client.get("/pprun/api/meta").get_json()
    assert "bus" in meta["tables"] and meta["defaults"]["freq"] == "1h" and meta["opf_modes"] == ["ac","dc","none"]
    assert any(g["group"] == "Power flow" for g in meta["options"])

def test_sim_lifecycle(client,post):
    status,sim = post("/pprun/api/sim/new",{"project":"demo","sim":"s1","model":"case9.py",
        "start":"2020-01-01 00:00","end":"2020-01-01 05:00"})
    assert status == 200 and sim["name"] == "s1.json" and sim["steps"] == 6 and sim["labels"]["bus"][4] == "bus 5"
    assert post("/pprun/api/sim/new",{"project":"demo","sim":"s1","model":"case9.py"})[0] == 400
    definition = {**sim["definition"],"freq":"30min","inputs":[{"file":"load.csv","table":"bus","column":"PD"}]}
    status,sim = post("/pprun/api/sim/save",{"project":"demo","sim":"s1.json","definition":definition})
    assert status == 200 and sim["definition"]["freq"] == "30min" and sim["steps"] == 11
    assert any("lacks" in x["message"] for x in sim["check"])
    proj = client.get("/pprun/api/project?project=demo").get_json()
    assert proj["models"] == ["case9.py"] and proj["data"] == ["load.csv"] and proj["sims"][0]["name"] == "s1.json"
    status,res = post("/pprun/api/run",{"project":"demo","sim":"s1"})
    assert status == 400 and "cannot run" in res["error"]
    assert post("/pprun/api/sim/save",{"project":"demo","sim":"s1","definition":{"opf":"xx"}})[0] == 400
    status,proj = post("/pprun/api/sim/delete",{"project":"demo","sim":"s1"})
    assert status == 200 and proj["sims"] == []
    assert client.get("/pprun/api/sim?project=demo&sim=s1").status_code == 400

def test_guard(client):
    assert client.post("/pprun/api/sim/new",json={}).status_code == 403
    assert client.get("/pprun/api/project?project=nope").status_code == 400

def test_input_table(client):
    head = client.get("/pprun/api/table?project=demo&file=load.csv&head=1").get_json()
    assert head["rows"] == 6 and head["columns"][:2] == ["0","1"] and head["first"] == "2020-01-01T00:00:00Z"
    page = client.get("/pprun/api/table?project=demo&file=load.csv&offset=2&limit=2").get_json()
    assert page["time"] == ["2020-01-01T02:00:00Z","2020-01-01T03:00:00Z"] and abs(page["values"][0][4] - 93.6) < 1e-9
    plot = client.get("/pprun/api/table?project=demo&file=load.csv&columns=4,6&points=10").get_json()
    assert plot["columns"] == ["4","6"] and len(plot["time"]) == 6 and plot["max"]["4"][0] == 90
    assert plot["time"][1] - plot["time"][0] == 3600000 and plot["time"][0] == 1577836800000
    assert client.get("/pprun/api/table?project=demo&file=nothere.csv&head=1").status_code == 404
    assert client.get("/pprun/api/table?project=demo&file=../x.csv&head=1").status_code == 400

def test_run_process(client,post,sim): # pylint: disable=unused-argument
    status,res = post("/pprun/api/run",{"project":"demo","sim":"base"})
    assert status == 200 and res["run"].startswith("base_") and res["status"]["state"] == "running"
    run = res["run"]
    final = wait(client,run)
    assert final["state"] == "done" and final["steps"] == 6 and not final["alive"]
    detail = client.get(f"/pprun/api/run?project=demo&run={run}").get_json()
    assert len(detail["times"]) == 6 and detail["profile"]["Completed iterations"] == 6
    assert [o["file"] for o in detail["outputs"]][-1] == "recorders.csv" and detail["labels"]["gen"]
    plot = client.get(f"/pprun/api/table?project=demo&run={run}&file=bus_VM.csv&points=100").get_json()
    assert len(plot["time"]) == 6 and len(plot["columns"]) == 8
    assert client.get(f"/pprun/api/file?project=demo&run={run}&file=gen_PG.csv").status_code == 200
    proj = client.get("/pprun/api/project?project=demo").get_json()
    assert proj["runs"][0]["name"] == run
    status,snap = post("/pprun/api/snapshot",{"project":"demo","run":run,"time":"2020-01-01T02:00:00Z"})
    assert status == 200 and snap["pf"] and "?solve=pf&view=network" in snap["url"]
    assert len(client.application.config["MODELS"].running()) == 1
    status,proj = post("/pprun/api/run/delete",{"project":"demo","run":run})
    assert status == 200 and proj["runs"] == [] and client.application.config["MODELS"].running() == []

def test_cancel(client,post,sim,project):
    sim.definition["end"] = "2020-01-03 00:00"
    sim.definition["inputs"] = []
    sim.save()
    status,res = post("/pprun/api/run",{"project":"demo","sim":"base"})
    assert status == 200
    run = res["run"]
    deadline = time.monotonic() + 60
    while client.get(f"/pprun/api/run?project=demo&run={run}").get_json()["status"]["steps"] < 1:
        assert time.monotonic() < deadline
        time.sleep(0.2)
    assert post("/pprun/api/run/delete",{"project":"demo","run":run})[0] == 400 # still running
    assert post("/pprun/api/cancel",{"project":"demo","run":run})[0] == 200
    final = wait(client,run)
    assert final["state"] == "cancelled" and 0 < final["steps"] < 49
    assert project.runs() == [run]
