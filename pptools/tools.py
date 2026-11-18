"""Tool registry and the ppedit launcher

`TOOLS` lists the browser tools the front page offers, in workflow order.
`ppedit` holds one case per server process (ppedit decision #1), so the
front server starts one `ppedit serve` process per open model file on a
free loopback port (`ModelServers`). The other tools are Flask blueprints
mounted in the front server at `/<tool>/`.

Examples
--------

    >>> from pptools.tools import TOOLS
    >>> [(t["name"],t["status"]) for t in TOOLS]
    [('ppedit', 'available'), ('ppdata', 'planned'), ('pprun', 'available'), ('ppoutput', 'planned')]
"""

import os
import sys
import time
import socket
import logging
import threading
import subprocess

_logger = logging.getLogger(__file__)

TOOLS = [
    {"name":"ppedit","folder":"models","status":"available","kind":"process",
     "title":"Model editor",
     "summary":"Create and edit network models (PYPOWER .py/.json, GridLAB-D module pypower .glm, "
        "PSS/E .raw input), check them, and solve power flow and OPF."},
    {"name":"ppdata","folder":"data","status":"planned","kind":"blueprint",
     "title":"Time-series data panels",
     "summary":"Construct time-series panels of data (loads, generation, ratings, prices) "
        "for objects in a model, as pypower_sim inputs."},
    {"name":"pprun","folder":"sims","status":"available","kind":"blueprint",
     "title":"Simulation runner",
     "summary":"Set up and run quasi-steady time-series simulations of a model and data panels "
        "with pypower_sim."},
    {"name":"ppoutput","folder":"outputs","status":"planned","kind":"blueprint",
     "title":"Output manager",
     "summary":"Manage, view, and compare the outputs of simulation runs."},
    ]
"""Browser tools in workflow order: `name`, project `folder` it works on,
`status` (`available` or `planned`), `kind` (`process`: separate server per
file; `blueprint`: mounted at `/<name>/`), `title`, `summary`"""

def free_port(host:str="127.0.0.1") -> int:
    """Return a TCP port that is free on `host` now"""
    with socket.socket() as sock:
        sock.bind((host,0))
        return sock.getsockname()[1]

class ModelServers:
    """`ppedit serve` processes, one per open model file"""

    STARTUP_TIMEOUT = 30.0
    """Seconds to wait for a new ppedit server to accept connections"""

    def __init__(self,host:str="127.0.0.1"):
        """Track ppedit servers listening on `host`"""
        self.host = host
        """Interface the ppedit servers listen on"""
        self._lock = threading.Lock()
        self._procs = {} # path -> (Popen,port)

    def _alive(self,path:str) -> bool:
        proc = self._procs.get(path)
        if proc and proc[0].poll() is None:
            return True
        self._procs.pop(path,None)
        return False

    def open(self,path:str) -> int:
        """Return the port of the ppedit server for model file `path`,
        starting one if none is running (a missing file opens as a new case
        that is saved to `path`)

        Exceptions
        ----------

          - `RuntimeError`: the server exited or did not start in time
        """
        path = os.path.abspath(path)
        with self._lock:
            if self._alive(path):
                return self._procs[path][1]
            port = free_port(self.host)
            cmd = [sys.executable,"-m","ppedit.cli","serve",path,
                "--no-browser","--host",self.host,"-p",str(port)]
            _logger.info("starting %s",' '.join(cmd))
            proc = subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE, # pylint: disable=consider-using-with
                text=True)
            deadline = time.monotonic() + self.STARTUP_TIMEOUT
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    err = proc.stderr.read().strip().splitlines()
                    raise RuntimeError(err[-1] if err else f"ppedit exited with code {proc.returncode}")
                try:
                    with socket.create_connection((self.host,port),timeout=0.5):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                proc.terminate()
                raise RuntimeError("ppedit did not start in time")
            self._procs[path] = (proc,port)
            return port

    def running(self) -> list[dict]:
        """Running servers: `path`, `port`, `pid`"""
        with self._lock:
            return [{"path":path,"port":port,"pid":proc.pid}
                for path,(proc,port) in list(self._procs.items()) if self._alive(path)]

    def stop(self,path:str) -> bool:
        """Stop the server for `path`; returns whether one was running"""
        path = os.path.abspath(path)
        with self._lock:
            if not self._alive(path):
                return False
            proc,_ = self._procs.pop(path)
        proc.terminate()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()
        return True

    def stop_all(self):
        """Stop every server (called when the front server exits)"""
        for item in self.running():
            self.stop(item["path"])
