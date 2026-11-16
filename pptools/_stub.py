"""@private Shared Flask blueprint for planned tools (ppdata, pprun, ppoutput)

Each planned tool mounts a blueprint at `/<tool>/` in the front server that
shows what the tool will do and the files already in its project folder.
The project is chosen with `?project=NAME`.
"""

from flask import Blueprint, current_app, render_template_string, request

from pptools.project import ProjectError

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ name }}{% if project %} · {{ project.name }}{% endif %}</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 16%22%3E%3Crect width=%2216%22 height=%2216%22 rx=%223%22 fill=%22%231f6f5c%22/%3E%3Ccircle cx=%225%22 cy=%2211%22 r=%222%22 fill=%22white%22/%3E%3Ccircle cx=%2211%22 cy=%225%22 r=%222%22 fill=%22white%22/%3E%3Cpath d=%22M5 11L11 5%22 stroke=%22white%22/%3E%3C/svg%3E">
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<header class="topbar">
  <a class="brand" href="/{% if project %}#{{ project.name }}{% endif %}" title="Back to pptools"><span class="mark">pp</span>tools</a>
  <span class="crumb">/</span>
  <span class="brand"><span class="mark">pp</span>{{ name[2:] }}</span>
  {% if project %}<span class="crumb">{{ project.name }}</span>{% endif %}
</header>
<main class="stub">
  <section class="card">
    <h1>{{ title }} <span class="badge planned">planned</span></h1>
    <p>{{ summary }}</p>
    <p class="muted">This tool is a placeholder. The design is recorded in
      <code>DESIGN.md</code> and in the <code>pptools.{{ name }}</code> module documentation.</p>
    <h2>Planned features</h2>
    <ul>{% for item in planned %}<li>{{ item }}</li>{% endfor %}</ul>
  </section>
  <section class="card">
    <h2>Project folder <code>{{ folder }}/</code></h2>
    {% if error %}<p class="err">{{ error }}</p>
    {% elif not project %}<p class="muted">No project selected. Open a project from the
      <a href="/">pptools</a> page and choose {{ name }} there.</p>
    {% elif files %}
    <table class="files"><thead><tr><th>File</th><th>Size</th><th>Modified (UTC)</th></tr></thead><tbody>
    {% for f in files %}<tr><td>{{ f.name }}</td><td class="num">{{ f.size }}</td><td>{{ f.modified.replace('T',' ').rstrip('Z') }}</td></tr>{% endfor %}
    </tbody></table>
    {% else %}<p class="muted">No files yet.</p>{% endif %}
  </section>
</main>
</body>
</html>
"""

def stub_blueprint(name:str,folder:str,title:str,summary:str,planned:list[str]) -> Blueprint:
    """Return the placeholder blueprint for planned tool `name`

    Arguments
    ---------

      - `name`: tool name (`ppdata`, `pprun`, `ppoutput`); mounted at `/<name>/`
      - `folder`: project subfolder the tool works on
      - `title`, `summary`: shown on the page
      - `planned`: planned features, one line each
    """
    bp = Blueprint(name,__name__)

    @bp.get("/")
    def index():
        project,files,error = None,[],None
        if request.args.get("project"):
            try:
                project = current_app.config["WORKSPACE"].get(request.args["project"])
                files = project.files(folder)
            except ProjectError as err:
                error = str(err)
        return render_template_string(_PAGE,name=name,folder=folder,title=title,
            summary=summary,planned=planned,project=project,files=files,error=error)

    @bp.get("/api/status")
    def status():
        return {"tool":name,"status":"planned","folder":folder}

    return bp
