"""Command line interface

See `pptools` for the command syntax.

Examples
--------

    pptools serve
    pptools serve --root ~/studies -p 8040
    pptools new wecc240 --description "WECC 240-bus summer study"
    pptools list
    pptools --version

`serve` prints the front page URL and opens it in a browser; `new` creates
a project folder and prints its path; `list` prints one line per project
(name and description).
"""

import os
import sys
import argparse
import logging
import threading
import warnings
import webbrowser

_logger = logging.getLogger(__file__)

DEFAULT_ROOT = os.environ.get("PPTOOLS_ROOT","~/pptools")
"""Default projects folder (`PPTOOLS_ROOT` environment variable, else `~/pptools`)"""

def _version() -> str:
    from pptools import __version__ # pylint: disable=import-outside-toplevel
    return __version__

def main(argv:list[str]|None=None) -> int:
    """Command line entry point

    Arguments
    ---------

      - `argv`: command line arguments (default `sys.argv[1:]`)

    Returns
    -------

      - `int`: exit code (0 on success, 1 on error)
    """
    # pylint: disable=too-many-statements
    parser = argparse.ArgumentParser(prog="pptools",
        description="Power system modeling, data, simulation, and output tools in your browser",
        epilog="See https://www.eudoxys.com/pptools for full documentation.")
    parser.add_argument("command",choices=["serve","new","list"])
    parser.add_argument("name",nargs="?",help="project name (new)")
    parser.add_argument("-r","--root",default=DEFAULT_ROOT,
        help=f"projects folder (default {DEFAULT_ROOT}; set PPTOOLS_ROOT to change)")
    parser.add_argument("--description",default="",help="project description (new)")
    parser.add_argument("-p","--port",type=int,default=8040,help="server port (default 8040)")
    parser.add_argument("--host",default="127.0.0.1",help="interface to listen on (default 127.0.0.1)")
    parser.add_argument("--no-browser",action="store_true",help="do not open a browser")
    parser.add_argument("-d","--debug",action="store_true",help="enable debug logging and traceback on exceptions")
    parser.add_argument("-v","--verbose",action="store_true",help="enable INFO messages (progress and server requests)")
    parser.add_argument("-w","--warning",action="store_true",help="enable warning messages from python")
    parser.add_argument("--version",action="version",version=f"pptools {_version()}",
        help="show the pptools version and exit")
    args = parser.parse_args(argv)

    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG if args.debug
        else logging.INFO if args.verbose else logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.INFO if args.verbose else logging.WARNING)
    if not args.warning:
        warnings.simplefilter("ignore")

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
        # serve
        if args.name:
            raise ValueError("serve takes no NAME")
        from pptools.server import create_app # pylint: disable=import-outside-toplevel
        from pptools.tools import ModelServers # pylint: disable=import-outside-toplevel
        from werkzeug.serving import make_server # pylint: disable=import-outside-toplevel
        server = None
        local = args.host in ("127.0.0.1","localhost","::1")
        models = ModelServers("127.0.0.1" if local else args.host)
        app = create_app(args.root,allow_remote=not local,
            shutdown=lambda: server.shutdown(),models=models)
        server = make_server(args.host,args.port,app,threaded=True)
        url = f"http://{'localhost' if args.host in ('127.0.0.1','0.0.0.0') else args.host}:{args.port}/"
        print("")
        print("pptools: power system modeling and simulation tools in your browser")
        print("")
        print(f"    Projects... {app.config['WORKSPACE'].root}")
        print(f"    URL........ {url}")
        print("")
        print("    Ctrl-C to stop server")
        if not args.no_browser:
            threading.Timer(1.0,lambda: webbrowser.open(url)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            models.stop_all()
            server.server_close()
        print("")
        print("pptools: thanks for using pptools!")
        print("")
        return 0
    except Exception as err: # pylint: disable=broad-exception-caught
        if args.debug:
            raise
        print(f"ERROR [pptools]: {err}",file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
