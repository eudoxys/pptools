// pptools front page: projects, project folders, and tool launcher.
// Vanilla JS, no build step (decision #3). The server is the only model:
// every change reloads the project from the API.
"use strict";

const S = { meta: null, projects: [], project: null, folder: "models", running: [] };

// ---- helpers ---------------------------------------------------------------

function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

async function api(path, body, form) {
  const opts = body === undefined && !form ? {} : {
    method: "POST",
    headers: form ? { "X-PPTools": "1" } : { "X-PPTools": "1", "Content-Type": "application/json" },
    body: form || JSON.stringify(body || {}),
  };
  const res = await fetch(path, opts);
  let data = {};
  try { data = await res.json(); } catch (e) { /* not JSON */ }
  if (!res.ok) throw new Error(data.error || `${res.status} ${res.statusText}`);
  return data;
}

let toastTimer = null;
function toast(msg, error) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast" + (error ? " error" : "");
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, error ? 6000 : 2500);
}

async function guarded(fn) {
  try { return await fn(); } catch (err) { toast(err.message, true); return null; }
}

function size(n) {
  if (n < 1024) return `${n} B`;
  const units = ["kB", "MB", "GB"];
  let u = -1;
  do { n /= 1024; u++; } while (n >= 1024 && u < units.length - 1);
  return `${n.toFixed(n < 10 ? 1 : 0)} ${units[u]}`;
}

function when(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

const ext = (name) => (name.includes(".") ? name.split(".").pop().toLowerCase() : "");

// ---- dialog ----------------------------------------------------------------

// Show a modal form; `fields` build the inputs, `submit(values)` may throw to
// keep the dialog open with the error shown.
function dialog(title, fields, okLabel, submit, danger) {
  const dlg = document.getElementById("dialog");
  const form = document.getElementById("dialog-form");
  const err = h("div", { class: "err" });
  form.replaceChildren(
    h("h2", {}, title), ...fields, err,
    h("div", { class: "buttons" },
      h("button", { type: "button", onclick: () => dlg.close() }, "Cancel"),
      h("button", { type: "submit", class: danger ? "primary danger-fill" : "primary" }, okLabel)));
  form.onsubmit = async (ev) => {
    ev.preventDefault();
    const values = Object.fromEntries(new FormData(form).entries());
    try { await submit(values); dlg.close(); } catch (e) { err.textContent = e.message; }
  };
  dlg.showModal();
  const first = form.querySelector("input,select,textarea");
  if (first) first.focus();
}

// ---- data ------------------------------------------------------------------

async function loadProjects() {
  S.projects = (await api("/api/projects")).projects;
  renderSidebar();
}

async function loadProject(name) {
  if (!name) { S.project = null; render(); return; }
  try {
    S.project = await api(`/api/projects/${encodeURIComponent(name)}`);
  } catch (err) {
    S.project = null;
    toast(err.message, true);
  }
  render();
}

async function loadRunning() {
  try { S.running = (await api("/api/ppmodel")).running; } catch (e) { S.running = []; }
  renderRunning();
}

function setProject(data) {
  S.project = data;
  render();
  loadProjects();
}

// ---- actions ---------------------------------------------------------------

function newProject() {
  dialog("New project", [
    h("label", {}, "Name (letters, digits, _ . -)", h("input", { name: "name", required: true, pattern: "[A-Za-z0-9][A-Za-z0-9_.\\-]{0,63}", autocomplete: "off" })),
    h("label", {}, "Description", h("input", { name: "description", autocomplete: "off" })),
  ], "Create", async (v) => {
    const data = await api("/api/projects/new", v);
    location.hash = encodeURIComponent(data.name);
    await loadProjects();
  });
}

function deleteProject() {
  const name = S.project.name;
  dialog(`Delete project ${name}?`, [
    h("p", {}, "This permanently deletes the project folder and every file in it:"),
    h("p", {}, h("code", {}, S.project.path)),
    h("label", {}, `Type ${name} to confirm`, h("input", { name: "confirm", required: true, autocomplete: "off" })),
  ], "Delete project", async (v) => {
    await api(`/api/projects/${encodeURIComponent(name)}/delete`, v);
    toast(`Deleted ${name}`);
    location.hash = "";
    await loadProjects();
  }, true);
}

async function saveDescription(value) {
  if (value === (S.project.description || "")) return;
  await guarded(async () => {
    setProject(await api(`/api/projects/${encodeURIComponent(S.project.name)}/update`, { description: value }));
  });
}

async function upload(files) {
  if (!files || !files.length) return;
  const exists = new Set(S.project.folders[S.folder].map((f) => f.name));
  const clash = [...files].filter((f) => exists.has(f.name)).map((f) => f.name);
  const send = async (overwrite) => {
    const form = new FormData();
    form.append("folder", S.folder);
    if (overwrite) form.append("overwrite", "1");
    for (const f of files) form.append("file", f, f.name);
    setProject(await api(`/api/projects/${encodeURIComponent(S.project.name)}/upload`, undefined, form));
    toast(`Uploaded ${files.length} file${files.length > 1 ? "s" : ""} to ${S.folder}/`);
  };
  if (clash.length) {
    dialog("Replace existing files?", [h("p", {}, `${clash.join(", ")} already exist${clash.length > 1 ? "" : "s"} in ${S.folder}/.`)],
      "Replace", () => send(true), true);
  } else {
    await guarded(() => send(false));
  }
}

function newModel() {
  const builtin = (S.meta && S.meta.builtin) || [];
  dialog("New model", [
    h("div", { class: "row" },
      h("label", {}, "File name", h("input", { name: "base", required: true, pattern: "[A-Za-z0-9][A-Za-z0-9_.\\-]{0,58}", autocomplete: "off" })),
      h("label", {}, "Format", h("select", { name: "fmt" },
        h("option", { value: "glm" }, ".glm  GridLAB-D module pypower"),
        h("option", { value: "py" }, ".py  PYPOWER case"),
        h("option", { value: "json" }, ".json  PYPOWER JSON")))),
    h("label", {}, "Start from", h("select", { name: "template" },
      h("option", { value: "" }, "Empty case"),
      h("optgroup", { label: "PYPOWER built-in cases" }, builtin.map((c) => h("option", { value: c }, c))))),
  ], "Create and open", async (v) => {
    const file = `${v.base}.${v.fmt}`;
    setProject(await api(`/api/projects/${encodeURIComponent(S.project.name)}/models/new`, { file, template: v.template }));
    await openModel(file);
  });
}

async function openModel(file) {
  // open the tab first (synchronously, inside the click) so popup blockers allow it
  const tab = window.open("about:blank", "_blank");
  try {
    const res = await api("/api/ppmodel/open", { project: S.project.name, file });
    if (tab) tab.location = res.url; else window.open(res.url, "_blank");
    loadRunning();
  } catch (err) {
    if (tab) tab.close();
    toast(err.message, true);
  }
}

async function stopModel(project, file) {
  await guarded(() => api("/api/ppmodel/stop", { project, file }));
  loadRunning();
}

function renameFile(file) {
  dialog(`Rename ${file}`, [
    h("label", {}, "New name", h("input", { name: "new", required: true, value: file, autocomplete: "off" })),
  ], "Rename", async (v) => {
    setProject(await api(`/api/projects/${encodeURIComponent(S.project.name)}/rename`, { folder: S.folder, file, new: v.new }));
    loadRunning();
  });
}

function removeFile(file) {
  dialog(`Delete ${file}?`, [h("p", {}, `This permanently deletes ${S.folder}/${file}.`)], "Delete", async () => {
    setProject(await api(`/api/projects/${encodeURIComponent(S.project.name)}/remove`, { folder: S.folder, file }));
    loadRunning();
  }, true);
}

function exitServer() {
  dialog("Stop pptools?", [h("p", {}, "This stops the pptools server and every model editor it started. Unsaved model edits are lost.")],
    "Stop", async () => {
      await api("/api/exit", {});
      document.getElementById("main").replaceChildren(h("div", { class: "card" }, h("h1", {}, "pptools stopped"),
        h("p", { class: "muted" }, "Run pptools serve to start it again.")));
    }, true);
}

// ---- rendering -------------------------------------------------------------

function renderSidebar() {
  const nav = document.getElementById("project-list");
  const current = S.project && S.project.name;
  nav.replaceChildren(...(S.projects.length ? S.projects.map((p) =>
    h("a", { href: `#${encodeURIComponent(p.name)}`, class: p.name === current ? "active" : null, title: p.error || p.description || p.name },
      p.name, h("span", { class: "desc" }, p.error ? "unreadable record" : (p.description || "")))) :
    [h("div", { class: "empty" }, "No projects yet")]));
}

function renderRunning() {
  const box = document.getElementById("running");
  box.replaceChildren(...S.running.map((r) => h("span", { class: "chip", title: `ppmodel on port ${r.port}` },
    h("a", { href: r.url, target: "_blank" }, `${r.project}/${r.file}`),
    h("button", { title: "Stop this model editor (unsaved edits are lost)", onclick: () => stopModel(r.project, r.file) }, "×"))));
}

function renderWelcome() {
  const root = S.meta ? S.meta.root : "";
  return h("div", { class: "card welcome" },
    h("h1", {}, "pptools"),
    h("p", {}, "Tools to edit, provision, and run time-series simulations of power systems with pypower_sim."),
    h("ol", {},
      h("li", {}, "Create a project. Each project is a folder in ", h("code", {}, root), " with ",
        h("code", {}, "models/"), ", ", h("code", {}, "data/"), ", ", h("code", {}, "sims/"), " and ", h("code", {}, "outputs/"), "."),
      h("li", {}, "Add network models (new, from a PYPOWER built-in case, or uploaded) and edit them in ppmodel."),
      h("li", {}, "Build time-series data panels (ppdata), run simulations (ppsim), and review outputs (ppoutput) — planned.")),
    h("button", { class: "primary", onclick: newProject }, "New project"));
}

function toolCards() {
  const p = S.project;
  return h("div", { class: "pipeline" }, (S.meta ? S.meta.tools : []).map((t) => {
    const n = (p.folders[t.folder] || []).length;
    let action;
    if (t.name === "ppmodel") {
      action = h("button", { class: "small", onclick: () => { S.folder = "models"; render(); } }, "Models");
    } else {
      action = h("button", { class: "small", onclick: () => { location.href = `/${t.name}/?project=${encodeURIComponent(p.name)}`; } }, "Open");
    }
    return h("div", { class: "tool" },
      h("h3", {}, t.title, h("span", { class: `badge ${t.status}` }, t.status)),
      h("span", { class: "name" }, t.name),
      h("p", {}, t.summary),
      h("div", { class: "foot" }, h("span", { class: "muted" }, `${t.folder}/ · ${n} file${n === 1 ? "" : "s"}`), action));
  }));
}

function fileRow(f) {
  const p = S.project;
  const href = `/api/projects/${encodeURIComponent(p.name)}/file/${S.folder}/${encodeURIComponent(f.name)}`;
  const canModel = S.folder === "models" && S.meta.model_formats.includes(f.ext);
  const isRunning = S.running.some((r) => r.project === p.name && r.file === f.name);
  return h("tr", {},
    h("td", { class: "fname" }, f.name),
    h("td", { class: "num" }, size(f.size)),
    h("td", {}, when(f.modified)),
    h("td", { class: "actions" },
      canModel ? h("button", { class: "small primary", title: isRunning ? "Show the running ppmodel editor" : "Edit in ppmodel (new tab)", onclick: () => openModel(f.name) },
        isRunning ? "Show" : "Edit") : null,
      h("a", { href: `${href}?download=1` }, h("button", { class: "link small", title: "Download" }, "Download")),
      h("button", { class: "link small", onclick: () => renameFile(f.name) }, "Rename"),
      h("button", { class: "link small danger", onclick: () => removeFile(f.name) }, "Delete")));
}

function folderView() {
  const p = S.project;
  const folders = S.meta.folders;
  const files = p.folders[S.folder] || [];
  const input = h("input", { type: "file", multiple: true, hidden: true, onchange: (e) => upload(e.target.files) });
  const box = h("div", { class: "folder" },
    h("div", { class: "folder-bar" },
      h("span", { class: "hint" }, folders[S.folder], " — drop files here to upload"),
      S.folder === "models" ? h("button", { class: "small primary", onclick: newModel }, "New model") : null,
      h("button", { class: "small", onclick: () => input.click() }, "Upload…"), input),
    files.length ?
      h("table", { class: "files" },
        h("thead", {}, h("tr", {}, h("th", {}, "File"), h("th", { style: "text-align:right" }, "Size"), h("th", {}, "Modified"), h("th", {}, ""))),
        h("tbody", {}, files.map(fileRow))) :
      h("div", { class: "empty-folder" }, `No files in ${S.folder}/ yet.`));
  box.addEventListener("dragover", (e) => { e.preventDefault(); box.classList.add("drag"); });
  box.addEventListener("dragleave", () => box.classList.remove("drag"));
  box.addEventListener("drop", (e) => { e.preventDefault(); box.classList.remove("drag"); upload(e.dataTransfer.files); });
  return [
    h("div", { class: "tabs" }, Object.keys(folders).map((name) =>
      h("button", { class: name === S.folder ? "active" : null, onclick: () => { S.folder = name; render(); } },
        `${name}/`, h("span", { class: "count" }, (p.folders[name] || []).length)))),
    box];
}

function render() {
  renderSidebar();
  const main = document.getElementById("main");
  const p = S.project;
  if (!p || !S.meta) { main.replaceChildren(renderWelcome()); document.title = "pptools"; return; }
  document.title = `${p.name} · pptools`;
  const desc = h("input", { class: "desc-input", value: p.description || "", placeholder: "Add a description…",
    onchange: (e) => saveDescription(e.target.value), onkeydown: (e) => { if (e.key === "Enter") e.target.blur(); } });
  main.replaceChildren(
    h("div", { class: "project-head" },
      h("div", { class: "title" }, h("h1", {}, p.name), desc,
        h("div", { class: "meta" }, h("code", {}, p.path), ` · created ${when(p.created)} · modified ${when(p.modified)}`)),
      h("button", { class: "small danger", onclick: deleteProject }, "Delete project")),
    toolCards(),
    ...folderView());
}

// ---- start -----------------------------------------------------------------

async function start() {
  document.getElementById("new-project-btn").onclick = newProject;
  document.getElementById("exit-btn").onclick = exitServer;
  try {
    S.meta = await api("/api/meta");
    document.getElementById("root").textContent = S.meta.root;
    document.getElementById("version").textContent = `v${S.meta.version}`;
  } catch (err) {
    toast(err.message, true);
  }
  await guarded(loadProjects);
  window.addEventListener("hashchange", () => loadProject(decodeURIComponent(location.hash.slice(1))));
  await loadProject(decodeURIComponent(location.hash.slice(1)));
  loadRunning();
  setInterval(loadRunning, 5000);
  // refresh file lists when returning from a tool tab (models saved there)
  window.addEventListener("focus", () => { if (S.project) loadProject(S.project.name); loadRunning(); });
}

start();
