"""Power system modeling and simulation tools

Syntax
------

    pptools [-h] [-r ROOT] [--description TEXT] [-p PORT] [--host HOST]
            [--no-browser] [-d] [-v] [-w] [--version] {serve,new,list} [NAME]

    ppmodel [-h] ... {serve,convert,check} [FILES ...]

Positional arguments
--------------------

  - `serve`: start the front server and open the front page in a browser

  - `new NAME`: create project `NAME` in the projects folder and print its path

  - `list`: list the projects in the projects folder

Optional arguments
------------------

  - `-r|--root ROOT`: projects folder (default `~/pptools`, or the
    `PPTOOLS_ROOT` environment variable)

  - `--description TEXT`: project description (`new`)

  - `-p|--port PORT`: front server port (default 8040)

  - `--host HOST`: interface to listen on (default `127.0.0.1`); any other
    value allows remote access, which has no authentication

  - `--no-browser`: do not open a browser

  - `-d|--debug`: enable debug logging and traceback on exceptions

  - `-v|--verbose`: enable INFO messages (progress and server requests)

  - `-w|--warning`: enable warning messages from python

  - `--version`: show the package version and exit

`ppmodel` runs the model editor on its own; see `pptools.ppmodel`.

Description
-----------

`pptools` is a suite of local browser tools to edit, provision, and run
time-series simulations of power systems with
[`pypower_sim`](https://www.eudoxys.com/pypower_sim):

| Tool | Status | Purpose | Project folder |
|---|---|---|---|
| `pptools.ppmodel` | available | create and edit network models; check, PF and OPF | `models/` |
| `pptools.ppdata` | planned | construct time-series data panels for model objects | `data/` |
| `pptools.ppsim` | planned | set up and run time-series simulations | `sims/` |
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

```mermaid
flowchart LR
    front[pptools front page] --> projects[(projects folder)]
    front --> ppmodel[ppmodel\\none server per model]
    front --> ppdata[ppdata]
    front --> ppsim[ppsim]
    front --> ppoutput[ppoutput]
    ppmodel <--> models[/models/]
    ppdata --> data[/data/]
    models --> ppdata
    models --> ppsim
    data --> ppsim
    ppsim <--> pypower_sim[[pypower_sim]]
    ppsim --> outputs[/outputs/]
    outputs --> ppoutput
```

What is not promised
--------------------

  - `ppdata`, `ppsim`, and `ppoutput` are placeholders: their pages list
    the planned features and the files in their project folder, nothing
    more.

  - One user on the local machine: there is no authentication, locking,
    or multi-user support; two browser tabs editing the same project see
    each other's changes only on refresh.

  - Deleting files and projects is permanent (no trash folder).

  - Projects store files only; there is no record yet of which data panels
    and simulations use which models (planned with ppdata and ppsim).

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
