"""Shared test setup for pprun

`project` is a project with `models/case9.py` (the PYPOWER built-in case)
and `data/load.csv`, a six-hour bus `PD` panel (hourly, from 2020-01-01
00:00 UTC, each bus's case load times 1.00, 1.02, ... 1.10); `sim` is a
saved simulation `base.json` of that model over those six hours with the
panel as its input. `app`, `client`, `post` are as in `pptools/_test`, on
the same projects folder.
"""

import pytest

from pptools import create_app
from pptools.project import Workspace
from pptools.ppmodel.case import Case
from pptools.pprun.sim import Simulation

START,END = "2020-01-01 00:00","2020-01-01 05:00"

def write_panel(path,case,hours=6,factor=0.02,naive=True,skip=None):
    """Write a bus PD panel for `case` to `path`"""
    lines = ["timestamp," + ",".join(str(n) for n in range(len(case.tables["bus"])))]
    for h in range(hours):
        if h == skip:
            continue
        stamp = f"2020-01-01 {h:02d}:00:00" + ("" if naive else "+00:00")
        lines.append(stamp + "," + ",".join(f"{row[2]*(1+factor*h):g}" for row in case.tables["bus"]))
    with open(path,"w",encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

@pytest.fixture(name="write_panel")
def write_panel_fixture():
    """The `write_panel` helper (test modules cannot import conftest under importlib mode)"""
    return write_panel

@pytest.fixture
def root(tmp_path):
    """Projects folder"""
    return str(tmp_path/"projects")

@pytest.fixture
def project(root):
    """Project `demo` with case9 and a six-hour load panel"""
    project = Workspace(root).create("demo")
    case = Case.builtin("case9")
    case.save(project.resolve("models","case9.py"))
    write_panel(project.resolve("data","load.csv"),case)
    return project

@pytest.fixture
def sim(project):
    """Simulation `base.json` of case9 over six hours with the load panel"""
    sim = Simulation.new(project,"base","case9.py",START,END)
    sim.definition["inputs"] = [{"file":"load.csv","table":"bus","column":"PD"}]
    sim.definition = sim.normalize(sim.definition)
    sim.save()
    return sim

@pytest.fixture
def app(root,project):
    """Front application on the projects folder holding `project`"""
    app = create_app(root)
    app.config["TESTING"] = True
    yield app
    app.config["RUNS"].stop_all()
    app.config["MODELS"].stop_all()

@pytest.fixture
def client(app):
    """Flask test client of `app`"""
    return app.test_client()

@pytest.fixture
def post(client):
    """POST JSON to the API and return (status, json)"""
    def _post(path,body=None):
        res = client.post(path,json=body or {},headers={"X-PPTools":"1"})
        return res.status_code,res.get_json()
    return _post
