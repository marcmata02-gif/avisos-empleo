import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm";

const CFG = window.APP_CONFIG || {};
const $ = (s, el = document) => el.querySelector(s);
const show = (id) => ["login", "setup", "main"].forEach((x) => $("#" + x).classList.toggle("hidden", x !== id));

if (!CFG.supabaseUrl || !CFG.supabaseKey || CFG.supabaseUrl.includes("TU_PROYECTO")) {
  show("setup");
  throw new Error("Falta config.js");
}

const sb = createClient(CFG.supabaseUrl, CFG.supabaseKey, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
});

const COLS = "id,title,company,published_at,first_seen,links,sources,area,areas,sector,is_graduate,flag_texts," +
  "cv_id,cv_name,cv_note,jornada,modalidad,contrato,summary,requirements,salario,ubicacion,priority,passes,discard_reason";

const state = {
  offers: [], rejected: null, status: new Map(), sources: [], cvNames: {},
  tab: "nuevas", shown: 120, target: null,
};

// ------------------------------------------------------------------ util
const parseDate = (s) => (s ? new Date(s) : null);
const offerDate = (o) => parseDate(o.published_at) || parseDate(o.first_seen);
function ago(d) {
  if (!d) return "";
  const mins = Math.max(1, Math.round((Date.now() - d.getTime()) / 60000));
  if (mins < 60) return `hace ${mins} min`;
  const h = Math.round(mins / 60);
  if (h < 24) return `hace ${h} h`;
  const days = Math.round(h / 24);
  if (days === 1) return "hace 1 día";
  if (days < 31) return `hace ${days} días`;
  return d.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
}
const norm = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}
const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : null);

// ------------------------------------------------------------------ acceso
async function init() {
  const m = location.hash.match(/o=([\w-]+)/);
  if (m) sessionStorage.setItem("target", m[1]);
  state.target = sessionStorage.getItem("target");

  const { data } = await sb.auth.getSession();
  if (data.session) return start();
  show("login");
  sb.auth.onAuthStateChange((_e, session) => { if (session) start(); });
}

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = $("#login-email").value.trim();
  $("#login-msg").textContent = "Enviando…";
  const { error } = await sb.auth.signInWithOtp({
    email,
    options: { emailRedirectTo: location.origin + location.pathname, shouldCreateUser: false },
  });
  $("#login-msg").textContent = error
    ? "No se pudo enviar: " + error.message
    : "Listo. Abre el enlace que te ha llegado por email (desde este mismo dispositivo).";
});

$("#btn-logout").addEventListener("click", async () => { await sb.auth.signOut(); location.reload(); });
$("#btn-refresh").addEventListener("click", () => load());

let started = false;
async function start() {
  if (started) return;
  started = true;
  show("main");
  await load();
}

// ------------------------------------------------------------------ datos
async function load() {
  $("#summary-line").textContent = "Cargando…";
  const [offers, statuses, sources] = await Promise.all([
    sb.from("offers").select(COLS).eq("passes", true).order("first_seen", { ascending: false }).limit(2000),
    sb.from("offer_status").select("*"),
    sb.from("source_state").select("*"),
  ]);
  if (offers.error) {
    $("#summary-line").textContent = "Error al cargar: " + offers.error.message +
      " (¿has añadido tu email en allowed_users? Paso 4 de la guía)";
    return;
  }
  state.offers = offers.data || [];
  state.status = new Map((statuses.data || []).map((s) => [s.offer_id, s]));
  state.sources = sources.data || [];
  const conf = state.sources.find((s) => s.source === "config");
  state.cvNames = conf?.meta?.cv || {};
  state.rejected = null;
  if ($("#f-rejected").checked) await loadRejected();
  fillFilters();
  render();
  renderStatus();
}

async function loadRejected() {
  const since = new Date(Date.now() - 30 * 864e5).toISOString();
  const { data } = await sb.from("offers").select(COLS).eq("passes", false).gte("last_seen", since)
    .order("first_seen", { ascending: false }).limit(1000);
  state.rejected = data || [];
}

function fillFilters() {
  const all = state.offers;
  const fill = (sel, values) => {
    const cur = sel.value;
    const first = sel.options[0].outerHTML;
    sel.innerHTML = first;
    [...values].filter(Boolean).sort((a, b) => a.localeCompare(b, "es")).forEach((v) => {
      const o = el("option", null, v); o.value = v; sel.appendChild(o);
    });
    sel.value = cur;
  };
  const areas = new Set((state.sources.find((s) => s.source === "config")?.meta?.areas) || all.map((o) => o.area));
  fill($("#f-area"), areas);
  fill($("#f-company"), new Set(all.map((o) => o.company)));
  fill($("#f-source"), new Set(all.flatMap((o) => o.sources || [])));
}

// ------------------------------------------------------------------ filtros
function filtered() {
  const q = norm($("#f-q").value);
  const area = $("#f-area").value, sector = $("#f-sector").value, company = $("#f-company").value,
    source = $("#f-source").value, grad = $("#f-grad").checked, rej = $("#f-rejected").checked;
  let list = rej ? (state.rejected || []) : state.offers;
  if (!rej) {
    list = list.filter((o) => {
      const st = state.status.get(o.id)?.status || null;
      if (state.tab === "nuevas") return !st;
      if (state.tab === "todas") return true;
      return st === state.tab;
    });
  }
  return list.filter((o) => {
    if (area && !(o.areas || [o.area]).includes(area)) return false;
    if (sector && o.sector !== sector) return false;
    if (company && o.company !== company) return false;
    if (source && !(o.sources || []).includes(source)) return false;
    if (grad && !o.is_graduate) return false;
    if (q) {
      const hay = norm([o.title, o.company, o.summary, o.area, o.sector, o.ubicacion, (o.requirements || []).join(" ")].join(" "));
      if (!q.split(/\s+/).every((w) => hay.includes(w))) return false;
    }
    return true;
  }).sort((a, b) => (offerDate(b) || 0) - (offerDate(a) || 0));
}

function counts() {
  const c = { nuevas: 0, guardada: 0, aplicada: 0, descartada: 0 };
  for (const o of state.offers) {
    const st = state.status.get(o.id)?.status;
    if (!st) c.nuevas++; else if (c[st] != null) c[st]++;
  }
  for (const k in c) $("#c-" + k).textContent = c[k] || "";
}

// ------------------------------------------------------------------ pintar
function render() {
  counts();
  const items = filtered();
  const list = $("#list");
  list.innerHTML = "";
  $("#empty").classList.toggle("hidden", items.length > 0);
  const nModa = items.filter((o) => o.sector === "Moda").length;
  const nGrad = items.filter((o) => o.is_graduate).length;
  $("#summary-line").textContent = $("#f-rejected").checked
    ? `${items.length} ofertas descartadas por el filtro (últimos 30 días). Útil para ajustar criterios.`
    : `${items.length} ofertas · ${nModa} de moda · ${nGrad} graduate programs`;

  let target = state.target ? items.findIndex((o) => o.id === state.target) : -1;
  const limit = Math.max(state.shown, target + 1);
  items.slice(0, limit).forEach((o) => list.appendChild(card(o)));
  if (items.length > limit) {
    const li = el("li");
    const b = el("button", "btn", `Mostrar más (${items.length - limit})`);
    b.style.width = "100%";
    b.onclick = () => { state.shown += 150; render(); };
    li.appendChild(b);
    list.appendChild(li);
  }
  if (target >= 0) {
    const node = document.getElementById("o-" + state.target);
    if (node) { node.classList.add("target"); node.scrollIntoView({ behavior: "smooth", block: "start" }); }
    state.target = null;
    sessionStorage.removeItem("target");
  }
}

function card(o) {
  const node = $("#card-tpl").content.firstElementChild.cloneNode(true);
  node.id = "o-" + o.id;
  const st = state.status.get(o.id) || {};
  if (o.sector === "Moda") node.classList.add("moda");
  if (o.is_graduate) node.classList.add("grad");
  if (!o.passes) node.classList.add("rejected");

  const badges = $(".badges", node);
  if (o.is_graduate) badges.appendChild(el("span", "badge grad", "Graduate"));
  if (o.sector) badges.appendChild(el("span", "badge " + (o.sector === "Moda" ? "moda" : "belleza"), o.sector));
  if (o.area) badges.appendChild(el("span", "badge area", o.area));
  if (st.status && state.tab === "todas") badges.appendChild(el("span", "badge state", st.status));

  $(".ago", node).textContent = ago(offerDate(o));
  $(".title", node).textContent = o.title || "";
  $(".company", node).textContent = [o.company, o.ubicacion].filter(Boolean).join(" · ");

  const chips = $(".chips", node);
  [o.modalidad, o.jornada, o.contrato, o.salario && "💶 " + o.salario].filter(Boolean)
    .forEach((t) => chips.appendChild(el("span", "chip", t)));

  $(".summary", node).textContent = o.summary || "";
  const warns = $(".warnings", node);
  (o.flag_texts || []).forEach((t) => warns.appendChild(el("div", "warn", "⚠ " + t)));

  const reqs = o.requirements || [];
  if (reqs.length) reqs.forEach((r) => $(".reqs ul", node).appendChild(el("li", null, r)));
  else $(".reqs", node).remove();

  const cv = $(".cv", node);
  if (o.cv_id) {
    cv.append("📄 CV recomendado: ");
    cv.appendChild(el("b", null, `${o.cv_id} · ${o.cv_name || state.cvNames[o.cv_id] || ""}`));
    if (o.cv_note) cv.appendChild(el("span", "note", o.cv_note));
  } else cv.remove();

  $(".reason", node).textContent = o.passes ? "" : "Descartada por: " + (o.discard_reason || "");

  const srcs = $(".sources", node);
  (o.links || []).forEach((l) => {
    const u = safeUrl(l.url);
    if (!u) return;
    const a = el("a", null, "↗ " + l.source);
    a.href = u; a.target = "_blank"; a.rel = "noopener";
    srcs.appendChild(a);
  });
  const first = safeUrl(o.links?.[0]?.url);
  const apply = $(".apply", node);
  if (first) apply.href = first; else apply.remove();

  node.querySelectorAll(".st").forEach((b) => {
    b.classList.toggle("on", st.status === b.dataset.st);
    b.addEventListener("click", () => setStatus(o, st.status === b.dataset.st ? null : b.dataset.st));
  });

  const applied = $(".applied", node);
  if (st.status === "aplicada") {
    applied.classList.remove("hidden");
    const sel = $(".cv-used", applied);
    sel.appendChild(el("option", null, "—"));
    Object.entries(state.cvNames).forEach(([k, v]) => {
      const op = el("option", null, `${k} · ${v}`); op.value = `${k} · ${v}`; sel.appendChild(op);
    });
    sel.value = st.cv_used || (o.cv_id ? `${o.cv_id} · ${state.cvNames[o.cv_id] || o.cv_name}` : "—");
    sel.addEventListener("change", () => saveExtra(o, { cv_used: sel.value === "—" ? null : sel.value }));
    const note = $(".note", applied);
    note.value = st.note || "";
    let t;
    note.addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => saveExtra(o, { note: note.value }), 600); });
  }
  return node;
}

async function setStatus(o, status) {
  const prev = state.status.get(o.id) || {};
  const row = { offer_id: o.id, status, cv_used: prev.cv_used ?? null, note: prev.note ?? null,
    updated_at: new Date().toISOString() };
  if (status === "aplicada" && !row.cv_used && o.cv_id) row.cv_used = `${o.cv_id} · ${state.cvNames[o.cv_id] || o.cv_name}`;
  const { error } = await sb.from("offer_status").upsert(row);
  if (error) return alert("No se pudo guardar: " + error.message);
  state.status.set(o.id, row);
  render();
}

async function saveExtra(o, patch) {
  const prev = state.status.get(o.id) || { offer_id: o.id, status: null };
  const row = { ...prev, ...patch, offer_id: o.id, updated_at: new Date().toISOString() };
  const { error } = await sb.from("offer_status").upsert(row);
  if (!error) state.status.set(o.id, row);
}

function renderStatus() {
  const body = $("#status-body");
  body.innerHTML = "";
  const t = el("table");
  const rows = state.sources.filter((s) => !["config", "limpieza"].includes(s.source))
    .sort((a, b) => (b.last_error ? 1 : 0) - (a.last_error ? 1 : 0) || a.source.localeCompare(b.source));
  rows.forEach((s) => {
    const tr = el("tr");
    tr.appendChild(el("td", null, s.source.replace("empresa:", "🏢 ")));
    tr.appendChild(el("td", null, ago(parseDate(s.last_run))));
    tr.appendChild(el("td", s.last_error ? "err" : null,
      s.last_error ? s.last_error : `${s.meta?.ultimas_ofertas ?? 0} ofertas leídas`));
    t.appendChild(tr);
  });
  body.appendChild(t);
  const conf = state.sources.find((s) => s.source === "config");
  const pend = conf?.meta?.empresas_pendientes || [];
  if (pend.length) {
    body.appendChild(el("p", null,
      `Empresas sin página de empleo configurada (sus ofertas llegan por LinkedIn, Indeed o InfoJobs): ${pend.join(", ")}.`));
  }
}

// ------------------------------------------------------------------ eventos
$("#tabs").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-tab]");
  if (!b) return;
  state.tab = b.dataset.tab;
  state.shown = 120;
  document.querySelectorAll("#tabs button").forEach((x) => x.classList.toggle("active", x === b));
  render();
});
["#f-q", "#f-area", "#f-sector", "#f-company", "#f-source", "#f-grad"].forEach((s) =>
  $(s).addEventListener("input", () => { state.shown = 120; render(); }));
$("#f-rejected").addEventListener("change", async (e) => {
  if (e.target.checked && !state.rejected) { $("#summary-line").textContent = "Cargando…"; await loadRejected(); }
  render();
});

init();
