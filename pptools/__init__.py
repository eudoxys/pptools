"""Power system modeling and simulation tools

Syntax
------

    pptools [-h] [-P PROJECT] [-r ROOT] [--description TEXT] [-p PORT] [--host HOST]
            [--no-browser] [-d] [-v] [-w] [--version] {serve,new,list} [NAME]

    ppdata [serve] [-P PROJECT] [-r ROOT] [-p PORT] [--host HOST] [--no-browser] [-d] [-v] [-w] [--version]
    pprun [serve] ...    (same options as ppdata)
    ppoutput [serve] ... (same options as ppdata)

    ppmodel [-h] ... {serve,convert,check} [FILES ...]

Positional arguments
--------------------

  - `serve`: start the pptools server and open the page in a browser; if a
    pptools server is already running on the port, open the page there
    instead (default and only command of `ppdata`, `pprun`, `ppoutput`)

  - `new NAME`: create project `NAME` in the projects folder and print its path

  - `list`: list the projects in the projects folder

Optional arguments
------------------

  - `-P|--project PROJECT`: project to open (must exist)

  - `-r|--root ROOT`: projects folder (default `~/pptools`, or the
    `PPTOOLS_ROOT` environment variable); ignored when a running server is
    reused

  - `--description TEXT`: project description (`new`)

  - `-p|--port PORT`: server port (default 8040)

  - `--host HOST`: interface to listen on (default `127.0.0.1`); any other
    value allows remote access, which has no authentication

  - `--no-browser`: do not open a browser

  - `-d|--debug`: enable debug logging and traceback on exceptions

  - `-v|--verbose`: enable INFO messages (progress and server requests)

  - `-w|--warning`: enable warning messages from python

  - `--version`: show the package version and exit

`pptools` opens the front page, and `ppdata`, `pprun`, and `ppoutput` open
their tool's page, all on the same server. `ppmodel` runs the model editor
on its own; see `pptools.ppmodel`.

Description
-----------

`pptools` is a suite of local browser tools to edit, provision, and run
time-series simulations of power systems with
[`pypower_sim`](https://www.eudoxys.com/pypower_sim):

| Tool | Status | Purpose | Project folder |
|---|---|---|---|
| `pptools.ppmodel` | available | create and edit network models; check, PF and OPF | `models/` |
| `pptools.ppdata` | planned | construct time-series data panels for model objects | `data/` |
| `pptools.pprun` | planned | set up and run time-series simulations | `sims/` |
| `pptools.ppoutput` | planned | manage and view simulation outputs | `outputs/` |

The front page (`pptools serve`) is the single entry point. It manages
*projects*: folders under the projects folder that collect the models,
data panels, simulation setups, and outputs of one study (see
`pptools.project`). From a project the front page creates, uploads,
downloads, renames, and deletes files, and opens each tool on the
project's files.

Given a projects folder, `pptools serve` is expected to satisfy:

  1. Every folder holding a `pptools.json` record is listed as a project;
     other folders are ignored and never changed.

  2. Files are read and written only inside the standard project
     subfolders (`models`, `data`, `sims`, `outputs`); names that would
     leave them are refused.

  3. Opening a model starts one `ppmodel` server for that file (or reuses
     the one already running) on a free loopback port and opens it in a
     new browser tab; edits are saved by ppmodel to the model file.

  4. Stopping the front server stops every ppmodel server it started.

  5. `ppdata`, `pprun`, and `ppoutput` start the server only if no pptools
     server answers on the port; otherwise they open their page on the
     running server, whatever its projects folder.

```mermaid
flowchart LR
    front[pptools front page] --> projects[(projects folder)]
    front --> ppmodel[ppmodel\\none server per model]
    front --> ppdata[ppdata]
    front --> pprun[pprun]
    front --> ppoutput[ppoutput]
    ppmodel <--> models[/models/]
    ppdata --> data[/data/]
    models --> ppdata
    models --> pprun
    data --> pprun
    pprun <--> pypower_sim[[pypower_sim]]
    pprun --> outputs[/outputs/]
    outputs --> ppoutput
```

What is not promised
--------------------

  - `ppdata`, `pprun`, and `ppoutput` are placeholders: their pages list
    the planned features and the files in their project folder, nothing
    more.

  - One user on the local machine: there is no authentication, locking,
    or multi-user support; two browser tabs editing the same project see
    each other's changes only on refresh.

  - Deleting files and projects is permanent (no trash folder).

  - Projects store files only; there is no record yet of which data panels
    and simulations use which models (planned with ppdata and pprun).

Installation
------------

Install using Eudoxys Package Manager:

    pip install --upgrade eudoxys
    epm install pptools

Install using `pip`:

    pip install git+https://github.com/eudoxys/pptools
"""

try:
    import importlib.metadata
    __version__ = importlib.metadata.version("pptools")
except Exception: # pylint: disable=broad-exception-caught
    __version__ = "dev"

from pptools.project import Workspace, Project, ProjectError, FOLDERS
from pptools.tools import TOOLS
from pptools.server import create_app
from pptools.cli import main
