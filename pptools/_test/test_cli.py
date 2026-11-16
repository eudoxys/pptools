"""Tests for `pptools.cli` (fast, no network)"""

from pptools import main, __version__

def test_version(capsys):
    try:
        main(["--version"])
    except SystemExit as err:
        assert err.code == 0
    assert capsys.readouterr().out.strip() == f"pptools {__version__}"

def test_new_and_list(tmp_path,capsys):
    root = str(tmp_path)
    assert main(["new","s1","--description","first","-r",root]) == 0
    assert capsys.readouterr().out.strip() == str(tmp_path/"s1")
    assert main(["new","s1","-r",root]) == 1
    assert "ERROR [pptools]" in capsys.readouterr().err
    assert main(["list","-r",root]) == 0
    assert capsys.readouterr().out.strip() == "s1  first"

def test_new_needs_name(tmp_path,capsys):
    assert main(["new","-r",str(tmp_path)]) == 1
    assert "needs a project NAME" in capsys.readouterr().err

import json
import socket
import threading
import time
import urllib.request

import pytest

from pptools.cli import running_server
from pptools.ppdata.cli import main as ppdata_main
from pptools.pprun.cli import main as pprun_main
from pptools.ppoutput.cli import main as ppoutput_main

TOOL_MAINS = {"ppdata":ppdata_main,"pprun":pprun_main,"ppoutput":ppoutput_main}

def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        return sock.getsockname()[1]

def _exit(port):
    req = urllib.request.Request(f"http://localhost:{port}/api/exit",data=b"{}",method="POST",
        headers={"Content-Type":"application/json","X-PPTools":"1"})
    with urllib.request.urlopen(req,timeout=5) as res:
        assert json.load(res) == {"exit":True}

def _start(target,port):
    out = {}
    thread = threading.Thread(target=lambda: out.update(code=target()))
    thread.start()
    for _ in range(100):
        if running_server("127.0.0.1",port):
            return thread,out
        time.sleep(0.05)
    raise AssertionError("server did not start")

@pytest.mark.parametrize("tool",TOOL_MAINS)
def test_tool_version(tool,capsys):
    try:
        TOOL_MAINS[tool](["--version"])
    except SystemExit as err:
        assert err.code == 0
    assert capsys.readouterr().out.strip() == f"{tool} {__version__}"

@pytest.mark.parametrize("tool",TOOL_MAINS)
def test_tool_starts_server(tool,tmp_path,capsys):
    root,port = str(tmp_path),_free_port()
    assert main(["new","s1","-r",root]) == 0
    thread,out = _start(lambda: TOOL_MAINS[tool](["-P","s1","-r",root,"-p",str(port),"--no-browser"]),port)
    with urllib.request.urlopen(f"http://localhost:{port}/{tool}/?project=s1",timeout=5) as res:
        assert ("planned" in res.read().decode()) == (tool != "pprun")
    _exit(port)
    thread.join(5)
    assert not thread.is_alive() and out["code"] == 0
    text = capsys.readouterr().out
    assert f"URL........ http://localhost:{port}/{tool}/?project=s1" in text
    assert f"thanks for using {tool}" in text

def test_tool_reuses_running_server(tmp_path,capsys):
    root,port = str(tmp_path),_free_port()
    assert main(["new","s1","-r",root]) == 0
    thread,out = _start(lambda: main(["serve","-r",root,"-p",str(port),"--no-browser"]),port)
    capsys.readouterr()
    try:
        assert pprun_main(["-P","s1","-p",str(port),"--no-browser","-r","/nonexistent"]) == 0
        text = capsys.readouterr().out
        assert "already running" in text and f"Projects... {tmp_path}" in text
        assert f"URL........ http://localhost:{port}/pprun/?project=s1" in text
        assert ppdata_main(["-P","nope","-p",str(port),"--no-browser"]) == 1
        assert "project 'nope' not found" in capsys.readouterr().err
    finally:
        _exit(port)
        thread.join(5)
    assert out["code"] == 0

def test_tool_unknown_project(tmp_path,capsys):
    assert ppoutput_main(["-P","nope","-r",str(tmp_path),"-p",str(_free_port()),"--no-browser"]) == 1
    assert "ERROR [ppoutput]: project 'nope' not found" in capsys.readouterr().err

def test_serve_rejects_name(tmp_path,capsys):
    assert main(["serve","s1","-r",str(tmp_path)]) == 1
    assert "-P PROJECT" in capsys.readouterr().err
