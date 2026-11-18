// pprun: simulation runner page (see pptools/pprun/server.py for the API)
"use strict";

const S = {
  meta: null,        // GET /pprun/api/meta
  project: null,     // GET /pprun/api/project
  sim: null,         // GET /pprun/api/sim (name, definition, check, labels, steps)
  def: null,         // working copy of the definition (edited in Settings)
  dirty: false,
  view: "settings",
  run: null,         // GET /pprun/api/run of the run selected in Runs/Outputs/Network
  runName: null,
  viewers: {},       // per tab: {file, run, table, columns:Set, page}
  netSource: "model",
  poll: null,
};
const PALETTE = ["--series-1", "--series-2", "--series-3", "--series-4", "--series-5", "--series-6", "--series-7", "--series-8"];
const MAX_SERIES = PALETTE.length;
const PAGE = 200;

const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
const h = (tag, attrs = {}, ...kids) => {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "value") el.value = v;
    else if (k === "checked") el.checked = !!v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false) el.append(kid.nodeType ? kid : String(kid));
  return el;
};
const SVGNS = "http://www.w3.org/2000/svg";
const sv = (tag, attrs = {}) => { const el = document.createElementNS(SVGNS, tag); for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v); return el; };
const cssVar = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const project = () => new URLSearchParams(location.search).get("project");
const q = obj => new URLSearchParams({ project: project(), ...obj }).toString();
const utc = iso => iso ? iso.replace("T", " ").replace(/:00Z$|Z$/, "") : "–";

async function api(path, body) {
  const opts = body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-PPTools": "1" },
    body: JSON.stringify({ project: project(), ...body }),
  };
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
  if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}
let toastTimer = null;
function toast(msg, error = false) {
  const t = $("#toast");
  t.textContent = msg; t.className = "toast" + (error ? " error" : ""); t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, error ? 7000 : 2500);
}
async function guard(fn) { try { return await fn(); } catch (err) { toast(err.message, true); } }

// ---------------------------------------------------------------- state

function setUrl() {
  const p = new URLSearchParams(location.search);
  if (S.sim) p.set("sim", S.sim.name); else p.delete("sim");
  history.replaceState(null, "", "?" + p.toString());
}
async function loadProject() {
  S.project = await api(`/pprun/api/project?${q({})}`);
  renderChrome();
}
async function loadSim(name) {
  if (!name) { S.sim = null; S.def = null; S.dirty = false; setUrl(); renderAll(); return; }
  setSim(await api(`/pprun/api/sim?${q({ sim: name })}`));
}
function setSim(sim) {
  S.sim = sim; S.def = JSON.parse(JSON.stringify(sim.definition)); S.dirty = false;
  setUrl(); renderAll();
}
function markDirty() { S.dirty = true; renderChrome(); }
async function save() {
  if (!S.sim) return;
  setSim(await api("/pprun/api/sim/save", { sim: S.sim.name, definition: S.def }));
  toast(`Saved sims/${S.sim.name}`);
}
function simRuns() { return S.project ? S.project.runs.filter(r => S.sim && r.simulation === S.sim.name) : []; }
function latestRun() { return simRuns()[0] || null; }

// ---------------------------------------------------------------- chrome

function renderChrome() {
  const p = S.project;
  $("#crumb-project").textContent = project() || "";
  $("#home").href = "/" + (project() ? "#" + project() : "");
  document.title = `${S.dirty ? "• " : ""}${S.sim ? S.sim.name.replace(/\.json$/, "") + " — " : ""}pprun`;
  const sel = $("#sim-select");
  sel.replaceChildren(h("option", { value: "" }, p && p.sims.length ? "— choose —" : "— none —"),
    ...(p ? p.sims : []).map(s => h("option", { value: s.name }, s.name.replace(/\.json$/, "") + (s.error ? " (invalid)" : ""))));
  sel.value = S.sim ? S.sim.name : "";
  sel.disabled = !p;
  $("[data-action=new-sim]").disabled = !p;
  $("#save-btn").disabled = !S.sim || !S.dirty;
  $("#dirty").hidden = !S.dirty;
  const run = latestRun();
  const running = run && run.state === "running" && run.alive;
  $("#run-btn").disabled = !S.sim || running;
  $("#cancel-btn").hidden = !running;
  const bar = $("#run-progress");
  bar.hidden = !run;
  if (run) {
    const pct = Math.round(100 * (run.progress || 0));
    $(".fill", bar).style.width = `${run.state === "done" ? 100 : pct}%`;
    $(".text", bar).textContent = run.state === "running"
      ? `${pct}% · ${utc(run.timestamp)}${run.errors ? ` · ${run.errors} errors` : ""}`
      : `${run.state} · ${run.steps}/${run.total} steps${run.errors ? ` · ${run.errors} errors` : ""}`;
    bar.title = `${run.name}: ${run.state}${run.message ? " — " + run.message : ""}`;
  }
  const issues = S.sim ? S.sim.check : [];
  const nerr = issues.filter(i => i.level === "error").length, nwarn = issues.length - nerr;
  const ic = $("#issue-count");
  ic.textContent = issues.length ? issues.length : "";
  ic.className = "count issues" + (nerr ? " has-err" : nwarn ? " has-warn" : "");
  $("#input-count").textContent = S.def ? S.def.inputs.length || "" : "";
  $("#run-count").textContent = simRuns().length || "";
  $$("#tabs > button").forEach(b => { b.classList.toggle("active", b.dataset.view === S.view); b.disabled = !S.sim && b.dataset.view !== "runs"; });
}
function show(view) { S.view = view; renderAll(); }
function renderAll() {
  renderChrome();
  $$(".view").forEach(v => v.classList.remove("active"));
  if (!project() || (!S.sim && S.view !== "runs")) { $("#view-empty").classList.add("active"); return renderEmpty(); }
  $(`#view-${S.view}`).classList.add("active");
  ({ settings: renderSettings, network: renderNetwork, inputs: renderInputs, outputs: renderOutputs, runs: renderRuns })[S.view]();
}

async function renderEmpty() {
  const el = $("#view-empty");
  if (!project()) {
    const { projects } = await api("/api/projects");
    el.replaceChildren(h("div", { class: "card welcome" }, h("h1", {}, "pprun"),
      h("p", {}, "Choose a project to set up and run its simulations."),
      projects.length ? h("ul", {}, ...projects.map(p => h("li", {}, h("a", { href: `?project=${encodeURIComponent(p.name)}` }, p.name)))) :
        h("p", { class: "muted" }, "No projects yet: create one on the ", h("a", { href: "/" }, "pptools"), " page.")));
    return;
  }
  const p = S.project;
  el.replaceChildren(h("div", { class: "card welcome" }, h("h1", {}, "Simulations"),
    h("p", {}, "A simulation runs a model from ", h("code", {}, "models/"), " from a start to an end date at a time step (1 h by default), "
      + "with time-series inputs from ", h("code", {}, "data/"), ". Each run writes its own folder in ", h("code", {}, "outputs/"), "."),
    p.sims.length ? h("p", {}, "Choose a simulation above, or create a new one.") : null,
    !p.models.length ? h("p", { class: "err" }, "This project has no model yet: add one on the ", h("a", { href: "/#" + project() }, "pptools"), " page.") :
      h("p", {}, h("button", { class: "primary", onclick: newSim }, "New simulation…"))));
}

// ---------------------------------------------------------------- settings

function field(label, input, title) { return h("label", { title }, label, input); }
function bind(el, get, set, kind = "str") {
  el.value = get() ?? "";
  el.addEventListener("change", () => {
    let v = el.value;
    if (kind === "num") v = v === "" ? null : Number(v);
    set(v); markDirty();
  });
  return el;
}
function check(label, get, set, title) {
  const cb = h("input", { type: "checkbox", checked: get() });
  cb.addEventListener("change", () => { set(cb.checked); markDirty(); });
  return h("label", { class: "check", title }, cb, label);
}
function select(options, get, set) {
  const el = h("select", {}, ...options.map(o => Array.isArray(o) ? h("option", { value: o[0] }, o[1]) : h("option", { value: o }, o)));
  return bind(el, get, set);
}
function numInput(get, set, attrs = {}) { return bind(h("input", { type: "number", step: "any", class: "n", ...attrs }), get, set, "num"); }
function textInput(get, set, attrs = {}) { return bind(h("input", { type: "text", ...attrs }), get, set); }
const columnsOf = table => (S.meta.tables[table] || []);

function renderIssues() {
  const issues = S.sim.check;
  return h("section", { class: "card" }, h("h2", {}, "Check", h("span", { class: "hint" }, S.dirty ? "of the saved definition — save to check again" : "")),
    h("ul", { class: "issues-list" }, issues.length ? issues.map(i => h("li", { class: i.level }, h("span", { class: "where" }, i.where), i.message))
      : h("li", { class: "ok" }, `Ready to run: ${S.sim.steps} time steps.`)));
}

function renderSettings() {
  const d = S.def, el = $("#view-settings");
  const models = S.project.models;
  const time = h("section", { class: "card" }, h("h2", {}, "Model and time", h("span", { class: "hint" }, "pandas.date_range(start, end, freq) in UTC")),
    h("div", { class: "grid-form" },
      field("Model", select(models.includes(d.model) || !d.model ? models : [d.model, ...models], () => d.model, v => d.model = v), "File in models/"),
      field("Start", textInput(() => d.start, v => d.start = v, { placeholder: "2020-01-01 00:00" }), "First time step; an offset like -07:00 is allowed"),
      field("End", textInput(() => d.end, v => d.end = v, { placeholder: "2020-01-02 00:00" }), "Last time step"),
      field("Time step (freq)", textInput(() => d.freq, v => d.freq = v || "1h", { placeholder: "1h", list: "freqs" }), "pandas frequency: 5min, 15min, 1h, 1D, …"),
      field("Time zone of start/end", textInput(() => d.tz, v => d.tz = v || "UTC", { placeholder: "UTC" }), "Used when start/end have no offset (e.g. US/Pacific)"),
      field("Inclusive", select(S.meta.inclusive, () => d.inclusive, v => d.inclusive = v), "Which ends of the range are time steps"),
      field("Zero BASE_KV becomes (kV)", numInput(() => d.base_kv, v => d.base_kv = v, { placeholder: "leave zeros" }), "PPModel.default_values BASE_KV: replaces bus base kV of 0; blank leaves zeros")),
    h("datalist", { id: "freqs" }, ...["5min", "15min", "30min", "1h", "2h", "6h", "1D"].map(x => h("option", { value: x }))));

  const solver = h("section", { class: "card" }, h("h2", {}, "Solver", h("span", { class: "hint" }, "PPSolver.run_timeseries")),
    h("div", { class: "grid-form" },
      field("OPF each time step", select([["ac", "AC OPF, then PF"], ["dc", "DC OPF, then PF"], ["none", "No OPF (PF only)"]], () => d.opf, v => { d.opf = v; renderSettings(); }), "use_acopf: True, False, or None"),
      check("Stop on first failure", () => d.stop_on_fail, v => d.stop_on_fail = v, "stop_on_fail"),
      check("Check limit violations", () => d.violations, v => d.violations = v, "violations: bus voltage, branch rating, generator and DC line limits after each step"),
      field("Violation tolerance (absolute)", numInput(() => d.abs_err, v => d.abs_err = v, { placeholder: "exact" }), "get_violations abs_err"),
      field("Violation tolerance (relative)", numInput(() => d.rel_err, v => d.rel_err = v, { placeholder: "exact" }), "get_violations rel_err")),
    d.violations && d.stop_on_fail ? h("p", { class: "help" }, "The first time step with a violation stops the run.") : null);

  const oce = d.oce;
  const oceCard = h("section", { class: "card" }, h("h2", {}, "Initial capacity expansion (OCE)", h("span", { class: "hint" }, "with_oce: OceOptions — experimental")),
    h("div", { class: "grid-form" }, check("Run OCE at the peak-load step before the run", () => !!d.oce, v => { d.oce = v ? JSON.parse(JSON.stringify(S.meta.oce)) : null; renderSettings(); })),
    oce ? h("div", { class: "grid-form" },
      field("Load margin", numInput(() => oce.margin, v => oce.margin = v ?? 0.15)),
      check("Use all resources (allin)", () => oce.allin, v => oce.allin = v),
      field("Voltage setpoints", select([["", "none"], ["true", "true"], ["false", "false"]], () => oce.setpoints === null ? "" : String(oce.setpoints),
        v => oce.setpoints = v === "" ? null : v === "true"), "setpoints on generation buses"),
      field("Small angles", numInput(() => typeof oce.smallangles === "number" ? oce.smallangles : null, v => oce.smallangles = v, { placeholder: "none" }), "restrict voltage angles near zero"),
      ...Object.keys(oce.costs).map(k => field(`Cost: ${k}`, numInput(() => oce.costs[k], v => oce.costs[k] = v ?? 0))),
      field("cvxpy canon_backend", textInput(() => oce.cvx.canon_backend, v => oce.cvx.canon_backend = v))) : null,
    h("p", { class: "help" }, "Needs an input to bus.PD to find the peak. pypower_sim records the OCE's success as a failure (known issue)."));

  // inputs
  const inRows = d.inputs.map((it, n) => h("tr", {},
    h("td", {}, select(S.project.data.includes(it.file) || !it.file ? ["", ...S.project.data] : [it.file, ...S.project.data], () => it.file, v => it.file = v)),
    h("td", {}, select(Object.keys(S.meta.tables), () => it.table, v => { it.table = v; it.column = ""; it.mapping = ""; renderSettings(); })),
    h("td", {}, select(["", ...columnsOf(it.table)], () => it.column, v => it.column = v)),
    h("td", {}, numInput(() => it.scale, v => it.scale = v ?? 1)),
    h("td", {}, numInput(() => it.offset, v => it.offset = v ?? 0)),
    h("td", {}, select([["", "row number"], ...columnsOf(it.table).slice(0, 13).map(c => [c, c])], () => it.mapping, v => it.mapping = v)),
    h("td", { class: "x" }, h("button", { class: "link danger", title: "Remove", onclick: () => { d.inputs.splice(n, 1); markDirty(); renderSettings(); } }, "✕"))));
  const inputs = h("section", { class: "card" }, h("h2", {}, "Inputs", h("span", { class: "hint" }, "PPData.set_input: value = data × scale + offset")),
    d.inputs.length ? h("table", { class: "rows" }, h("thead", {}, h("tr", {}, ...["Panel in data/", "Table", "Column", "Scale", "Offset", "CSV columns are", ""].map(x => h("th", {}, x)))), h("tbody", {}, inRows))
      : h("p", { class: "muted" }, "No inputs: every time step solves the model as it is."),
    h("button", { onclick: () => { d.inputs.push({ file: S.project.data[0] || "", table: "bus", column: "PD", scale: 1, offset: 0, mapping: "" }); markDirty(); renderSettings(); } }, "+ Add input"),
    S.project.data.length ? null : h("p", { class: "help" }, "Upload CSV panels to the project's data/ folder on the pptools page (timestamp first, then one column per case row)."));

  // outputs
  const outRows = d.outputs.map((it, n) => h("tr", {},
    h("td", {}, select(Object.keys(S.meta.tables), () => it.table, v => { it.table = v; it.column = columnsOf(v)[0]; renderSettings(); })),
    h("td", {}, select(columnsOf(it.table), () => it.column, v => it.column = v)),
    h("td", {}, numInput(() => it.scale, v => it.scale = v ?? 1)),
    h("td", {}, numInput(() => it.offset, v => it.offset = v ?? 0)),
    h("td", {}, textInput(() => it.format, v => it.format = v || "g", { class: "n" })),
    h("td", { class: "mono muted" }, `${it.table}_${it.column}.csv`),
    h("td", { class: "x" }, h("button", { class: "link danger", title: "Remove", onclick: () => { d.outputs.splice(n, 1); markDirty(); renderSettings(); } }, "✕"))));
  const have = new Set(d.outputs.map(o => `${o.table}.${o.column}`));
  const quick = [["bus", ["VM", "VA", "PD", "QD", "LAM_P", "LAM_Q"]], ["gen", ["PG", "QG", "VG", "MU_PMAX", "MU_PMIN"]], ["branch", ["PF", "QF", "PT", "QT", "MU_SF", "MU_ST"]], ["dcline", ["PF", "PT", "QF", "QT"]]];
  const outputs = h("section", { class: "card" }, h("h2", {}, "Outputs", h("span", { class: "hint" }, "PPData.set_output: one CSV per case column, one column per row")),
    h("table", { class: "rows" }, h("thead", {}, h("tr", {}, ...["Table", "Column", "Scale", "Offset", "Format", "File", ""].map(x => h("th", {}, x)))), h("tbody", {}, outRows)),
    h("div", { class: "chips" }, h("span", { class: "muted" }, "Add:"), ...quick.flatMap(([t, cols]) => cols.filter(c => !have.has(`${t}.${c}`)).map(c =>
      h("button", { onclick: () => { d.outputs.push({ table: t, column: c, scale: 1, offset: 0, format: "g" }); markDirty(); renderSettings(); } }, `${t}.${c}`))),
      h("button", { onclick: () => { d.outputs.push({ table: "bus", column: "VM", scale: 1, offset: 0, format: "g" }); markDirty(); renderSettings(); } }, "other…")));

  // recorders
  const recRows = d.recorders.map((it, n) => h("tr", {},
    h("td", {}, textInput(() => it.name, v => it.name = v)),
    h("td", {}, bind(h("input", { type: "text", placeholder: "cost" }), () => it.target.join(" "), v => it.target = v.split(/[\s,]+/).filter(Boolean))),
    h("td", {}, numInput(() => it.scale, v => it.scale = v ?? 1)),
    h("td", {}, numInput(() => it.offset, v => it.offset = v ?? 0)),
    h("td", {}, textInput(() => it.format, v => it.format = v || "g", { class: "n" })),
    h("td", { class: "x" }, h("button", { class: "link danger", title: "Remove", onclick: () => { d.recorders.splice(n, 1); markDirty(); renderSettings(); } }, "✕"))));
  const recorders = h("section", { class: "card" }, h("h2", {}, "Recorders", h("span", { class: "hint" }, "PPData.set_recorder: single case values to recorders.csv")),
    d.recorders.length ? h("table", { class: "rows" }, h("thead", {}, h("tr", {}, ...["Name", "Case keys", "Scale", "Offset", "Format", ""].map(x => h("th", {}, x)))), h("tbody", {}, recRows)) : null,
    h("button", { onclick: () => { d.recorders.push({ name: "", target: [], scale: 1, offset: 0, format: "g" }); markDirty(); renderSettings(); } }, "+ Add recorder"),
    h("p", { class: "help" }, "Case keys name a scalar in the case: cost (OPF objective, $/h, after OPF), baseMVA, version."));

  // PYPOWER options
  const opts = h("section", { class: "card" }, h("h2", {}, "PYPOWER options", h("span", { class: "hint" }, "PPModel.options → ppoption; only changed values are saved")),
    ...S.meta.options.map(g => {
      const changed = g.options.filter(o => o.name in d.options).length;
      return h("details", { class: "opts", open: changed > 0 || g.group === "Power flow" },
        h("summary", {}, g.group, h("span", { class: "hint" }, [g.note, changed ? `${changed} changed` : ""].filter(Boolean).join(" · "))),
        h("table", { class: "opts" }, h("tbody", {}, ...g.options.map(o => optionRow(o)))));
    }));

  el.replaceChildren(h("div", { class: "settings" }, renderIssues(), time, solver, inputs, outputs, recorders, oceCard, opts));
}

function optionRow(o) {
  const d = S.def, cur = o.name in d.options ? d.options[o.name] : o.default;
  let input;
  const setv = v => {
    if (v === "" || v === null || String(v) === String(o.default)) delete d.options[o.name]; else d.options[o.name] = v;
    markDirty(); tr.classList.toggle("changed", o.name in d.options);
  };
  if (o.type === "bool") {
    input = h("select", {}, h("option", { value: "true" }, "true"), h("option", { value: "false" }, "false"));
    input.value = String(!!cur);
    input.addEventListener("change", () => setv(input.value === "true"));
  } else {
    input = h("input", { type: o.type === "str" ? "text" : "number", step: "any", value: cur });
    input.addEventListener("change", () => setv(o.type === "str" ? input.value : (input.value === "" ? "" : Number(input.value))));
  }
  const tr = h("tr", { class: o.name in d.options ? "changed" : "" },
    h("td", { class: "name", title: `pypower default: ${o.pypower}` }, o.name),
    h("td", { class: "val" }, input),
    h("td", { class: "doc" }, o.doc, h("span", { class: "muted" }, ` (default ${o.default})`)));
  return tr;
}

// ---------------------------------------------------------------- network

function renderNetwork() {
  const runs = simRuns().filter(r => r.steps > 0 || r.state === "done");
  const src = $("#net-source");
  src.replaceChildren(h("option", { value: "model" }, `Model: ${S.def.model || "(none)"}`),
    ...runs.map(r => h("option", { value: r.name }, `Run ${r.name} (${r.state})`)));
  if (S.netSource !== "model" && !runs.some(r => r.name === S.netSource)) S.netSource = "model";
  src.value = S.netSource;
  const frame = $("#net-frame");
  if (S.netSource === "model") {
    $("#net-time-wrap").hidden = true;
    if (!S.def.model) { frame.hidden = true; $("#net-empty").textContent = "Choose a model in Settings."; return; }
    if (frame.dataset.key === "model:" + S.def.model) return;
    frame.dataset.key = "model:" + S.def.model;
    $("#net-note").textContent = "The model as saved; edits here change the model file.";
    guard(async () => {
      const r = await api("/api/ppedit/open", { file: S.def.model });
      frame.src = r.url + "?view=network"; frame.hidden = false; $("#net-empty").textContent = "";
    });
  } else {
    $("#net-time-wrap").hidden = false;
    guard(async () => {
      if (S.runName !== S.netSource || !S.run) await loadRun(S.netSource);
      const n = Math.max(1, S.run.status.steps || 0);
      const range = $("#net-time");
      range.max = Math.min(n, S.run.times.length) - 1;
      if (+range.value > +range.max) range.value = range.max;
      $("#net-time-label").textContent = utc(S.run.times[+range.value]);
      if (!frame.dataset.key || !frame.dataset.key.startsWith("run:" + S.netSource)) {
        frame.hidden = true; $("#net-empty").textContent = "Choose a time step and press Show time step: pprun re-solves it and opens it in ppedit.";
        $("#net-note").textContent = "";
      }
    });
  }
}
async function showSnapshot() {
  const t = S.run.times[+$("#net-time").value];
  $("#net-note").textContent = `Solving ${utc(t)}…`;
  await guard(async () => {
    const r = await api("/pprun/api/snapshot", { run: S.netSource, time: t });
    const frame = $("#net-frame");
    frame.dataset.key = `run:${S.netSource}:${r.time}`;
    frame.src = r.url; frame.hidden = false; $("#net-empty").textContent = "";
    $("#net-note").textContent = `${utc(r.time)} UTC · OPF ${r.opf === null ? "off" : r.opf ? "ok" : "failed"} · PF ${r.pf ? "ok" : "failed"}`
      + (r.notes.length ? " · " + r.notes.join("; ") : "");
  });
}

// ---------------------------------------------------------------- data viewers (inputs, outputs)

function colLabel(table, mapping, col) {
  if (!table) return col;
  if (mapping) return `${mapping} ${col}`;
  const labels = (S.viewLabels || {})[table];
  return labels && /^\d+$/.test(col) && labels[+col] ? labels[+col] : col;
}

async function openViewer(tab, spec) {
  const key = `${spec.run || ""}/${spec.file}`;
  const cur = S.viewers[tab];
  if (cur && cur.key === key) return drawViewer(tab);
  const head = await api(`/pprun/api/table?${q({ file: spec.file, ...(spec.run ? { run: spec.run } : {}), head: 1 })}`);
  S.viewers[tab] = { ...spec, key, head, columns: new Set(head.columns.slice(0, Math.min(4, MAX_SERIES))), page: 0 };
  drawViewer(tab);
}

async function drawViewer(tab) {
  const v = S.viewers[tab], el = $(`#${tab}-viewer`);
  if (!v) return;
  const labelOf = c => colLabel(v.table, v.mapping, c);
  const pick = h("div", { class: "col-pick" }, ...v.head.columns.map(c => {
    const cb = h("input", { type: "checkbox", checked: v.columns.has(c) });
    cb.addEventListener("change", () => {
      if (cb.checked && v.columns.size >= MAX_SERIES) { cb.checked = false; return toast(`At most ${MAX_SERIES} columns are plotted at once`, true); }
      cb.checked ? v.columns.add(c) : v.columns.delete(c); drawChart(tab);
    });
    return h("label", {}, cb, labelOf(c));
  }));
  const dl = `/pprun/api/file?${q({ file: v.file, ...(v.run ? { run: v.run } : {}) })}`;
  el.replaceChildren(
    h("h2", {}, v.title),
    h("div", { class: "meta" }, `${v.run ? `outputs/${v.run}/` : "data/"}${v.file} · ${v.head.rows} rows × ${v.head.columns.length} columns · ${utc(v.head.first)} to ${utc(v.head.last)} UTC · `,
      h("a", { href: dl }, "download")),
    h("div", { class: "col-tools" }, `Plot (up to ${MAX_SERIES}):`,
      h("button", { class: "small", onclick: () => { v.columns = new Set(v.head.columns.slice(0, MAX_SERIES)); drawViewer(tab); } }, "first 8"),
      h("button", { class: "small", onclick: () => { v.columns.clear(); drawViewer(tab); } }, "none")),
    pick,
    h("div", { class: "chart", id: `${tab}-chart` }),
    h("div", { id: `${tab}-table` }));
  drawChart(tab); drawTable(tab);
}

async function drawChart(tab) {
  const v = S.viewers[tab], box = $(`#${tab}-chart`);
  if (!v.columns.size) { box.replaceChildren(h("div", { class: "muted" }, "Choose columns to plot.")); return; }
  const width = Math.max(320, box.clientWidth - 24);
  const cols = v.head.columns.filter(c => v.columns.has(c));
  const data = await api(`/pprun/api/table?${q({ file: v.file, ...(v.run ? { run: v.run } : {}), columns: cols.join(","), points: Math.round(width) })}`);
  // color follows the column's position in the file, so a series keeps its color when others are added or removed
  const colorOf = c => cssVar(PALETTE[v.head.columns.indexOf(c) % MAX_SERIES]);
  lineChart(box, data, { width, label: c => colLabel(v.table, v.mapping, c), color: colorOf, single: cols.length === 1 ? v.title : null });
}

function niceTicks(lo, hi, n = 5) {
  if (!(isFinite(lo) && isFinite(hi))) return [0, 1];
  if (lo === hi) { lo -= Math.abs(lo) * 0.05 || 1; hi += Math.abs(hi) * 0.05 || 1; }
  const step0 = (hi - lo) / n, mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= step0);
  const ticks = [];
  for (let t = Math.floor(lo / step) * step; t <= hi + step * 1e-9; t += step) ticks.push(+t.toPrecision(12));
  if (ticks[ticks.length - 1] < hi) ticks.push(+(ticks[ticks.length - 1] + step).toPrecision(12));
  return ticks;
}
const fmtNum = x => x === null || x === undefined ? "–" : Math.abs(x) >= 1e5 || (Math.abs(x) < 1e-3 && x !== 0) ? x.toExponential(3) : +x.toPrecision(6) + "";
function timeTicks(t0, t1, n) {
  const span = t1 - t0, H = 3600e3, D = 24 * H;
  const steps = [60e3, 5 * 60e3, 15 * 60e3, H, 3 * H, 6 * H, 12 * H, D, 2 * D, 7 * D, 14 * D, 30 * D, 91 * D, 365 * D];
  const step = steps.find(s => span / s <= n) || 365 * D;
  const out = [];
  for (let t = Math.ceil(t0 / step) * step; t <= t1; t += step) out.push(t);
  return { ticks: out, step };
}
function timeLabel(t, step) {
  const s = new Date(t).toISOString();
  return step >= 24 * 3600e3 ? s.slice(5, 10) : step >= 3600e3 ? s.slice(5, 10) + " " + s.slice(11, 16) : s.slice(11, 16);
}

function lineChart(box, data, { width, label, color, single }) {
  const H = 300, m = { l: 62, r: 14, t: 8, b: 26 }, W = width;
  const times = data.time, cols = data.columns;
  let lo = Infinity, hi = -Infinity;
  for (const c of cols) { for (const x of data.min[c]) if (x !== null) lo = Math.min(lo, x); for (const x of data.max[c]) if (x !== null) hi = Math.max(hi, x); }
  const yt = niceTicks(lo, hi);
  const y0 = yt[0], y1 = yt[yt.length - 1];
  const t0 = times[0], t1 = times[times.length - 1] === t0 ? t0 + 1 : times[times.length - 1];
  const X = t => m.l + (t - t0) / (t1 - t0) * (W - m.l - m.r);
  const Y = v => m.t + (1 - (v - y0) / (y1 - y0 || 1)) * (H - m.t - m.b);
  const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": `Line chart of ${cols.map(label).join(", ")}` });
  const grid = sv("g", { class: "grid" }), axis = sv("g", { class: "axis" });
  for (const v of yt) {
    grid.append(sv("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v) }));
    const tx = sv("text", { x: m.l - 6, y: Y(v) + 4, "text-anchor": "end" }); tx.textContent = fmtNum(v); axis.append(tx);
  }
  const tt = timeTicks(t0, t1, Math.max(2, Math.floor((W - m.l - m.r) / 90)));
  for (const t of tt.ticks) {
    const tx = sv("text", { x: X(t), y: H - 8, "text-anchor": "middle" }); tx.textContent = timeLabel(t, tt.step); axis.append(tx);
  }
  axis.append(sv("line", { class: "base", x1: m.l, x2: W - m.r, y1: H - m.b, y2: H - m.b }));
  svg.append(grid, axis);
  const decimated = cols.some(c => data.min[c].some((x, i) => x !== data.max[c][i]));
  for (const c of cols) {
    const col = color(c);
    if (decimated) { // min-max envelope band plus the mid line
      let top = "", bot = "";
      times.forEach((t, i) => { const a = data.max[c][i], b = data.min[c][i]; if (a === null) return; top += `${top ? "L" : "M"}${X(t).toFixed(1)},${Y(a).toFixed(1)}`; bot = `L${X(t).toFixed(1)},${Y(b).toFixed(1)}` + bot; });
      if (top) svg.append(sv("path", { class: "band", d: top + bot + "Z", fill: col }));
    }
    let d = "", pen = false;
    times.forEach((t, i) => {
      const a = data.max[c][i], b = data.min[c][i];
      if (a === null) { pen = false; return; }
      d += `${pen ? "L" : "M"}${X(t).toFixed(1)},${Y((a + b) / 2).toFixed(1)}`; pen = true;
    });
    svg.append(sv("path", { class: "series", d, stroke: col }));
  }
  const cross = sv("line", { class: "cross", y1: m.t, y2: H - m.b, visibility: "hidden" });
  const hit = sv("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent" });
  svg.append(cross, hit);
  const tip = h("div", { class: "tip", hidden: true });
  hit.addEventListener("mousemove", e => {
    const r = svg.getBoundingClientRect(), x = (e.clientX - r.left) * W / r.width;
    const t = t0 + (x - m.l) / (W - m.l - m.r) * (t1 - t0);
    let i = 0, best = Infinity;
    times.forEach((tt2, k) => { const dd = Math.abs(tt2 - t); if (dd < best) { best = dd; i = k; } });
    cross.setAttribute("x1", X(times[i])); cross.setAttribute("x2", X(times[i])); cross.setAttribute("visibility", "visible");
    tip.replaceChildren(h("div", { class: "t" }, new Date(times[i]).toISOString().replace("T", " ").slice(0, 16) + " UTC" + (decimated ? " (bucket)" : "")),
      ...cols.map(c => {
        const a = data.max[c][i], b = data.min[c][i];
        return h("div", {}, h("span", { class: "sw", style: `background:${color(c)}` }), label(c), h("span", { class: "v" }, a === b ? fmtNum(a) : `${fmtNum(b)} – ${fmtNum(a)}`));
      }));
    tip.hidden = false;
    const px = (X(times[i]) / W) * r.width;
    tip.style.left = `${px + 12 + 200 > r.width ? px - 212 : px + 12}px`; tip.style.top = "30px";
  });
  hit.addEventListener("mouseleave", () => { tip.hidden = true; cross.setAttribute("visibility", "hidden"); });
  const legend = single ? h("div", { class: "legend" }, label(cols[0])) :
    h("div", { class: "legend" }, ...cols.map(c => h("span", {}, h("span", { class: "sw", style: `background:${color(c)}` }), label(c))));
  box.replaceChildren(legend, svg, tip);
}

async function drawTable(tab) {
  const v = S.viewers[tab], box = $(`#${tab}-table`);
  const page = await api(`/pprun/api/table?${q({ file: v.file, ...(v.run ? { run: v.run } : {}), offset: v.page * PAGE, limit: PAGE })}`);
  const pages = Math.max(1, Math.ceil(page.rows / PAGE));
  const go = n => { v.page = Math.max(0, Math.min(pages - 1, n)); drawTable(tab); };
  box.replaceChildren(
    h("div", { class: "pager" }, h("button", { class: "small", disabled: v.page === 0, onclick: () => go(v.page - 1) }, "‹ Prev"),
      `Rows ${page.offset + 1}–${page.offset + page.values.length} of ${page.rows} (page ${v.page + 1} of ${pages})`,
      h("button", { class: "small", disabled: v.page >= pages - 1, onclick: () => go(v.page + 1) }, "Next ›")),
    h("div", { class: "table-wrap" }, h("table", { class: "data" },
      h("thead", {}, h("tr", {}, h("th", {}, "timestamp (UTC)"), ...page.columns.map(c => h("th", { title: c }, colLabel(v.table, v.mapping, c))))),
      h("tbody", {}, ...page.values.map((row, i) => h("tr", {}, h("td", {}, utc(page.time[i])), ...row.map(x => h("td", {}, typeof x === "number" ? fmtNum(x) : x ?? "–"))))))));
}

function renderInputs() {
  const list = $("#input-list"), d = S.def;
  S.viewLabels = S.sim.labels;
  if (!d.inputs.length) {
    list.replaceChildren(h("div", { class: "empty" }, "No inputs. Add them in Settings."));
    $("#inputs-viewer").replaceChildren();
    return;
  }
  const cur = S.viewers.inputs;
  list.replaceChildren(...d.inputs.map((it, n) => {
    const a = h("a", { class: cur && cur.file === it.file && !cur.run ? "active" : "" }, it.file || "(no file)", h("span", { class: "sub" }, `→ ${it.table}.${it.column}${it.scale !== 1 ? ` ×${it.scale}` : ""}${it.offset ? ` +${it.offset}` : ""}`));
    a.addEventListener("click", () => guard(async () => { await openViewer("inputs", { file: it.file, table: it.table, mapping: it.mapping, title: `Input ${n + 1}: ${it.table}.${it.column}` }); renderInputs(); }));
    return a;
  }));
  if (!cur && d.inputs[0].file && S.project.data.includes(d.inputs[0].file)) list.firstChild.click();
  else if (cur) drawViewer("inputs");
}

async function loadRun(name) {
  S.run = await api(`/pprun/api/run?${q({ run: name })}`);
  S.runName = name;
  return S.run;
}

function renderOutputs() {
  const runs = simRuns();
  const sel = $("#output-run");
  sel.replaceChildren(...runs.map(r => h("option", { value: r.name }, `${r.name.replace(/^.*_/, "")} · ${r.state}`)));
  if (!runs.length) {
    sel.disabled = true;
    $("#output-list").replaceChildren(h("div", { class: "empty" }, "No runs yet: press Run."));
    $("#outputs-viewer").replaceChildren();
    return;
  }
  sel.disabled = false;
  if (!S.runName || !runs.some(r => r.name === S.runName)) S.runName = runs[0].name;
  sel.value = S.runName;
  guard(async () => {
    if (!S.run || S.run.status.name !== S.runName || S.run.status.state === "running") await loadRun(S.runName);
    S.viewLabels = S.run.labels;
    const cur = S.viewers.outputs;
    const list = $("#output-list");
    if (!S.run.outputs.length) { list.replaceChildren(h("div", { class: "empty" }, "This run wrote no output files.")); $("#outputs-viewer").replaceChildren(); return; }
    list.replaceChildren(...S.run.outputs.map(o => {
      const a = h("a", { class: cur && cur.run === S.runName && cur.file === o.file ? "active" : "" }, o.title, h("span", { class: "sub" }, o.file));
      a.addEventListener("click", () => guard(async () => { await openViewer("outputs", { file: o.file, run: S.runName, table: o.table, title: o.title }); renderOutputs(); }));
      return a;
    }));
    if (!cur || cur.run !== S.runName) list.firstChild.click();
    else if (S.run.status.state === "running") { S.viewers.outputs.key = null; openViewer("outputs", cur); }
  });
}

// ---------------------------------------------------------------- runs

function renderRuns() {
  const el = $("#view-runs");
  const all = S.project.runs, mine = simRuns();
  const shown = S.sim ? mine : all;
  const dur = r => r.started && r.finished ? `${Math.round((Date.parse(r.finished) - Date.parse(r.started)) / 1000)} s` : r.state === "running" ? "…" : "–";
  const rows = shown.map(r => {
    const tr = h("tr", { class: r.name === S.runName ? "sel" : "" },
      h("td", { class: "mono" }, r.name), h("td", {}, h("span", { class: `state ${r.state}` }, r.state)),
      h("td", { class: "num" }, `${Math.round(100 * (r.state === "done" ? 1 : r.progress || 0))}%`),
      h("td", { class: "num" }, `${r.steps ?? 0}/${r.total ?? "?"}`), h("td", { class: "num" }, r.errors ?? 0),
      h("td", {}, utc(r.started)), h("td", { class: "num" }, dur(r)),
      h("td", {}, r.alive ? h("button", { class: "small", onclick: e => { e.stopPropagation(); cancelRun(r.name); } }, "Cancel")
        : h("button", { class: "small danger", onclick: e => { e.stopPropagation(); deleteRun(r.name); } }, "Delete")));
    tr.addEventListener("click", () => guard(async () => { await loadRun(r.name); renderRuns(); }));
    return tr;
  });
  el.replaceChildren(
    h("h2", {}, S.sim ? `Runs of ${S.sim.name.replace(/\.json$/, "")}` : "All runs", h("span", { class: "muted" }, S.sim && all.length > mine.length ? ` · ${all.length - mine.length} runs of other simulations` : "")),
    shown.length ? h("table", { class: "runs" }, h("thead", {}, h("tr", {}, ...["Run", "State", "Progress", "Steps", "Errors", "Started (UTC)", "Duration", ""].map(x => h("th", {}, x)))), h("tbody", {}, rows))
      : h("p", { class: "muted" }, "No runs yet."),
    S.run && shown.some(r => r.name === S.runName) ? runDetail(S.run) : null);
}

function runDetail(r) {
  const st = r.status;
  const files = h("table", { class: "kv" }, h("tbody", {}, ...r.files.map(f => h("tr", {},
    h("td", {}, h("a", { href: `/pprun/api/file?${q({ run: st.name, file: f.name })}` }, f.name)), h("td", { class: "num" }, `${(f.size / 1024).toFixed(1)} kB`)))));
  return h("div", { class: "run-detail" },
    h("div", {},
      h("section", { class: "card" }, h("h2", {}, "Status"), h("table", { class: "kv" }, h("tbody", {},
        ...[["State", st.state], ["Event", st.event], ["Current time step", utc(st.timestamp)], ["Steps", `${st.steps}/${st.total}`], ["Errors", st.errors],
          ["Started", utc(st.started)], ["Finished", utc(st.finished)], ["Message", st.message || "–"]].map(([k, v]) => h("tr", {}, h("td", {}, k), h("td", {}, v ?? "–")))))),
      h("section", { class: "card" }, h("h2", {}, "Profile"), Object.keys(r.profile).length ? h("table", { class: "kv" }, h("tbody", {},
        ...Object.entries(r.profile).map(([k, v]) => h("tr", {}, h("td", {}, k), h("td", { class: "num" }, v))))) : h("p", { class: "muted" }, "Written when the run ends.")),
      h("section", { class: "card" }, h("h2", {}, "Files"), files)),
    h("div", {},
      h("section", { class: "card" }, h("h2", {}, `Errors and warnings (${r.errors.length})`), r.errors.length ? h("pre", {}, r.errors.join("\n")) : h("p", { class: "muted" }, "None.")),
      h("section", { class: "card" }, h("h2", {}, "Log"), r.log ? h("pre", {}, r.log) : h("p", { class: "muted" }, "Empty."))));
}

async function startRun() {
  if (S.dirty) await save();
  const r = await api("/pprun/api/run", { sim: S.sim.name });
  S.runName = r.run; S.run = null;
  toast(`Started ${r.run}`);
  await loadProject();
  startPolling();
  renderAll();
}
async function cancelRun(name) { await guard(async () => { await api("/pprun/api/cancel", { run: name }); toast(`Cancelling ${name}…`); await loadProject(); }); }
async function deleteRun(name) {
  await guard(async () => {
    S.project = await api("/pprun/api/run/delete", { run: name });
    if (S.runName === name) { S.runName = null; S.run = null; }
    for (const k of Object.keys(S.viewers)) if (S.viewers[k] && S.viewers[k].run === name) delete S.viewers[k];
    renderAll();
  });
}

function startPolling() {
  if (S.poll) return;
  S.poll = setInterval(async () => {
    const before = S.project && S.project.runs.filter(r => r.state === "running").map(r => r.name);
    try { await loadProject(); } catch (_) { return; }
    const running = S.project.runs.filter(r => r.state === "running");
    if (S.runName && (running.some(r => r.name === S.runName) || (before || []).includes(S.runName))) {
      if (S.view === "runs") { await loadRun(S.runName).catch(() => {}); renderRuns(); }
      else if (S.view === "outputs" && !running.length) renderOutputs();
    } else if (S.view === "runs") renderRuns();
    if (!running.length) { clearInterval(S.poll); S.poll = null; if (S.view !== "settings") renderAll(); }
  }, 1000);
}

// ---------------------------------------------------------------- new simulation

function newSim() {
  const dlg = $("#new-dialog"), form = $("#new-form");
  form.reset();
  form.model.replaceChildren(...S.project.models.map(m => h("option", { value: m }, m)));
  const day = new Date().toISOString().slice(0, 10);
  const next = new Date(Date.parse(day) + 86400e3).toISOString().slice(0, 10);
  form.start.value = `${day} 00:00`; form.end.value = `${next} 00:00`;
  dlg.returnValue = "";
  dlg.showModal();
  dlg.onclose = () => {
    if (dlg.returnValue !== "ok") return;
    guard(async () => {
      const sim = await api("/pprun/api/sim/new", { sim: form.sim.value, model: form.model.value, start: form.start.value, end: form.end.value });
      await loadProject(); setSim(sim); show("settings");
    });
  };
}

// ---------------------------------------------------------------- init

async function init() {
  S.meta = await api("/pprun/api/meta");
  document.addEventListener("click", e => {
    const b = e.target.closest("[data-action]");
    if (b && !b.disabled) {
      const a = b.dataset.action;
      if (a === "new-sim") newSim();
      else if (a === "save") guard(save);
      else if (a === "run") guard(startRun);
      else if (a === "cancel") { const r = latestRun(); if (r) cancelRun(r.name); }
      else if (a === "snapshot") showSnapshot();
      return;
    }
    const tab = e.target.closest("[data-view]");
    if (tab && !tab.disabled) show(tab.dataset.view);
  });
  $("#sim-select").addEventListener("change", async e => {
    const want = e.target.value;
    if (S.dirty) { e.target.value = S.sim.name; if (!await confirmDiscard()) return; e.target.value = want; }
    S.viewers = {}; S.run = null; S.runName = null; $("#net-frame").dataset.key = "";
    guard(() => loadSim(e.target.value));
  });
  $("#net-source").addEventListener("change", e => { S.netSource = e.target.value; renderNetwork(); });
  $("#net-time").addEventListener("input", e => { $("#net-time-label").textContent = utc(S.run.times[+e.target.value]); });
  $("#output-run").addEventListener("change", e => { S.runName = e.target.value; S.run = null; renderOutputs(); });
  document.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); if (S.dirty) guard(save); }
  });
  window.addEventListener("beforeunload", e => { if (S.dirty) { e.preventDefault(); e.returnValue = ""; } });
  let resizeTimer = null;
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (S.viewers[S.view]) drawChart(S.view); }, 200); });
  if (!project()) return renderAll();
  await loadProject();
  const want = new URLSearchParams(location.search).get("sim");
  if (want && S.project.sims.some(s => s.name === want)) await loadSim(want);
  else if (S.project.sims.length === 1) await loadSim(S.project.sims[0].name);
  else renderAll();
  if (S.project.runs.some(r => r.state === "running")) startPolling();
}
function confirmDiscard() {
  const dlg = $("#confirm-dialog");
  dlg.returnValue = "";
  dlg.showModal();
  return new Promise(resolve => { dlg.onclose = () => resolve(dlg.returnValue === "ok"); });
}

init().catch(err => toast(err.message, true));
