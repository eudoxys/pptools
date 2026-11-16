"""Tests for `pptools.server` and the planned tools' pages (fast, no network)"""

import io
import time
import urllib.request

def test_meta(client):
    data = client.get("/api/meta").get_json()
    assert [t["name"] for t in data["tools"]] == ["ppmodel","ppdata","ppsim","ppoutput"]
    assert list(data["folders"]) == ["models","data","sims","outputs"]
    assert "case9" in data["builtin"]

def test_index(client):
    assert b"pptools" in client.get("/").data
    assert client.get("/static/app.js").status_code == 200

def test_post_guard(client):
    assert client.post("/api/projects/new",json={"name":"a"}).status_code == 403
    res = client.post("/api/projects/new",data="name=a",headers={"X-PPTools":"1",
        "Content-Type":"application/x-www-form-urlencoded"})
    assert res.status_code == 403

def test_remote_refused(client):
    assert client.get("/api/meta",headers={"Host":"example.com"}).status_code == 403

def test_project_lifecycle(client,post):
    status,data = post("/api/projects/new",{"name":"s1","description":"first"})
    assert status == 200 and data["name"] == "s1"
    assert set(data["folders"]) == {"models","data","sims","outputs"}
    assert client.get("/api/projects").get_json()["projects"][0]["description"] == "first"
    status,data = post("/api/projects/s1/update",{"description":"changed"})
    assert data["description"] == "changed"
    status,data = post("/api/projects/s1/delete",{})
    assert status == 400
    status,data = post("/api/projects/s1/delete",{"confirm":"s1"})
    assert data == {"deleted":"s1"}
    assert client.get("/api/projects/s1").status_code == 400

def test_upload_rename_remove_download(client,post):
    post("/api/projects/new",{"name":"s1"})
    res = client.post("/api/projects/s1/upload",headers={"X-PPTools":"1"},
        data={"folder":"data","file":(io.BytesIO(b"timestamp,0\n"),"load.csv")})
    assert res.status_code == 200
    assert [f["name"] for f in res.get_json()["folders"]["data"]] == ["load.csv"]
    res = client.post("/api/projects/s1/upload",headers={"X-PPTools":"1"},
        data={"folder":"data","file":(io.BytesIO(b"x"),"load.csv")})
    assert res.status_code == 400
    res = client.post("/api/projects/s1/upload",headers={"X-PPTools":"1"},
        data={"folder":"data","file":(io.BytesIO(b"x"),"../evil.csv")})
    assert res.status_code == 200 # basename only
    assert client.get("/api/projects/s1/file/data/load.csv").data == b"timestamp,0\n"
    status,data = post("/api/projects/s1/rename",{"folder":"data","file":"load.csv","new":"l.csv"})
    assert status == 200 and "l.csv" in [f["name"] for f in data["folders"]["data"]]
    status,data = post("/api/projects/s1/remove",{"folder":"data","file":"l.csv"})
    assert [f["name"] for f in data["folders"]["data"]] == ["evil.csv"]
    assert client.get("/api/projects/s1/file/data/..%2Fpptools.json").status_code in (400,404)

def test_new_model(client,post):
    post("/api/projects/new",{"name":"s1"})
    status,data = post("/api/projects/s1/models/new",{"file":"c9.glm","template":"case9"})
    assert status == 200 and [f["name"] for f in data["folders"]["models"]] == ["c9.glm"]
    assert b"module pypower" in client.get("/api/projects/s1/file/models/c9.glm").data
    status,data = post("/api/projects/s1/models/new",{"file":"c9.glm"})
    assert status == 400
    status,data = post("/api/projects/s1/models/new",{"file":"x.raw"})
    assert status == 400
    status,data = post("/api/projects/s1/models/new",{"file":"empty.py"})
    assert status == 200

def test_ppmodel_launch(client,post):
    post("/api/projects/new",{"name":"s1"})
    post("/api/projects/s1/models/new",{"file":"c9.py","template":"case9"})
    status,data = post("/api/ppmodel/open",{"project":"s1","file":"c9.py"})
    assert status == 200, data
    port = data["port"]
    assert data["url"] == f"http://localhost:{port}/"
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state",timeout=10) as res:
        assert b"\"bus\":9" in res.read()
    status,again = post("/api/ppmodel/open",{"project":"s1","file":"c9.py"})
    assert again["port"] == port # reused
    running = client.get("/api/ppmodel").get_json()["running"]
    assert running == [{"project":"s1","file":"c9.py","url":data["url"],"port":port}]
    status,data = post("/api/ppmodel/stop",{"project":"s1","file":"c9.py"})
    assert data == {"stopped":True}
    assert client.get("/api/ppmodel").get_json()["running"] == []

def test_ppmodel_refuses(post):
    post("/api/projects/new",{"name":"s1"})
    assert post("/api/ppmodel/open",{"project":"s1","file":"nothere.glm"})[0] == 400
    assert post("/api/ppmodel/open",{"project":"s1","file":"x.csv"})[0] == 400

def test_stub_pages(client,post):
    post("/api/projects/new",{"name":"s1"})
    for tool,folder in [("ppdata","data"),("ppsim","sims"),("ppoutput","outputs")]:
        page = client.get(f"/{tool}/?project=s1").data.decode()
        assert "planned" in page and f"{folder}/" in page and "s1" in page
        assert client.get(f"/{tool}/").status_code == 200
        assert "not found" in client.get(f"/{tool}/?project=nope").data.decode()
        assert client.get(f"/{tool}/api/status").get_json() == {"tool":tool,"status":"planned","folder":folder}

def test_exit(tmp_path):
    from pptools import create_app # pylint: disable=import-outside-toplevel
    called = []
    app = create_app(str(tmp_path),shutdown=lambda: called.append(True))
    res = app.test_client().post("/api/exit",json={},headers={"X-PPTools":"1"})
    assert res.get_json() == {"exit":True}
    time.sleep(0.5)
    assert called == [True]
