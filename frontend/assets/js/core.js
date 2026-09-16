// ═════════════════════════════════════════════════════════════
// CORE — infraestrutura, autenticação, navegação, painel,
// cidadãos e usuários. Transversal aos dois MVPs (ver
// "Lean Inception — Vida+ Clínica"): carregado antes de
// prontuario.js e gestao.js, que dependem destes utilitários.
// ═════════════════════════════════════════════════════════════
const API = "/api";
let token = localStorage.getItem("esus_token") || null;
let user = JSON.parse(localStorage.getItem("esus_user") || "null");

// ───────── infra ─────────
const $ = (s, e = document) => e.querySelector(s);
const el = (h) => { const t = document.createElement("template"); t.innerHTML = h.trim(); return t.content.firstElementChild; };
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function api(path, opt = {}) {
  const h = { "Content-Type": "application/json", ...(opt.headers || {}) };
  if (token) h.Authorization = `Bearer ${token}`;
  const r = await fetch(API + path, { cache: "no-store", ...opt, headers: h });
  if (r.status === 401) { sair(); throw new Error("Sessão expirada."); }
  if (r.status === 204) return null;
  const d = await r.json().catch(() => null);
  if (!r.ok) { const m = d && d.detail; throw new Error(typeof m === "string" ? m : m ? JSON.stringify(m) : `Erro ${r.status}`); }
  return d;
}

function toast(msg, err = false) {
  const t = $("#toast"); t.textContent = msg; t.classList.toggle("err", err); t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 3800);
}

const fmtDT = (i) => i ? new Date(i).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "-";
const fmtD = (i) => {
  if (!i) return "-";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(i);          // data pura → sem fuso
  return m ? `${m[3]}/${m[2]}/${m[1]}` : new Date(i).toLocaleDateString("pt-BR");
};
const hojeInput = () => { const d = new Date(); return new Date(d - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 10); };
const risco = (r) => r ? `<span class="badge risco-${r}">${r}</span>` : "";
const stBadge = (s) => `<span class="badge st-${s}">${s.replace(/_/g, " ")}</span>`;

// ───────── modal ─────────
function openModal(title, body) {
  $("#modal-title").textContent = title;
  const b = $("#modal-body"); b.innerHTML = ""; b.appendChild(body);
  $("#modal-backdrop").hidden = false;
}
const closeModal = () => ($("#modal-backdrop").hidden = true);
$("#modal-close").onclick = closeModal;
$("#modal-backdrop").onclick = (e) => e.target.id === "modal-backdrop" && closeModal();

function formModal({ title, fields, values = {}, onSubmit, submitLabel = "Salvar" }) {
  const f = el('<form class="grid2"></form>');
  fields.forEach((fd) => {
    const w = el(`<div class="${fd.full ? "full" : ""}"></div>`);
    w.appendChild(el(`<label class="fld">${fd.label}${fd.required ? " *" : ""}</label>`));
    let inp;
    const v = values[fd.name] ?? fd.default ?? "";
    if (fd.type === "textarea") { inp = el(`<textarea name="${fd.name}"></textarea>`); inp.value = v; }
    else if (fd.type === "select") {
      inp = el(`<select name="${fd.name}"></select>`);
      (fd.options || []).forEach((o) => { const op = el(`<option value="${esc(o.value)}">${esc(o.label)}</option>`); if (String(o.value) === String(v)) op.selected = true; inp.appendChild(op); });
    } else { inp = el(`<input name="${fd.name}" type="${fd.type || "text"}" />`); inp.value = v; }
    if (fd.required) inp.required = true;
    if (fd.step) inp.step = fd.step;
    w.appendChild(inp); f.appendChild(w);
  });
  const a = el('<div class="modal-actions full"></div>');
  const c = el('<button type="button" class="btn sec">Cancelar</button>'); c.onclick = closeModal;
  a.append(c, el(`<button type="submit" class="btn">${submitLabel}</button>`));
  f.appendChild(a);
  f.onsubmit = async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(f).entries());
    fields.forEach((fd) => {
      if (data[fd.name] === "") data[fd.name] = null;
      else if (fd.cast === "number" && data[fd.name] != null) data[fd.name] = Number(data[fd.name]);
      else if (fd.cast === "int" && data[fd.name] != null) data[fd.name] = parseInt(data[fd.name], 10);
    });
    try { await onSubmit(data); closeModal(); } catch (err) { toast(err.message, true); }
  };
  openModal(title, f);
}

// autocomplete de catálogo → chama cb({label,value,...})
function autocomplete(endpoint, placeholder, onPick) {
  const wrap = el(`<div class="autocomplete"><input placeholder="${placeholder}" /></div>`);
  const inp = $("input", wrap);
  let box, deb;
  const fechar = () => { if (box) { box.remove(); box = null; } };
  inp.oninput = () => {
    clearTimeout(deb);
    deb = setTimeout(async () => {
      const q = inp.value.trim();
      if (q.length < 2) return fechar();
      const its = await api(`${endpoint}?q=${encodeURIComponent(q)}`).catch(() => []);
      fechar();
      box = el('<div class="opts"></div>');
      if (!its.length) box.appendChild(el('<div class="opt muted">nada encontrado</div>'));
      its.forEach((it) => {
        const label = it.descricao ? `${it.codigo} — ${it.descricao}` : (it.nome + (it.apresentacao ? ` (${it.apresentacao})` : ""));
        const o = el(`<div class="opt">${esc(label)}</div>`);
        o.onclick = () => { onPick(it, label); inp.value = ""; fechar(); };
        box.appendChild(o);
      });
      wrap.appendChild(box);
    }, 220);
  };
  inp.onblur = () => setTimeout(fechar, 200);
  return wrap;
}

// gráfico de linha SVG simples
function lineChart(titulo, series) {
  // series: [{tipo,unidade,pontos:[{data,valor}]}]  (linhas no mesmo eixo)
  const W = 520, H = 150, pad = 30;
  const todos = series.flatMap((s) => s.pontos);
  if (todos.length < 2) return el(`<div class="chart"><small class="muted">${titulo}: dados insuficientes</small></div>`);
  const xs = todos.map((p) => new Date(p.data).getTime());
  const ys = todos.map((p) => p.valor);
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const y0 = Math.min(...ys) * 0.95, y1 = Math.max(...ys) * 1.05;
  const px = (t) => pad + ((t - x0) / (x1 - x0 || 1)) * (W - pad * 2);
  const py = (v) => H - pad - ((v - y0) / (y1 - y0 || 1)) * (H - pad * 2);
  const cores = ["#1e6fd9", "#db2777", "#059669", "#b45309"];
  let paths = "";
  series.forEach((s, i) => {
    if (s.pontos.length < 2) return;
    const d = s.pontos.map((p, j) => `${j ? "L" : "M"}${px(new Date(p.data).getTime()).toFixed(1)},${py(p.valor).toFixed(1)}`).join(" ");
    paths += `<path d="${d}" fill="none" stroke="${cores[i % 4]}" stroke-width="2"/>`;
    paths += s.pontos.map((p) => `<circle cx="${px(new Date(p.data).getTime()).toFixed(1)}" cy="${py(p.valor).toFixed(1)}" r="3" fill="${cores[i % 4]}"/>`).join("");
  });
  const leg = series.map((s, i) => `<tspan fill="${cores[i % 4]}">■</tspan> ${s.tipo.replace(/_/g, " ").toLowerCase()}`).join("   ");
  const ult = series.map((s) => s.pontos.length ? `${s.tipo.replace("PA_", "").toLowerCase()}: <b>${s.pontos.at(-1).valor}</b> ${s.unidade}` : "").filter(Boolean).join(" · ");
  return el(`<div class="chart">
    <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
      <b>${titulo}</b><span class="muted">${ult}</span></div>
    <svg viewBox="0 0 ${W} ${H}">
      <line x1="${pad}" y1="${H - pad}" x2="${W - pad}" y2="${H - pad}" stroke="#cbd5e1"/>
      <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${H - pad}" stroke="#cbd5e1"/>
      <text x="${pad}" y="14" font-size="10" fill="#64748b">${y1.toFixed(0)}</text>
      <text x="${pad}" y="${H - pad}" font-size="10" fill="#64748b">${y0.toFixed(0)}</text>
      ${paths}
      <text x="${pad}" y="${H - 6}" font-size="10">${leg}</text>
    </svg></div>`);
}

// ───────── auth ─────────
$("#login-form").onsubmit = async (e) => {
  e.preventDefault();
  const d = Object.fromEntries(new FormData(e.target).entries());
  $("#login-erro").hidden = true;
  try {
    const r = await api("/auth/login-json", { method: "POST", body: JSON.stringify({ email: d.email, senha: d.senha }) });
    token = r.access_token; user = r.usuario;
    localStorage.setItem("esus_token", token);
    localStorage.setItem("esus_user", JSON.stringify(user));
    iniciar();
  } catch (err) { $("#login-erro").textContent = err.message; $("#login-erro").hidden = false; }
};
function sair() {
  token = user = null;
  localStorage.removeItem("esus_token"); localStorage.removeItem("esus_user");
  $("#app").hidden = true; $("#login").hidden = false;
}
$("#sair").onclick = sair;

// ───────── navegação ─────────
const MENU = [
  { v: "painel", t: "Painel", p: "*" },
  { v: "agenda", t: "Agenda", p: ["RECEPCAO", "ENFERMEIRO", "MEDICO"] },
  { v: "fila", t: "Atendimento do dia", p: ["MEDICO", "ENFERMEIRO", "RECEPCAO"] },
  { v: "retornos", t: "Retornos", p: ["RECEPCAO", "ENFERMEIRO", "MEDICO"] },
  { v: "cidadaos", t: "Pacientes", p: ["RECEPCAO", "ENFERMEIRO", "MEDICO"] },
  { v: "financeiro", t: "Financeiro", p: ["RECEPCAO", "ADMIN"] },
  { v: "estoque", t: "Estoque", p: ["RECEPCAO", "ENFERMEIRO", "ADMIN"] },
  { v: "convenios", t: "Convênios", p: ["RECEPCAO", "ADMIN"] },
  { v: "relatorios", t: "Relatórios", p: ["MEDICO", "ENFERMEIRO"] },
  { v: "unidades", t: "Unidades", p: ["ADMIN"] },
  { v: "usuarios", t: "Usuários", p: ["ADMIN"] },
];
const pode = (m) => m.p === "*" || user.perfil === "ADMIN" || m.p.includes(user.perfil);
const views = {};
const viewEl = $("#view");

function setView(v, arg) {
  const m = MENU.find((x) => x.v === v);
  if (m && !pode(m)) v = "painel";
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.v === v));
  (views[v] || views.painel)(arg);
}
function iniciar() {
  $("#login").hidden = true; $("#app").hidden = false;
  $("#user-info").innerHTML = `${esc(user.nome)} · <span class="badge">${user.perfil}</span>`;
  const nav = $("#nav"); nav.innerHTML = "";
  MENU.filter(pode).forEach((m) => {
    const b = el(`<button class="nav-item" data-v="${m.v}">${m.t}</button>`);
    b.onclick = () => setView(m.v);
    nav.appendChild(b);
  });
  setView("fila");
}

// ═════════ PAINEL ═════════
views.painel = async () => {
  viewEl.innerHTML = `<div class="page-head"><h1 class="title">Painel</h1></div><div id="pc"></div>`;
  try {
    const d = await api("/painel");
    const cards = [
      ["Agendamentos hoje", d.agendamentos_hoje],
      ["Aguardando", d.aguardando],
      ["Sem acolhimento", d.em_acolhimento_pendente],
      ["Em atendimento", d.em_atendimento],
      ["Finalizados hoje", d.finalizados_hoje],
      ["Retornos (7 dias)", d.retornos_7dias],
      ["Faturamento hoje", "R$ " + d.faturamento_hoje.toFixed(2).replace(".", ",")],
      ["Itens em estoque baixo", d.estoque_baixo],
      ["Pacientes cadastrados", d.cidadaos],
    ];
    $("#pc").innerHTML = `<div class="cards">
      ${cards.map(([k, v]) => `<div class="card"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("")}
    </div>
    ${(d.producao_hoje || []).length ? `<div class="panel"><h3>Produção de hoje</h3>
      <table><tbody>${d.producao_hoje.map((p) => `<tr><td>${esc(p.profissional)}</td><td><b>${p.total}</b> atendimento(s)</td></tr>`).join("")}</tbody></table></div>` : ""}`;
  } catch (e) { $("#pc").innerHTML = `<p class="empty">${e.message}</p>`; }
};

// ═════════ CIDADÃOS ═════════
views.cidadaos = async () => {
  const editar = ["RECEPCAO", "ENFERMEIRO"].includes(user.perfil) || user.perfil === "ADMIN";
  viewEl.innerHTML = `
    <div class="page-head"><h1 class="title">Pacientes</h1>
      ${editar ? '<button class="btn" id="novo">+ Novo paciente</button>' : ""}</div>
    <div class="panel"><input id="busca" placeholder="Buscar por nome, CPF ou CNS…" style="max-width:340px"/></div>
    <div class="panel" id="lista"></div>`;
  const carregar = async (q = "") => {
    const l = await api("/cidadaos" + (q ? `?q=${encodeURIComponent(q)}` : ""));
    const box = $("#lista"); box.innerHTML = "";
    if (!l.length) return (box.innerHTML = '<p class="empty">Nenhum paciente.</p>');
    const t = el(`<table><thead><tr><th>Nome</th><th>Idade</th><th>CPF</th><th>Convênio</th><th></th></tr></thead><tbody></tbody></table>`);
    l.forEach((c) => {
      const tr = el(`<tr><td><b>${esc(c.nome_social || c.nome_completo)}</b>${c.nome_social ? "<br><span class='muted'>" + esc(c.nome_completo) + "</span>" : ""}</td>
        <td>${c.idade ?? "-"}</td><td>${esc(c.cpf || "-")}</td>
        <td>${c.convenio ? esc(c.convenio.nome) : '<span class="muted">Particular</span>'}</td><td class="row-actions"></td></tr>`);
      const ficha = el('<button class="btn small sec">Ficha</button>'); ficha.onclick = () => fichaCidadao(c.id);
      $(".row-actions", tr).appendChild(ficha);
      if (editar) { const e = el('<button class="btn small sec">Editar</button>'); e.onclick = () => cidadaoForm(c, () => carregar($("#busca").value)); $(".row-actions", tr).appendChild(e); }
      t.querySelector("tbody").appendChild(tr);
    });
    box.appendChild(t);
  };
  let d; $("#busca").oninput = (e) => { clearTimeout(d); d = setTimeout(() => carregar(e.target.value), 250); };
  if ($("#novo")) $("#novo").onclick = () => cidadaoForm(null, carregar);
  carregar();
};

async function cidadaoForm(c, reload) {
  const convenios = await api("/convenios").catch(() => []);
  const values = c ? { ...c, convenio_id: c.convenio ? c.convenio.id : "" } : {};
  formModal({
    title: c ? "Editar paciente" : "Novo paciente",
    values,
    fields: [
      { name: "nome_completo", label: "Nome completo", required: true, full: true },
      { name: "nome_social", label: "Nome social" },
      { name: "cpf", label: "CPF (só números)" },
      { name: "cns", label: "CNS" },
      { name: "data_nascimento", label: "Nascimento", type: "date", required: true },
      { name: "sexo", label: "Sexo", type: "select", options: [{ value: "F", label: "Feminino" }, { value: "M", label: "Masculino" }, { value: "I", label: "Não informado" }] },
      { name: "nome_mae", label: "Nome da mãe", full: true },
      { name: "telefone", label: "Telefone" },
      { name: "endereco", label: "Endereço", full: true },
      { name: "convenio_id", label: "Convênio", type: "select",
        options: [{ value: "", label: "— Particular —" }, ...convenios.map((v) => ({ value: v.id, label: v.nome }))] },
      { name: "numero_carteirinha", label: "Nº da carteirinha" },
    ],
    onSubmit: async (d) => {
      if (c) await api(`/cidadaos/${c.id}`, { method: "PUT", body: JSON.stringify(d) });
      else await api("/cidadaos", { method: "POST", body: JSON.stringify(d) });
      toast("Paciente salvo"); reload();
    },
  });
}

async function fichaCidadao(cid) {
  const [c, alergias, meds, atends] = await Promise.all([
    api(`/cidadaos/${cid}`), api(`/cidadaos/${cid}/alergias`), api(`/cidadaos/${cid}/medicamentos`),
    api(`/atendimentos?cidadao_id=${cid}`),
  ]);
  const clinico = ["MEDICO", "ENFERMEIRO"].includes(user.perfil);
  const w = el(`<div>
    <p class="muted">${c.idade} anos · ${c.sexo} · nasc. ${fmtD(c.data_nascimento)} · CPF ${esc(c.cpf || "-")} · CNS ${esc(c.cns || "-")}</p>
    <h3>Alergias</h3><div id="fc-al"></div>
    ${clinico ? '<button class="btn small" id="fc-al-add" style="margin:6px 0">+ Alergia</button>' : ""}
    <h3 style="margin-top:14px">Medicamentos em uso</h3><div id="fc-md"></div>
    ${clinico ? '<button class="btn small" id="fc-md-add" style="margin:6px 0">+ Medicamento</button>' : ""}
    <h3 style="margin-top:14px">Linha do tempo (${atends.length})</h3><div id="fc-tl"></div>
  </div>`);
  const pinta = () => {
    $("#fc-al", w).innerHTML = alergias.length ? alergias.map((a) =>
      `<div class="alerta-vermelho">${esc(a.substancia)} · ${a.gravidade}${a.reacao ? " · " + esc(a.reacao) : ""}</div>`).join("") : '<p class="muted">Nenhuma.</p>';
    $("#fc-md", w).innerHTML = meds.length ? "<ul>" + meds.map((m) =>
      `<li>${esc(m.descricao)}${m.posologia ? " — " + esc(m.posologia) : ""}</li>`).join("") + "</ul>" : '<p class="muted">Nenhum.</p>';
  };
  pinta();
  const tl = $("#fc-tl", w);
  if (!atends.length) tl.innerHTML = '<p class="muted">Nenhum atendimento.</p>';
  atends.forEach((a) => {
    const it = el(`<div style="border-left:3px solid var(--border);padding:4px 0 4px 10px;margin:4px 0;cursor:pointer">
      <span class="muted">${fmtD(a.fim_atendimento || a.criado_em)}</span> · ${stBadge(a.status)}
      ${a.desfecho ? "· " + esc(a.desfecho.replace(/_/g, " ")) : ""} <span class="muted">${esc(a.profissional ? "· " + a.profissional.nome : "")}</span></div>`);
    if (a.status === "FINALIZADO") it.onclick = () => verAtendimento(a.id);
    tl.appendChild(it);
  });
  openModal("Ficha — " + (c.nome_social || c.nome_completo), w);
  if (clinico) {
    $("#fc-al-add", w).onclick = () => formModal({
      title: "Registrar alergia",
      fields: [
        { name: "substancia", label: "Substância", required: true, full: true },
        { name: "categoria", label: "Categoria", type: "select", options: ["MEDICAMENTO", "ALIMENTO", "AMBIENTAL", "OUTRO"].map((v) => ({ value: v, label: v })) },
        { name: "gravidade", label: "Gravidade", type: "select", options: ["LEVE", "MODERADA", "GRAVE"].map((v) => ({ value: v, label: v })), default: "MODERADA" },
        { name: "reacao", label: "Reação observada", full: true },
      ],
      onSubmit: async (d) => { const n = await api(`/cidadaos/${cid}/alergias`, { method: "POST", body: JSON.stringify(d) }); alergias.unshift(n); pinta(); toast("Alergia registrada"); },
    });
    $("#fc-md-add", w).onclick = () => formModal({
      title: "Medicamento em uso",
      fields: [
        { name: "descricao", label: "Medicamento", required: true, full: true },
        { name: "posologia", label: "Posologia", full: true },
        { name: "via", label: "Via" },
        { name: "uso_continuo", label: "Uso contínuo", type: "select", options: [{ value: "true", label: "Sim" }, { value: "false", label: "Não" }] },
      ],
      onSubmit: async (d) => { d.uso_continuo = d.uso_continuo === "true"; const n = await api(`/cidadaos/${cid}/medicamentos`, { method: "POST", body: JSON.stringify(d) }); meds.unshift(n); pinta(); toast("Medicamento adicionado"); },
    });
  }
}

// ═════════ USUÁRIOS ═════════
views.usuarios = async () => {
  viewEl.innerHTML = `<div class="page-head"><h1 class="title">Usuários</h1><button class="btn" id="novo">+ Novo</button></div><div class="panel" id="lista"></div>`;
  const carregar = async () => {
    const l = await api("/usuarios");
    const t = el(`<table><thead><tr><th>Nome</th><th>E-mail</th><th>Perfil</th><th>Unidade</th><th>Conselho</th><th>Ativo</th><th></th></tr></thead><tbody></tbody></table>`);
    l.forEach((u) => {
      const tr = el(`<tr><td>${esc(u.nome)}</td><td>${esc(u.email)}</td><td><span class="badge">${u.perfil}</span></td>
        <td>${u.unidade ? esc(u.unidade.nome) : '<span class="muted">—</span>'}</td>
        <td>${esc(u.conselho || "-")}</td><td>${u.ativo ? "sim" : "não"}</td><td></td></tr>`);
      const e = el('<button class="btn small sec">Editar</button>'); e.onclick = () => usuarioForm(u, carregar);
      tr.lastElementChild.appendChild(e); t.querySelector("tbody").appendChild(tr);
    });
    $("#lista").innerHTML = ""; $("#lista").appendChild(t);
  };
  $("#novo").onclick = () => usuarioForm(null, carregar);
  carregar();
};
async function usuarioForm(u, reload) {
  const unidades = await api("/unidades").catch(() => []);
  const values = u ? { ...u, unidade_id: u.unidade ? u.unidade.id : "" } : {};
  formModal({
    title: u ? "Editar usuário" : "Novo usuário",
    values,
    fields: [
      { name: "nome", label: "Nome", required: true, full: true },
      { name: "email", label: "E-mail", type: "email", required: !u },
      { name: "perfil", label: "Perfil", type: "select", required: true, options: ["MEDICO", "ENFERMEIRO", "RECEPCAO", "ADMIN"].map((v) => ({ value: v, label: v })) },
      { name: "senha", label: u ? "Nova senha (vazio = manter)" : "Senha", type: "password", required: !u },
      { name: "conselho", label: "Conselho (CRM/COREN)" },
      { name: "cbo", label: "CBO" },
      { name: "cns", label: "CNS profissional" },
      { name: "unidade_id", label: "Unidade", type: "select",
        options: [{ value: "", label: "— todas / não definida —" }, ...unidades.map((un) => ({ value: un.id, label: un.nome }))] },
      ...(u ? [{ name: "ativo", label: "Ativo", type: "select", options: [{ value: "true", label: "Sim" }, { value: "false", label: "Não" }] }] : []),
    ],
    onSubmit: async (d) => {
      if (d.ativo !== undefined) d.ativo = d.ativo === "true";
      if (u && !d.senha) delete d.senha;
      if (u) await api(`/usuarios/${u.id}`, { method: "PUT", body: JSON.stringify(d) });
      else await api("/usuarios", { method: "POST", body: JSON.stringify(d) });
      toast("Usuário salvo"); reload();
    },
  });
}
