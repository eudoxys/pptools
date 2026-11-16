"""Tests for `pptools.project` (fast, no network)"""

import os
import json

import pytest

from pptools.project import Workspace, Project, ProjectError, FOLDERS, RECORD

def test_create_layout(tmp_path):
    ws = Workspace(str(tmp_path))
    project = ws.create("study1","test study")
    assert sorted(os.listdir(project.path)) == sorted([RECORD,*FOLDERS])
    record = project.record
    assert record["application"] == "pptools"
    assert record["name"] == "study1" and record["description"] == "test study"
    assert record["created"].endswith("Z") and record["modified"] == record["created"]

def test_projects_ignores_other_folders(tmp_path):
    ws = Workspace(str(tmp_path))
    ws.create("b")
    ws.create("a")
    os.mkdir(tmp_path/"not_a_project")
    os.mkdir(tmp_path/".hidden")
    assert [p.name for p in ws.projects()] == ["a","b"]

@pytest.mark.parametrize("name",["",".x","../x","a/b","a b","x"*65,None])
def test_invalid_names(tmp_path,name):
    ws = Workspace(str(tmp_path))
    with pytest.raises(ProjectError):
        ws.create(name)

def test_duplicate_and_missing(tmp_path):
    ws = Workspace(str(tmp_path))
    ws.create("a")
    with pytest.raises(ProjectError,match="already exists"):
        ws.create("a")
    with pytest.raises(ProjectError,match="not found"):
        ws.get("b")
    with pytest.raises(ProjectError,match="not a pptools project"):
        Project(str(tmp_path))

def test_files_write_rename_delete(tmp_path):
    project = Workspace(str(tmp_path)).create("a")
    project.write("data","load.csv",b"timestamp,0\n")
    with pytest.raises(ProjectError,match="already exists"):
        project.write("data","load.csv",b"x")
    project.write("data","load.csv",b"timestamp,0,1\n",overwrite=True)
    files = project.files("data")
    assert [(f["name"],f["size"],f["ext"]) for f in files] == [("load.csv",14,"csv")]
    project.rename("data","load.csv","load2.csv")
    assert [f["name"] for f in project.files("data")] == ["load2.csv"]
    project.delete("data","load2.csv")
    assert project.files("data") == []
    with pytest.raises(ProjectError,match="not found"):
        project.delete("data","load2.csv")

@pytest.mark.parametrize("folder,name",[("data","../x.csv"),("data","/etc/passwd"),
    ("data",".secret"),("other","x.csv"),("..","x.csv")])
def test_paths_confined(tmp_path,folder,name):
    project = Workspace(str(tmp_path)).create("a")
    with pytest.raises(ProjectError):
        project.write(folder,name,b"x")

def test_update(tmp_path):
    project = Workspace(str(tmp_path)).create("a")
    record = project.update(description="new")
    assert record["description"] == "new"
    with open(os.path.join(project.path,RECORD),encoding="utf-8") as fh:
        assert json.load(fh)["description"] == "new"
    with pytest.raises(ProjectError):
        project.update(name="b")

def test_delete_project(tmp_path):
    ws = Workspace(str(tmp_path))
    ws.create("a")
    ws.delete("a")
    assert ws.projects() == []

def test_run_folders(tmp_path):
    project = Workspace(str(tmp_path)).create("p")
    assert project.runs() == []
    path = project.run_path("base_20200101T000000Z","bus_VM.csv")
    assert path == os.path.join(project.path,"outputs","base_20200101T000000Z","bus_VM.csv")
    os.makedirs(os.path.dirname(path))
    with open(path,"w",encoding="utf-8") as fh:
        fh.write("x")
    assert project.runs() == ["base_20200101T000000Z"]
    assert [f["name"] for f in project.files("outputs",run="base_20200101T000000Z")] == ["bus_VM.csv"]
    assert project.files("outputs") == [] # run folders are not files
    for bad in ("../x","a/b",".hidden"):
        with pytest.raises(ProjectError):
            project.run_path("r",bad)
        with pytest.raises(ProjectError):
            project.run_path(bad)
