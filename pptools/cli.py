"""Command line interface

See `pptools` for the command syntax. `ppdata`, `pprun`, and `ppoutput`
use the same server through `tool_main` (see `pptools.ppdata.cli`,
`pptools.pprun.cli`, `pptools.ppoutput.cli`).

Examples
--------

    pptools serve
    pptools serve --root ~/studies -p 8040
    pptools serve -P wecc240
    pptools new wecc240 --description "WECC 240-bus summer study"
    pptools list
    pptools --version
    ppdata -P wecc240
    pprun -P wecc240
    ppoutput

`serve` (and `ppdata`, `pprun`, `ppoutput`) prints the page URL and opens it
in a browser; if a pptools server is already running on the port, it opens
the page there instead of starting another server. `new` creates a project
folder and prints its path; `list` prints one line per project (name and
description).
"""

import os
import sys
import json
import argparse
import logging
import threading
import warnings
import webbrowser
import urllib.parse
import urllib.request

_logger = logging.getLogger(__file__)

DEFAULT_ROOT = os.environ.get("PPTOOLS_ROOT","~/pptools")
"""Default projects folder (`PPTOOLS_ROOT` environment variable, else `~/pptools`)"""

DEFAULT_PORT = 8040
"""Default port of the pptools server (all tools share it)"""

TOOL_TITLES = {
    "ppdata": "time-series data panels",
    "pprun": "time-series simulation runner",
    "ppoutput": "simulation output manager",
    }
"""Tools with their own command (`tool_main`) and the title the command prints"""

def _version() -> str:
    from pptools import __version__ # pylint: disable=import-outside-toplevel
    return __version__

def _local_url(host:str,port:int) -> str:
    return f"http://{'localhost' if host in ('127.0.0.1','0.0.0.0') else host}:{port}/"

def running_server(host:str,port:int) -> dict|None:
    """Return `GET /api/meta` of a pptools server on `host`:`port`, or None if
    nothing answers there as pptools"""
    url = _local_url(host,port) + "api/meta"
    try:
        with urllib.request.urlopen(url,timeout=1) as res:
            meta = json.load(res)
    except (OSError,ValueError):
        return None
    return meta if isinstance(meta,dict) and "tools" in meta and "root" in meta else None

def _page(tool:str|None,project:str|None) -> str:
    """Page path for `tool` (None: the front page) and `project`"""
    quoted = urllib.parse.quote(project or "")
    if tool:
        return f"{tool}/" + (f"?project={quoted}" if project else "")
    return f"#{quoted}" if project else ""

def serve(root:str,host:str="127.0.0.1",port:int=DEFAULT_PORT,tool:str|None=None,
        project:str|None=None,browser:bool=True) -> int:
    """Open `tool`'s page (None: the front page) on the pptools server at
    `host`:`port`, starting the server if none is running there

    Arguments
    ---------

      - `root`: projects folder (used only when a server is started)
      - `host`, `port`: server interface and port
      - `tool`: `ppdata`, `pprun`, `ppoutput`, or None for the front page
      - `project`: project to open (must exist)
      - `browser`: open the page in a web browser

    Returns
    -------

      - `int`: exit code (0 on success)

    Exceptions
    ----------

      - `ValueError`, `ProjectError`: unknown `project`
      - `OSError`: the port is in use by something other than pptools
    """
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    base = _local_url(host,port)
    meta = running_server(host,port)
    if meta:
        if project:
            try:
                with urllib.request.urlopen(base+"api/projects/"+urllib.parse.quote(project),timeout=5):
                    pass
            except OSError as err:
                raise ValueError(f"project '{project}' not found in {meta['root']}") from err
        url = base + _page(tool,project)
        print(f"{tool or 'pptools'}: using the pptools server already running at {base}")
        print(f"    Projects... {meta['root']}")
        print(f"    URL........ {url}")
        if browser:
            webbrowser.open(url)
        return 0

    from pptools.project import Workspace # pylint: disable=import-outside-toplevel
    from pptools.server import create_app # pylint: disable=import-outside-toplevel
    from pptools.tools import ModelServers # pylint: disable=import-outside-toplevel
    from werkzeug.serving import make_server # pylint: disable=import-outside-toplevel
    if project:
        Workspace(root).get(project) # raises ProjectError if missing
    server = None
    local = host in ("127.0.0.1","localhost","::1")
    models = ModelServers("127.0.0.1" if local else host)
    app = create_app(root,allow_remote=not local,shutdown=lambda: server.shutdown(),models=models)
    server = make_server(host,port,app,threaded=True)
    url = base + _page(tool,project)
    name = tool or "pptools"
    print("")
    print(f"{name}: " + (TOOL_TITLES[tool] if tool else "power system modeling and simulation tools")
        + " in your browser")
    print("")
    print(f"    Projects... {app.config['WORKSPACE'].root}")
    print(f"    URL........ {url}")
    print("")
    print("    Ctrl-C to stop server")
    if browser:
        threading.Timer(1.0,lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        models.stop_all()
        server.server_close()
    print("")
    print(f"{name}: thanks for using {name}!")
    print("")
    return 0

def _common_options(parser:argparse.ArgumentParser,prog:str):
    """Add the options shared by `pptools` and the tool commands"""
    parser.add_argument("-P","--project",help="project to open")
    parser.add_argument("-r","--root",default=DEFAULT_ROOT,
        help=f"projects folder (default {DEFAULT_ROOT}; set PPTOOLS_ROOT to change)")
    parser.add_argument("-p","--port",type=int,default=DEFAULT_PORT,
        help=f"server port (default {DEFAULT_PORT}; a pptools server already running there is reused)")
    parser.add_argument("--host",default="127.0.0.1",help="interface to listen on (default 127.0.0.1)")
    parser.add_argument("--no-browser",action="store_true",help="do not open a browser")
    parser.add_argument("-d","--debug",action="store_true",help="enable debug logging and traceback on exceptions")
    parser.add_argument("-v","--verbose",action="store_true",help="enable INFO messages (progress and server requests)")
    parser.add_argument("-w","--warning",action="store_true",help="enable warning messages from python")
    parser.add_argument("--version",action="version",version=f"{prog} {_version()}",
        help=f"show the {prog} version and exit")

def _setup(args:argparse.Namespace):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG if args.debug
        else logging.INFO if args.verbose else logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.INFO if args.verbose else logging.WARNING)
    if not args.warning:
        warnings.simplefilter("ignore")

def main(argv:list[str]|None=None) -> int:
    """Command line entry point of `pptools`

    Arguments
    ---------

      - `argv`: command line arguments (default `sys.argv[1:]`)

    Returns
    -------

      - `int`: exit code (0 on success, 1 on error)
    """
    parser = argparse.ArgumentParser(prog="pptools",
        description="Power system modeling, data, simulation, and output tools in your browser",
        epilog="See https://www.eudoxys.com/pptools for full documentation.")
    parser.add_argument("command",choices=["serve","new","list"])
    parser.add_argument("name",nargs="?",help="project name (new)")
    parser.add_argument("--description",default="",help="project description (new)")
    _common_options(parser,"pptools")
    args = parser.parse_args(argv)
    _setup(args)
    try:
        from pptools.project import Workspace # pylint: disable=import-outside-toplevel
        if args.command == "new":
            if not args.name:
                raise ValueError("new needs a project NAME")
            project = Workspace(args.root).create(args.name,args.description)
            print(project.path)
            return 0
        if args.command == "list":
            for project in Workspace(args.root).projects():
                desc = project.record.get("description","")
                print(f"{project.name}" + (f"  {desc}" if desc else ""))
            return 0
        if args.name:
            raise ValueError("serve takes no NAME (use -P PROJECT to open a project)")
        return serve(args.root,args.host,args.port,None,args.project,not args.no_browser)
    except Exception as err: # pylint: disable=broad-exception-caught
        if args.debug:
            raise
        print(f"ERROR [pptools]: {err}",file=sys.stderr)
        return 1

def tool_main(tool:str,argv:list[str]|None=None) -> int:
    """Command line entry point of the `ppdata`, `pprun`, and `ppoutput` commands

    Arguments
    ---------

      - `tool`: `ppdata`, `pprun`, or `ppoutput`
      - `argv`: command line arguments (default `sys.argv[1:]`)

    Returns
    -------

      - `int`: exit code (0 on success, 1 on error)
    """
    assert tool in TOOL_TITLES,f"unknown tool '{tool}'"
    parser = argparse.ArgumentParser(prog=tool,
        description=f"pptools {TOOL_TITLES[tool]} in your browser (planned: the page lists "
            "the planned features and the project's files)",
        epilog=f"See https://www.eudoxys.com/pptools/pptools/{tool}.html for full documentation.")
    parser.add_argument("command",nargs="?",choices=["serve"],default="serve",
        help="start (or reuse) the pptools server and open the page (default)")
    _common_options(parser,tool)
    args = parser.parse_args(argv)
    _setup(args)
    try:
        return serve(args.root,args.host,args.port,tool,args.project,not args.no_browser)
    except Exception as err: # pylint: disable=broad-exception-caught
        if args.debug:
            raise
        print(f"ERROR [{tool}]: {err}",file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
