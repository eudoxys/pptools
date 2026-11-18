"""Front server

`create_app` returns the Flask application behind `pptools serve`: the
front page (`pptools/static/`), a JSON API over the projects in one
`pptools.project.Workspace`, the ppedit launcher, the simulation runner
at `/pprun/` (`pptools.pprun.server`, its own API), and the planned tools'
pages mounted at `/ppdata/` and `/ppoutput/`.

API
---

All `POST` requests must carry the header `X-PPTools: 1` and a JSON body
(except `upload`, which is `multipart/form-data`); errors return
`{"error": message}` with status 400 (or 403/404).

  - `GET /api/meta`: `version`, `root`, `tools` (`pptools.tools.TOOLS`),
    `folders` (`pptools.project.FOLDERS`), `model_formats`, `builtin` (PYPOWER
    built-in case names)
  - `GET /api/projects`: `{"projects": [record, ...]}`
  - `POST /api/projects/new`: `{"name", "description"?}` -> project
  - `GET /api/projects/<name>`: project (`Project.to_dict`)
  - `POST /api/projects/<name>/update`: `{"description"}` -> project
  - `POST /api/projects/<name>/delete`: `{"confirm": name}` -> `{"deleted": name}`
  - `POST /api/projects/<name>/upload`: form fields `folder`, `overwrite`?,
    files `file` (one or more) -> project
  - `POST /api/projects/<name>/rename`: `{"folder", "file", "new"}` -> project
  - `POST /api/projects/<name>/remove`: `{"folder", "file"}` -> project
  - `GET /api/projects/<name>/file/<folder>/<file>`: the file (download)
  - `POST /api/projects/<name>/models/new`: `{"file", "template"?}` (template
    `""` for an empty case or a built-in case name) -> project
  - `POST /api/ppedit/open`: `{"project", "file"}` -> `{"url", "port"}`
  - `GET /api/ppedit`: `{"running": [{"project", "file", "url", "port"}, ...]}`
  - `POST /api/ppedit/stop`: `{"project", "file"}` -> `{"stopped": bool}`
  - `POST /api/exit`: stop the ppedit servers and the front server

Security
--------

As in ppedit (ppedit decision #29): requests whose `Host` is not a
loopback name are refused unless `allow_remote=True`, and `POST` requests
need the `X-PPTools` header, which a cross-origin page cannot send without
a CORS preflight (never granted). There is no authentication. File names
are confined to the standard project folders (`Project.resolve`).
"""

import os
import signal
import atexit
import logging
import threading

from flask import Flask, jsonify, request, send_from_directory, abort

from pptools.project import Workspace, ProjectError, FOLDERS
from pptools.tools import TOOLS, ModelServers

_logger = logging.getLogger(__file__)

STATIC = os.path.join(os.path.dirname(__file__),"static")
"""Folder of the front page files"""

MODEL_FORMATS = ["py","json","glm","raw"]
"""Model file extensions opened with ppedit (`raw` is input only)"""

MAX_UPLOAD = 512 * 1024 * 1024
"""Largest accepted upload request, in bytes"""

_LOOPBACK = {"localhost","127.0.0.1","[::1]","::1"}

def _shutdown():
    if signal.getsignal(signal.SIGINT) is signal.SIG_IGN:
        os._exit(0) # pylint: disable=protected-access
    os.kill(os.getpid(),signal.SIGINT)

def create_app(root:str,allow_remote:bool=False,shutdown=None,models:ModelServers|None=None) -> Flask:
    """Create the front application

    Arguments
    ---------

      - `root`: projects folder (created if missing)

      - `allow_remote`: accept requests whose `Host` is not a loopback name

      - `shutdown`: function called by `POST /api/exit` after the ppedit
        servers are stopped (default: raise `SIGINT` in the server process)

      - `models`: ppedit server manager (default: a new `ModelServers`)

    Returns
    -------

      - `Flask`: the application; `app.config["WORKSPACE"]` is the
        `Workspace`, `app.config["MODELS"]` the `ModelServers`, and
        `app.config["RUNS"]` the pprun `pptools.pprun.runner.Runs`
    """
    # pylint: disable=too-many-locals,too-many-statements
    app = Flask(__name__,static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD
    app.json.sort_keys = False # keep FOLDERS and TOOLS in workflow order
    workspace = Workspace(root)
    models = models or ModelServers()
    atexit.register(models.stop_all)
    app.config["WORKSPACE"] = workspace
    app.config["MODELS"] = models
    app.config["SHUTDOWN"] = shutdown or _shutdown

    from pptools.ppdata import blueprint as ppdata # pylint: disable=import-outside-toplevel
    from pptools.pprun import blueprint as pprun # pylint: disable=import-outside-toplevel
    from pptools.ppoutput import blueprint as ppoutput # pylint: disable=import-outside-toplevel
    for bp in (ppdata,pprun,ppoutput):
        app.register_blueprint(bp,url_prefix=f"/{bp.name}")

    @app.before_request
    def _guard():
        host = (request.host or "").rsplit(":",1)[0] if not (request.host or "").startswith("[") \
            else request.host.split("]")[0]+"]"
        if not allow_remote and host not in _LOOPBACK:
            return jsonify(error="remote access is disabled"),403
        if request.method == "POST":
            if request.headers.get("X-PPTools") != "1":
                return jsonify(error="missing X-PPTools header"),403
            if not request.is_json and not request.path.endswith("/upload"):
                return jsonify(error="request body must be JSON"),403
        return None

    @app.errorhandler(ProjectError)
    def _project_error(err):
        return jsonify(error=str(err)),400

    @app.errorhandler(KeyError)
    def _key_error(err):
        return jsonify(error=f"missing field {err}"),400

    def body() -> dict:
        return request.get_json(silent=True) or {}

    def model_url(port:int) -> str:
        host = request.host.rsplit(":",1)[0] if not request.host.startswith("[") \
            else request.host.split("]")[0]+"]"
        return f"http://{host}:{port}/"

    def locate(path:str) -> tuple[str,str]|None:
        """(project, file) of a model path in the workspace, or None"""
        rel = os.path.relpath(path,workspace.root).split(os.sep)
        if len(rel) == 3 and rel[1] == "models":
            return rel[0],rel[2]
        return None

    @app.get("/")
    def index():
        return send_from_directory(STATIC,"index.html")

    @app.get("/static/<path:name>")
    def static_file(name):
        return send_from_directory(STATIC,name)

    @app.get("/api/meta")
    def meta():
        from pptools import __version__ # pylint: disable=import-outside-toplevel
        from ppedit.case import builtin_cases # pylint: disable=import-outside-toplevel
        return jsonify(version=__version__,root=workspace.root,tools=TOOLS,
            folders=FOLDERS,model_formats=MODEL_FORMATS,builtin=builtin_cases())

    @app.get("/api/projects")
    def projects():
        result = []
        for project in workspace.projects():
            try:
                result.append({**project.record,"name":project.name})
            except ProjectError as err:
                result.append({"name":project.name,"error":str(err)})
        return jsonify(projects=result)

    @app.post("/api/projects/new")
    def new_project():
        data = body()
        project = workspace.create(data["name"],str(data.get("description","")))
        return jsonify(project.to_dict())

    @app.get("/api/projects/<name>")
    def get_project(name):
        return jsonify(workspace.get(name).to_dict())

    @app.post("/api/projects/<name>/update")
    def update_project(name):
        project = workspace.get(name)
        project.update(description=str(body().get("description","")))
        return jsonify(project.to_dict())

    @app.post("/api/projects/<name>/delete")
    def delete_project(name):
        if body().get("confirm") != name:
            raise ProjectError("deleting a project needs {\"confirm\": NAME}")
        for item in models.running():
            if (locate(item["path"]) or ("",))[0] == name:
                models.stop(item["path"])
        workspace.delete(name)
        return jsonify(deleted=name)

    @app.post("/api/projects/<name>/upload")
    def upload(name):
        project = workspace.get(name)
        folder = request.form.get("folder","")
        overwrite = request.form.get("overwrite") in ("1","true","yes")
        files = request.files.getlist("file")
        if not files:
            raise ProjectError("no files uploaded")
        for item in files:
            project.write(folder,os.path.basename(item.filename or ""),item.read(),overwrite=overwrite)
        return jsonify(project.to_dict())

    @app.post("/api/projects/<name>/rename")
    def rename(name):
        data = body()
        project = workspace.get(name)
        if data["folder"] == "models":
            models.stop(project.resolve("models",data["file"]))
        project.rename(data["folder"],data["file"],data["new"])
        return jsonify(project.to_dict())

    @app.post("/api/projects/<name>/remove")
    def remove(name):
        data = body()
        project = workspace.get(name)
        if data["folder"] == "models":
            models.stop(project.resolve("models",data["file"]))
        project.delete(data["folder"],data["file"])
        return jsonify(project.to_dict())

    @app.get("/api/projects/<name>/file/<folder>/<file>")
    def download(name,folder,file):
        path = workspace.get(name).resolve(folder,file)
        if not os.path.isfile(path):
            abort(404)
        return send_from_directory(os.path.dirname(path),os.path.basename(path),
            as_attachment=request.args.get("download") == "1")

    @app.post("/api/projects/<name>/models/new")
    def new_model(name):
        from ppedit.case import Case, CaseError # pylint: disable=import-outside-toplevel
        data = body()
        project = workspace.get(name)
        path = project.resolve("models",data["file"])
        ext = os.path.splitext(path)[1][1:].lower()
        if ext not in ("py","json","glm"):
            raise ProjectError("a new model file must end in .py, .json or .glm")
        if os.path.exists(path):
            raise ProjectError(f"'models/{data['file']}' already exists")
        try:
            template = data.get("template") or ""
            case = Case.builtin(template) if template \
                else Case(name=os.path.splitext(os.path.basename(path))[0])
            case.save(path)
        except CaseError as err:
            raise ProjectError(str(err)) from err
        project.update()
        return jsonify(project.to_dict())

    @app.post("/api/ppedit/open")
    def ppedit_open():
        data = body()
        path = workspace.get(data["project"]).resolve("models",data["file"])
        if os.path.splitext(path)[1][1:].lower() not in MODEL_FORMATS:
            raise ProjectError(f"ppedit opens {', '.join('.'+x for x in MODEL_FORMATS)} files")
        if not os.path.isfile(path):
            raise ProjectError(f"'models/{data['file']}' not found")
        try:
            port = models.open(path)
        except RuntimeError as err:
            raise ProjectError(f"ppedit failed to start: {err}") from err
        return jsonify(url=model_url(port),port=port)

    @app.get("/api/ppedit")
    def ppedit_running():
        result = []
        for item in models.running():
            where = locate(item["path"])
            if where:
                result.append({"project":where[0],"file":where[1],
                    "url":model_url(item["port"]),"port":item["port"]})
        return jsonify(running=result)

    @app.post("/api/ppedit/stop")
    def ppedit_stop():
        data = body()
        path = workspace.get(data["project"]).resolve("models",data["file"])
        return jsonify(stopped=models.stop(path))

    @app.post("/api/exit")
    def exit_server():
        models.stop_all()
        threading.Timer(0.2,app.config["SHUTDOWN"]).start()
        return jsonify(exit=True)

    return app
