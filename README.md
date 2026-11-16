[![Validation](https://github.com/eudoxys/pptools/actions/workflows/validate.yaml/badge.svg)](https://github.com/eudoxys/pptools/actions/workflows/validate.yaml)
[![Documentation](https://github.com/eudoxys/pptools/actions/workflows/deploy-pages.yaml/badge.svg)](https://github.com/eudoxys/pptools/actions/workflows/deploy-pages.yaml)

Browser-based tools to edit, provision, and run time-series simulations of
power systems with [`pypower_sim`](https://github.com/eudoxys/pypower_sim).

`pptools` is a suite of local web tools for transmission studies. One front
page manages *projects* (folders that collect a study's network models,
time-series data, simulation setups, and outputs) and opens each tool on a
project's files:

| Tool | Status | Purpose |
|---|---|---|
| `ppmodel` | available | create and edit PYPOWER and GridLAB-D `module pypower` models (PSS/E `.raw` input), check them, solve PF/OPF |
| `ppdata` | planned | construct time-series panels of data for objects in a model |
| `ppsim` | planned | set up and run time-series simulations with `pypower_sim` |
| `ppoutput` | planned | manage and view simulation outputs |

`ppmodel` was developed as [`dchassin/ppedit`](https://github.com/dchassin/ppedit).
The design and plan are in [DESIGN.md](DESIGN.md).

# Documentation

See https://www.eudoxys.com/pptools

# Installation

Install using Eudoxys Package Manager:

    pip install --upgrade eudoxys
    epm install pptools

Install using `pip`:

    pip install git+https://github.com/eudoxys/pptools

# Maintenance

## Update docs

    make docs

## Run tests

    pip install -e . pytest
    pytest

All tests are fast and need no network or credentials; see
[`pptools/_test/README.md`](pptools/_test/README.md) and
[`pptools/ppmodel/_test/README.md`](pptools/ppmodel/_test/README.md).

# Examples

## Command line

Start the front page (projects are kept in `~/pptools` unless `--root` or
`PPTOOLS_ROOT` says otherwise):

    pptools serve

which prints

    pptools: power system modeling and simulation tools in your browser

        Projects... /home/user/pptools
        URL........ http://localhost:8040/

        Ctrl-C to stop server

and opens the page in a browser. Projects can also be created and listed
from the command line:

    pptools new wecc240 --description "WECC 240-bus summer peak study"
    pptools list

The model editor also runs on its own:

    ppmodel serve case14.glm
    ppmodel convert wecc240.raw wecc240.glm
    ppmodel check case14.glm

## Python

    import tempfile
    from pptools import Workspace
    ws = Workspace(tempfile.mkdtemp())
    project = ws.create("wecc240")
    print(project.folders())

outputs

    ['models', 'data', 'sims', 'outputs']
