"""Project folders

A project is a folder that collects everything for one study: network
models, time-series data panels, simulation setups, and simulation outputs.
`Workspace` manages the projects under one root folder; `Project` manages
the files of one project.

Layout of a project folder `ROOT/NAME/`:

    pptools.json    project record (see `Project.record`)
    models/         network models (ppmodel: .py, .json, .glm; .raw input only)
    data/           time-series data panels (ppdata)
    sims/           simulation setups (ppsim)
    outputs/        simulation outputs (ppoutput)

Examples
--------

    >>> import tempfile
    >>> from pptools import Workspace
    >>> ws = Workspace(tempfile.mkdtemp())
    >>> project = ws.create("wecc240",description="WECC 240-bus summer study")
    >>> sorted(project.folders())
    ['data', 'models', 'outputs', 'sims']
    >>> _ = project.write("models","notes.txt",b"hello")
    >>> [f["name"] for f in project.files("models")]
    ['notes.txt']
    >>> [p.name for p in ws.projects()]
    ['wecc240']

Caveats
-------

  - Paths given to `Project` methods are relative to a project folder and
    must stay inside it: absolute paths, `..` segments, and hidden names
    (starting with `.`) raise `ProjectError`.

  - Deleting a file is permanent; `Project.delete` does not use a trash
    folder.
"""

import os
import re
import json
import shutil
import logging
import datetime

_logger = logging.getLogger(__file__)

RECORD = "pptools.json"
"""Name of the project record file in each project folder"""

FOLDERS = {
    "models": "Network models edited with ppmodel (.py, .json, .glm; PSS/E .raw input only)",
    "data": "Time-series data panels built with ppdata",
    "sims": "Simulation setups run with ppsim",
    "outputs": "Simulation outputs managed with ppoutput",
    }
"""Standard project subfolders and what each holds"""

NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
"""Allowed project and file names: letters, digits, `_`, `.`, `-`; no leading `.`"""

class ProjectError(Exception):
    """Invalid project name, path, or operation"""

def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _version() -> str:
    from pptools import __version__ # pylint: disable=import-outside-toplevel
    return __version__

def check_name(name:str,what:str="name") -> str:
    """Return `name` if it is a valid project or file name, else raise `ProjectError`"""
    if not isinstance(name,str) or not NAME_PATTERN.match(name):
        raise ProjectError(f"invalid {what} '{name}': use letters, digits, '_', '.', '-' "
            "(at most 64 characters, not starting with '.')")
    return name

class Project:
    """One project folder"""

    def __init__(self,path:str):
        """Open the project in folder `path`

        Arguments
        ---------

          - `path`: project folder; it must hold a `pptools.json` record

        Exceptions
        ----------

          - `ProjectError`: `path` is not a project folder
        """
        self.path = os.path.abspath(path)
        """Absolute path of the project folder"""
        self.name = os.path.basename(self.path)
        """Project name (the folder name)"""
        if not os.path.isfile(os.path.join(self.path,RECORD)):
            raise ProjectError(f"'{path}' is not a pptools project (no {RECORD})")

    @property
    def record(self) -> dict:
        """Project record from `pptools.json`: `application`, `version`,
        `name`, `description`, `created`, `modified` (UTC ISO 8601)"""
        try:
            with open(os.path.join(self.path,RECORD),encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError,ValueError) as err:
            raise ProjectError(f"cannot read {RECORD} in '{self.path}': {err}") from err
        return data if isinstance(data,dict) else {}

    def update(self,**fields) -> dict:
        """Change record fields (e.g. `description`) and set `modified`; returns the record"""
        data = self.record
        for key,value in fields.items():
            if key in ("application","created","name"):
                raise ProjectError(f"record field '{key}' cannot be changed")
            data[key] = value
        data["modified"] = _now()
        self._write_record(data)
        return data

    def _write_record(self,data:dict):
        with open(os.path.join(self.path,RECORD),"w",encoding="utf-8") as fh:
            json.dump(data,fh,indent=2)
            fh.write("\n")

    def folders(self) -> list[str]:
        """Names of the standard subfolders, creating any that are missing"""
        for folder in FOLDERS:
            os.makedirs(os.path.join(self.path,folder),exist_ok=True)
        return list(FOLDERS)

    def resolve(self,folder:str,name:str|None=None) -> str:
        """Absolute path of `folder` (a standard subfolder), or of file `name` in it

        Exceptions
        ----------

          - `ProjectError`: unknown folder or invalid file name
        """
        if folder not in FOLDERS:
            raise ProjectError(f"unknown project folder '{folder}' (use one of {', '.join(FOLDERS)})")
        base = os.path.join(self.path,folder)
        if name is None:
            return base
        path = os.path.abspath(os.path.join(base,check_name(name,"file name")))
        if os.path.dirname(path) != base:
            raise ProjectError(f"'{name}' is outside the project folder")
        return path

    def files(self,folder:str) -> list[dict]:
        """Files in `folder`, sorted by name: `name`, `size` (bytes),
        `modified` (UTC ISO 8601), `ext` (lower-case extension without the dot)"""
        base = self.resolve(folder)
        if not os.path.isdir(base):
            return []
        result = []
        for name in sorted(os.listdir(base),key=str.lower):
            path = os.path.join(base,name)
            if name.startswith(".") or not os.path.isfile(path):
                continue
            stat = os.stat(path)
            result.append({
                "name": name,
                "size": stat.st_size,
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime,datetime.timezone.utc)
                    .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ext": os.path.splitext(name)[1][1:].lower(),
                })
        return result

    def write(self,folder:str,name:str,data:bytes,overwrite:bool=False) -> str:
        """Write file `name` in `folder`; returns its path

        Exceptions
        ----------

          - `ProjectError`: the file exists and `overwrite` is false
        """
        path = self.resolve(folder,name)
        if os.path.exists(path) and not overwrite:
            raise ProjectError(f"'{folder}/{name}' already exists")
        os.makedirs(os.path.dirname(path),exist_ok=True)
        with open(path,"wb") as fh:
            fh.write(data)
        self.update()
        return path

    def rename(self,folder:str,name:str,new:str) -> str:
        """Rename file `name` in `folder` to `new`; returns the new path"""
        src,dst = self.resolve(folder,name),self.resolve(folder,new)
        if not os.path.isfile(src):
            raise ProjectError(f"'{folder}/{name}' not found")
        if os.path.exists(dst):
            raise ProjectError(f"'{folder}/{new}' already exists")
        os.rename(src,dst)
        self.update()
        return dst

    def delete(self,folder:str,name:str):
        """Delete file `name` in `folder` (permanent)"""
        path = self.resolve(folder,name)
        if not os.path.isfile(path):
            raise ProjectError(f"'{folder}/{name}' not found")
        os.remove(path)
        self.update()

    def to_dict(self) -> dict:
        """Project summary for the API: `name`, `path`, the record fields,
        and `folders` (name -> list of `files()`)"""
        return {
            **self.record,
            "name": self.name,
            "path": self.path,
            "folders": {folder:self.files(folder) for folder in self.folders()},
            }

class Workspace:
    """The projects under one root folder"""

    def __init__(self,root:str):
        """Use `root` as the projects folder, creating it if needed

        Arguments
        ---------

          - `root`: folder holding one subfolder per project
        """
        self.root = os.path.abspath(os.path.expanduser(root))
        """Absolute path of the projects folder"""
        os.makedirs(self.root,exist_ok=True)

    def projects(self) -> list[Project]:
        """Projects in the root folder, sorted by name (folders without
        `pptools.json` are ignored)"""
        result = []
        for name in sorted(os.listdir(self.root),key=str.lower):
            if not name.startswith(".") and os.path.isfile(os.path.join(self.root,name,RECORD)):
                result.append(Project(os.path.join(self.root,name)))
        return result

    def get(self,name:str) -> Project:
        """Open project `name`

        Exceptions
        ----------

          - `ProjectError`: invalid name or no such project
        """
        path = os.path.join(self.root,check_name(name,"project name"))
        if not os.path.isfile(os.path.join(path,RECORD)):
            raise ProjectError(f"project '{name}' not found")
        return Project(path)

    def create(self,name:str,description:str="") -> Project:
        """Create project `name` with the standard subfolders

        Exceptions
        ----------

          - `ProjectError`: invalid name or the folder already exists
        """
        path = os.path.join(self.root,check_name(name,"project name"))
        if os.path.exists(path):
            raise ProjectError(f"'{name}' already exists in {self.root}")
        os.makedirs(path)
        now = _now()
        project_record = {"application":"pptools","version":_version(),
            "name":name,"description":description,"created":now,"modified":now}
        with open(os.path.join(path,RECORD),"w",encoding="utf-8") as fh:
            json.dump(project_record,fh,indent=2)
            fh.write("\n")
        project = Project(path)
        project.folders()
        _logger.info("created project %s",path)
        return project

    def delete(self,name:str):
        """Delete project `name` and everything in it (permanent)"""
        project = self.get(name)
        shutil.rmtree(project.path)
        _logger.info("deleted project %s",project.path)
