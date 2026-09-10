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
const fmtD = (i) => i ? new Date(i).toLocaleDateString("pt-BR") : "-";
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

// abre o documento (receita/atestado/exames) numa aba nova e manda imprimir
async function imprimir(atId, tipo) {
  try {
    const { html } = await api(`/atendimentos/${atId}/documento/${tipo}`);
    const w = window.open("", "_blank");
    if (!w) return toast("Permita pop-ups para imprimir", true);
    w.document.open(); w.document.write(html); w.document.close();
  } catch (e) { toast(e.message, true); }
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
  { v: "fila", t: "Atendimento do dia", p: ["MEDICO", "ENFERMEIRO", "RECEPCAO"] },
  { v: "cidadaos", t: "Cidadãos", p: ["RECEPCAO", "ENFERMEIRO", "MEDICO"] },
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
    $("#pc").innerHTML = `<div class="cards">
      ${[["Aguardando", d.aguardando], ["Em atendimento", d.em_atendimento],
         ["Finalizados hoje", d.finalizados_hoje], ["Cidadãos", d.cidadaos]]
        .map(([k, v]) => `<div class="card"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("")}
    </div>`;
  } catch (e) { $("#pc").innerHTML = `<p class="empty">${e.message}</p>`; }
};

// ═════════ PASSO 1 — FILA ═════════
views.fila = async () => {
  const clinico = ["MEDICO", "ENFERMEIRO"].includes(user.perfil);
  const recep = ["RECEPCAO", "ENFERMEIRO"].includes(user.perfil);
  viewEl.innerHTML = `
    <div class="page-head"><h1 class="title">Atendimento do dia</h1>
      ${recep ? '<button class="btn" id="add">+ Adicionar à fila</button>' : ""}</div>
    <div class="panel" id="lista"></div>`;
  const carregar = async () => {
    const fila = await api("/fila");
    const box = $("#lista"); box.innerHTML = "";
    if (!fila.length) return (box.innerHTML = '<p class="empty">Ninguém aguardando atendimento.</p>');
    const t = el(`<table><thead><tr><th>Risco</th><th>Cidadão</th><th>Idade</th><th>Motivo / queixa</th><th>Status</th><th>Chegada</th><th></th></tr></thead><tbody></tbody></table>`);
    fila.forEach((a) => {
      const c = a.cidadao || {};
      const tr = el(`<tr>
        <td>${risco(a.classificacao_risco)}</td>
        <td><b>${esc(c.nome_social || c.nome_completo)}</b></td>
        <td>${c.idade ?? "-"}${c.sexo ? " · " + c.sexo : ""}</td>
        <td>${esc(a.motivo || "-")}</td>
        <td>${stBadge(a.status)}${a.profissional ? "<br><span class='muted'>" + esc(a.profissional.nome) + "</span>" : ""}</td>
        <td>${fmtDT(a.criado_em)}</td>
        <td class="row-actions"></td></tr>`);
      const acts = $(".row-actions", tr);
      if (clinico) {
        const b = el(`<button class="btn small">${a.status === "EM_ATENDIMENTO" ? "Continuar" : "Atender"}</button>`);
        b.onclick = async () => {
          try { await api(`/fila/${a.id}/atender`, { method: "POST" }); setView("atendimento", a.id); }
          catch (e) { toast(e.message, true); }
        };
        acts.appendChild(b);
      }
      if (recep && a.status === "AGUARDANDO") {
        const x = el('<button class="btn small sec">Remover</button>');
        x.onclick = async () => { if (!confirm("Remover da fila?")) return; await api(`/fila/${a.id}/cancelar`, { method: "POST" }); carregar(); };
        acts.appendChild(x);
      }
      t.querySelector("tbody").appendChild(tr);
    });
    box.appendChild(t);
  };
  if ($("#add")) $("#add").onclick = () => filaForm(carregar);
  carregar();
};

async function filaForm(reload) {
  const cids = await api("/cidadaos");
  formModal({
    title: "Adicionar cidadão à fila",
    fields: [
      { name: "cidadao_id", label: "Cidadão", required: true, type: "select", full: true,
        options: cids.map((c) => ({ value: c.id, label: `${c.nome_completo}${c.cpf ? " — " + c.cpf : ""}` })) },
      { name: "tipo", label: "Tipo", type: "select", options: ["CONSULTA", "RETORNO", "URGENCIA", "PROCEDIMENTO"].map((v) => ({ value: v, label: v })) },
      { name: "classificacao_risco", label: "Classificação de risco", type: "select",
        options: [{ value: "", label: "— não classificado —" }, ...["AZUL", "VERDE", "AMARELO", "LARANJA", "VERMELHO"].map((v) => ({ value: v, label: v }))] },
      { name: "motivo", label: "Motivo / queixa (acolhimento)", type: "textarea", full: true },
    ],
    onSubmit: async (d) => { await api("/fila", { method: "POST", body: JSON.stringify(d) }); toast("Adicionado à fila"); reload(); },
  });
}

// ═════════ PASSOS 2–5 — ATENDIMENTO ═════════
views.atendimento = async (aid) => {
  let at;
  try { at = await api(`/atendimentos/${aid}`); }
  catch (e) { toast(e.message, true); return setView("fila"); }
  const bloqueado = at.assinado || at.status === "FINALIZADO";
  const meu = !at.profissional || at.profissional.id === user.id;
  const editavel = !bloqueado && meu && ["MEDICO", "ENFERMEIRO"].includes(user.perfil);
  const c = at.cidadao || {};

  viewEl.innerHTML = `
    <div class="page-head">
      <div><h1 class="title">${esc(c.nome_social || c.nome_completo)}</h1>
        <span class="muted">${c.idade ?? "?"} anos · ${c.sexo || "-"} · nasc. ${fmtD(c.data_nascimento)} · ${stBadge(at.status)}
        ${at.assinado ? "· <b style='color:var(--ok)'>assinado ✔</b>" : ""}</span></div>
      <button class="btn sec" id="voltar">← Voltar à fila</button>
    </div>
    <div id="alertas"></div>
    <details class="panel" id="fr-panel" open><summary style="cursor:pointer;font-weight:600">Passo 2 — Folha de rosto</summary><div id="fr" style="margin-top:12px">carregando…</div></details>
    <div class="panel"><h3>Passo 3 — Registro clínico (SOAP)</h3><div id="soap"></div></div>
    <div class="panel"><h3>Passo 4 — Prescrição e documentos</h3><div id="docs"></div></div>
    <div class="panel" id="fim-panel"><h3>Passo 5 — Finalização</h3><div id="fim"></div></div>`;
  $("#voltar").onclick = () => setView("fila");

  renderFolhaRosto(aid);
  renderSoap(at, editavel);
  renderDocs(at, editavel);
  renderFinalizar(at, editavel);
};

async function renderFolhaRosto(aid) {
  const fr = await api(`/atendimentos/${aid}/folha-rosto`);
  // alertas de alergia em vermelho
  const al = $("#alertas"); al.innerHTML = "";
  fr.alergias.forEach((a) => al.appendChild(el(
    `<div class="alerta-vermelho">⚠️ <b>ALERGIA — ${esc(a.substancia)}</b> · ${a.gravidade}${a.reacao ? " · " + esc(a.reacao) : ""}</div>`)));
  if (!fr.alergias.length) al.appendChild(el('<div class="muted" style="margin-bottom:8px">Sem alergias registradas.</div>'));

  const box = $("#fr");
  box.innerHTML = `<div class="grid2">
    <div><h3>Medicamentos em uso</h3><div id="fr-med"></div></div>
    <div><h3>Consultas anteriores</h3><div id="fr-hist"></div></div>
  </div><div id="fr-graf" style="margin-top:14px"></div>`;

  $("#fr-med").innerHTML = fr.medicamentos_ativos.length
    ? "<ul>" + fr.medicamentos_ativos.map((m) => `<li><b>${esc(m.descricao)}</b>${m.posologia ? " — " + esc(m.posologia) : ""}</li>`).join("") + "</ul>"
    : '<p class="muted">Nenhum.</p>';

  $("#fr-hist").innerHTML = fr.consultas_anteriores.length
    ? fr.consultas_anteriores.map((h) => `<div style="border-bottom:1px solid var(--border);padding:6px 0">
        <div class="muted">${fmtD(h.criado_em)} · ${esc(h.profissional ? h.profissional.nome : "")}</div>
        ${esc((h.desfecho || "").replace(/_/g, " "))}</div>`).join("")
    : '<p class="muted">Primeira consulta registrada.</p>';

  const g = $("#fr-graf");
  const pa = fr.evolucao.filter((s) => s.tipo.startsWith("PA_"));
  const peso = fr.evolucao.find((s) => s.tipo === "PESO");
  const imc = fr.evolucao.find((s) => s.tipo === "IMC");
  const glic = fr.evolucao.find((s) => s.tipo === "GLICEMIA");
  if (pa.length) g.appendChild(lineChart("Pressão arterial (mmHg)", pa));
  const outras = [peso, imc, glic].filter(Boolean);
  outras.forEach((s) => g.appendChild(lineChart(s.tipo.replace(/_/g, " ") + " (" + s.unidade + ")", [s])));
  if (!pa.length && !outras.length) g.innerHTML = '<p class="muted">Sem medições para gráfico de evolução.</p>';
}

function renderSoap(at, editavel) {
  const box = $("#soap");
  const dis = editavel ? "" : "disabled";
  box.innerHTML = `<div class="soap">
    <div class="soap-bloco S"><h3><span class="soap-tag">S</span> Subjetivo</h3>
      <textarea id="s_sub" ${dis} placeholder="Queixa principal, história da doença atual, relato do cidadão…">${esc(at.subjetivo || "")}</textarea></div>
    <div class="soap-bloco O"><h3><span class="soap-tag">O</span> Objetivo</h3>
      <div class="grid4" style="margin-bottom:10px">
        <div><label class="fld">PA sistólica</label><input id="v_pas" type="number" ${dis} placeholder="mmHg"/></div>
        <div><label class="fld">PA diastólica</label><input id="v_pad" type="number" ${dis} placeholder="mmHg"/></div>
        <div><label class="fld">Peso</label><input id="v_peso" type="number" step="0.1" ${dis} placeholder="kg"/></div>
        <div><label class="fld">Altura</label><input id="v_alt" type="number" ${dis} placeholder="cm"/></div>
        <div><label class="fld">Temperatura</label><input id="v_temp" type="number" step="0.1" ${dis} placeholder="°C"/></div>
        <div><label class="fld">FC</label><input id="v_fc" type="number" ${dis} placeholder="bpm"/></div>
        <div><label class="fld">SatO₂</label><input id="v_sat" type="number" ${dis} placeholder="%"/></div>
        <div><label class="fld">Glicemia</label><input id="v_glic" type="number" ${dis} placeholder="mg/dL"/></div>
      </div>
      <textarea id="s_obj" ${dis} placeholder="Exame físico, achados objetivos…">${esc(at.objetivo || "")}</textarea></div>
    <div class="soap-bloco A"><h3><span class="soap-tag">A</span> Avaliação</h3>
      <div id="probs" class="pill-list" style="margin-bottom:8px"></div>
      ${editavel ? '<div id="cid-ac" style="margin-bottom:6px"></div><div id="ciap-ac" style="margin-bottom:8px"></div>' : ""}
      <textarea id="s_ava" ${dis} placeholder="Diagnóstico, hipóteses, avaliação clínica…">${esc(at.avaliacao || "")}</textarea></div>
    <div class="soap-bloco P"><h3><span class="soap-tag">P</span> Plano</h3>
      <textarea id="s_pla" ${dis} placeholder="Conduta, orientações ao cidadão, plano terapêutico…">${esc(at.plano || "")}</textarea></div>
    ${editavel ? '<div><button class="btn" id="salvar-soap">Salvar registro clínico</button> <span class="muted" id="soap-status"></span></div>' : ""}
  </div>`;

  const renderProbs = () => {
    const p = $("#probs"); p.innerHTML = "";
    (at.problemas || []).forEach((pr) => {
      const pill = el(`<span class="pill">${pr.sistema} ${esc(pr.codigo)} — ${esc(pr.descricao)}</span>`);
      if (editavel) {
        const b = el("<button>×</button>");
        b.onclick = async () => { await api(`/atendimentos/${at.id}/problemas/${pr.id}`, { method: "DELETE" }); at.problemas = at.problemas.filter((x) => x.id !== pr.id); renderProbs(); };
        pill.appendChild(b);
      }
      p.appendChild(pill);
    });
  };
  renderProbs();

  if (editavel) {
    const addProb = async (sistema, it) => {
      const novo = await api(`/atendimentos/${at.id}/problemas`, {
        method: "POST", body: JSON.stringify({ sistema, codigo: it.codigo, descricao: it.descricao }),
      });
      at.problemas.push(novo); renderProbs();
    };
    $("#cid-ac").appendChild(autocomplete("/catalogo/cid10", "Buscar CID-10…", (it) => addProb("CID10", it)));
    $("#ciap-ac").appendChild(autocomplete("/catalogo/ciap2", "Buscar CIAP-2…", (it) => addProb("CIAP2", it)));

    $("#salvar-soap").onclick = async () => {
      const num = (id) => { const v = $(id).value; return v === "" ? null : Number(v); };
      const body = {
        subjetivo: $("#s_sub").value || null, objetivo: $("#s_obj").value || null,
        avaliacao: $("#s_ava").value || null, plano: $("#s_pla").value || null,
        pa_sistolica: num("#v_pas"), pa_diastolica: num("#v_pad"), peso: num("#v_peso"),
        altura: num("#v_alt"), temperatura: num("#v_temp"), freq_cardiaca: num("#v_fc"),
        saturacao: num("#v_sat"), glicemia: num("#v_glic"),
      };
      try {
        const r = await api(`/atendimentos/${at.id}/soap`, { method: "PUT", body: JSON.stringify(body) });
        Object.assign(at, r);
        $("#soap-status").textContent = "salvo " + new Date().toLocaleTimeString("pt-BR");
        toast("Registro clínico salvo");
        renderFolhaRosto(at.id);
      } catch (e) { toast(e.message, true); }
    };
  }
}

function renderDocs(at, editavel) {
  const box = $("#docs");
  box.innerHTML = `<div class="tabs">
      <button class="tab active" data-t="presc">Prescrição</button>
      <button class="tab" data-t="atest">Atestado</button>
      <button class="tab" data-t="exame">Exames</button>
    </div><div id="doc-body"></div>`;
  const tabs = box.querySelectorAll(".tab");
  const show = (t) => {
    tabs.forEach((b) => b.classList.toggle("active", b.dataset.t === t));
    ({ presc: docPresc, atest: docAtest, exame: docExame }[t])(at, editavel);
  };
  tabs.forEach((b) => (b.onclick = () => show(b.dataset.t)));
  show("presc");
}

function docPresc(at, editavel) {
  const b = $("#doc-body"); b.innerHTML = "";
  const lista = el("<div></div>");
  const pinta = () => {
    lista.innerHTML = (at.prescricoes || []).length ? "" : '<p class="muted">Nenhum medicamento prescrito.</p>';
    (at.prescricoes || []).forEach((p) => {
      const row = el(`<div style="border-bottom:1px solid var(--border);padding:8px 0">
        <b>${esc(p.medicamento)}</b> — ${esc(p.posologia)} ${p.quantidade ? "· " + esc(p.quantidade) : ""} ${p.uso_continuo ? "· <span class='badge'>uso contínuo</span>" : ""}</div>`);
      if (editavel) { const x = el('<button class="btn small danger" style="margin-left:8px">remover</button>');
        x.onclick = async () => { await api(`/atendimentos/${at.id}/prescricoes/${p.id}`, { method: "DELETE" }); at.prescricoes = at.prescricoes.filter((y) => y.id !== p.id); pinta(); };
        row.appendChild(x); }
      lista.appendChild(row);
    });
  };
  pinta(); b.appendChild(lista);
  if ((at.prescricoes || []).length) {
    const pr = el('<button class="btn sec small" style="margin-top:10px">🖨️ Imprimir receita</button>');
    pr.onclick = () => imprimir(at.id, "receita");
    b.appendChild(pr);
  }
  if (!editavel) return;
  const form = el(`<div class="grid3" style="margin-top:12px">
    <div class="full" id="med-ac"></div>
    <div><label class="fld">Medicamento *</label><input id="p_med"/></div>
    <div><label class="fld">Posologia *</label><input id="p_pos" placeholder="1 comp 12/12h por 7 dias"/></div>
    <div><label class="fld">Quantidade</label><input id="p_qtd" placeholder="14 comprimidos"/></div>
    <div><label class="fld">Via</label><input id="p_via" placeholder="oral"/></div>
    <div><label class="fld">Duração (dias)</label><input id="p_dur" type="number"/></div>
    <div><label class="fld">Uso contínuo</label><select id="p_cont"><option value="false">Não</option><option value="true">Sim</option></select></div>
    <div class="full"><button class="btn" id="p_add">Adicionar à receita</button></div>
  </div>`);
  b.appendChild(form);
  $("#med-ac").appendChild(autocomplete("/catalogo/medicamentos", "Buscar na farmácia municipal…", (it) => { $("#p_med").value = it.nome; }));
  $("#p_add").onclick = async () => {
    const body = { medicamento: $("#p_med").value, posologia: $("#p_pos").value, quantidade: $("#p_qtd").value || null,
      via: $("#p_via").value || null, duracao_dias: $("#p_dur").value ? Number($("#p_dur").value) : null,
      uso_continuo: $("#p_cont").value === "true" };
    if (!body.medicamento || !body.posologia) return toast("Informe medicamento e posologia", true);
    try { const novo = await api(`/atendimentos/${at.id}/prescricoes`, { method: "POST", body: JSON.stringify(body) });
      at.prescricoes.push(novo); pinta();
      ["#p_med", "#p_pos", "#p_qtd", "#p_via", "#p_dur"].forEach((s) => ($(s).value = ""));
      toast("Adicionado à receita");
    } catch (e) { toast(e.message, true); }
  };
}

function docAtest(at, editavel) {
  const b = $("#doc-body"); b.innerHTML = "";
  (at.atestados || []).forEach((a) => b.appendChild(el(`<div class="doc-preview" style="margin-bottom:10px">${esc(a.texto)}</div>`)));
  if (!(at.atestados || []).length) b.appendChild(el('<p class="muted">Nenhum atestado emitido.</p>'));
  if ((at.atestados || []).length) {
    const pr = el('<button class="btn sec small">🖨️ Imprimir atestado</button>');
    pr.onclick = () => imprimir(at.id, "atestado");
    b.appendChild(pr);
  }
  if (!editavel) return;
  const form = el(`<div class="grid3" style="margin-top:12px">
    <div><label class="fld">Tipo</label><select id="a_tipo"><option value="COMPARECIMENTO">Comparecimento</option><option value="AFASTAMENTO">Afastamento</option></select></div>
    <div><label class="fld">Dias de afastamento</label><input id="a_dias" type="number"/></div>
    <div><label class="fld">CID (opcional)</label><input id="a_cid"/></div>
    <div><label class="fld">Data início</label><input id="a_ini" type="date" value="${hojeInput()}"/></div>
    <div class="full"><button class="btn" id="a_add">Emitir atestado</button> <span class="muted">o texto é gerado automaticamente</span></div>
  </div>`);
  b.appendChild(form);
  $("#a_add").onclick = async () => {
    const body = { tipo: $("#a_tipo").value, dias_afastamento: $("#a_dias").value ? Number($("#a_dias").value) : null,
      cid: $("#a_cid").value || null, data_inicio: $("#a_ini").value || null };
    try { const novo = await api(`/atendimentos/${at.id}/atestados`, { method: "POST", body: JSON.stringify(body) });
      at.atestados.push(novo); docAtest(at, editavel); toast("Atestado emitido");
    } catch (e) { toast(e.message, true); }
  };
}

function docExame(at, editavel) {
  const b = $("#doc-body"); b.innerHTML = "";
  (at.solicitacoes_exame || []).forEach((s) => b.appendChild(el(
    `<div class="doc-preview" style="margin-bottom:10px"><b>${s.prioridade}</b>\n${esc(s.exames)}${s.indicacao_clinica ? "\n\nIndicação: " + esc(s.indicacao_clinica) : ""}</div>`)));
  if (!(at.solicitacoes_exame || []).length) b.appendChild(el('<p class="muted">Nenhuma solicitação.</p>'));
  if ((at.solicitacoes_exame || []).length) {
    const pr = el('<button class="btn sec small">🖨️ Imprimir solicitação</button>');
    pr.onclick = () => imprimir(at.id, "exames");
    b.appendChild(pr);
  }
  if (!editavel) return;
  const form = el(`<div style="margin-top:12px">
    <div id="ex-ac"></div>
    <label class="fld" style="margin-top:8px">Exames solicitados (um por linha) *</label>
    <textarea id="e_lista" style="min-height:90px"></textarea>
    <div class="grid2" style="margin-top:8px">
      <div><label class="fld">Indicação clínica</label><input id="e_ind"/></div>
      <div><label class="fld">Prioridade</label><select id="e_pri"><option value="ROTINA">Rotina</option><option value="URGENTE">Urgente</option></select></div>
    </div>
    <button class="btn" id="e_add" style="margin-top:10px">Gerar solicitação</button>
  </div>`);
  b.appendChild(form);
  $("#ex-ac").appendChild(autocomplete("/catalogo/exames", "Buscar exame do SUS…", (it) => {
    $("#e_lista").value += (($("#e_lista").value && !$("#e_lista").value.endsWith("\n")) ? "\n" : "") + it.nome + "\n";
  }));
  $("#e_add").onclick = async () => {
    if (!$("#e_lista").value.trim()) return toast("Liste ao menos um exame", true);
    try {
      const novo = await api(`/atendimentos/${at.id}/exames`, { method: "POST", body: JSON.stringify({
        exames: $("#e_lista").value.trim(), indicacao_clinica: $("#e_ind").value || null, prioridade: $("#e_pri").value }) });
      at.solicitacoes_exame.push(novo); docExame(at, editavel); toast("Solicitação gerada");
    } catch (e) { toast(e.message, true); }
  };
}

function renderFinalizar(at, editavel) {
  const box = $("#fim");
  if (at.assinado || at.status === "FINALIZADO") {
    box.innerHTML = `<div class="doc-preview">Atendimento finalizado em ${fmtDT(at.fim_atendimento)}.
Desfecho: <b>${(at.desfecho || "").replace(/_/g, " ")}</b>${at.retorno_data ? " · retorno " + fmtD(at.retorno_data) : ""}
${at.desfecho_obs ? "\n" + esc(at.desfecho_obs) : ""}
Assinado por ${esc(at.profissional ? at.profissional.nome : "")} em ${fmtDT(at.assinado_em)}.</div>`;
    return;
  }
  if (!editavel) { box.innerHTML = '<p class="muted">Somente o profissional responsável finaliza o atendimento.</p>'; return; }
  box.innerHTML = `<div class="grid2">
    <div><label class="fld">Desfecho *</label><select id="f_des">
      <option value="ALTA">Alta do episódio</option>
      <option value="RETORNO_AGENDADO">Retorno agendado</option>
      <option value="ENCAMINHAMENTO">Encaminhamento para especialista</option>
      <option value="ENCAMINHAMENTO_URGENCIA">Encaminhamento — urgência/emergência</option>
      <option value="OBSERVACAO">Manter em observação</option></select></div>
    <div id="f_ret_w" hidden><label class="fld">Data do retorno</label><input id="f_ret" type="date"/></div>
    <div class="full" id="f_enc_w" hidden>
      <div class="grid3">
        <div><label class="fld">Especialidade</label><input id="f_esp"/></div>
        <div><label class="fld">Prioridade</label><select id="f_pri"><option>ROTINA</option><option>PRIORITARIO</option><option>URGENTE</option></select></div>
        <div class="full"><label class="fld">Motivo do encaminhamento</label><textarea id="f_mot"></textarea></div>
      </div></div>
    <div class="full"><label class="fld">Observações / orientações finais</label><textarea id="f_obs"></textarea></div>
    <div class="full"><button class="btn ok" id="f_fim">Finalizar atendimento e assinar</button></div>
  </div>`;
  const sync = () => {
    const v = $("#f_des").value;
    $("#f_ret_w").hidden = v !== "RETORNO_AGENDADO";
    $("#f_enc_w").hidden = !v.startsWith("ENCAMINHAMENTO");
  };
  $("#f_des").onchange = sync; sync();
  $("#f_fim").onclick = async () => {
    const v = $("#f_des").value;
    const body = { desfecho: v, desfecho_obs: $("#f_obs").value || null,
      retorno_data: v === "RETORNO_AGENDADO" ? ($("#f_ret").value || null) : null,
      encaminhamento_especialidade: v.startsWith("ENCAMINHAMENTO") ? $("#f_esp").value : null,
      encaminhamento_motivo: v.startsWith("ENCAMINHAMENTO") ? $("#f_mot").value : null,
      encaminhamento_prioridade: v.startsWith("ENCAMINHAMENTO") ? $("#f_pri").value : "ROTINA" };
    if (!confirm("Finalizar e assinar? O prontuário ficará bloqueado para edição.")) return;
    try {
      await api(`/atendimentos/${at.id}/finalizar`, { method: "POST", body: JSON.stringify(body) });
      toast("Atendimento finalizado e assinado");
      setView("fila");
    } catch (e) { toast(e.message, true); }
  };
}

// ═════════ CIDADÃOS ═════════
views.cidadaos = async () => {
  const editar = ["RECEPCAO", "ENFERMEIRO"].includes(user.perfil) || user.perfil === "ADMIN";
  viewEl.innerHTML = `
    <div class="page-head"><h1 class="title">Cidadãos</h1>
      ${editar ? '<button class="btn" id="novo">+ Novo cidadão</button>' : ""}</div>
    <div class="panel"><input id="busca" placeholder="Buscar por nome, CPF ou CNS…" style="max-width:340px"/></div>
    <div class="panel" id="lista"></div>`;
  const carregar = async (q = "") => {
    const l = await api("/cidadaos" + (q ? `?q=${encodeURIComponent(q)}` : ""));
    const box = $("#lista"); box.innerHTML = "";
    if (!l.length) return (box.innerHTML = '<p class="empty">Nenhum cidadão.</p>');
    const t = el(`<table><thead><tr><th>Nome</th><th>Idade</th><th>CPF</th><th>CNS</th><th></th></tr></thead><tbody></tbody></table>`);
    l.forEach((c) => {
      const tr = el(`<tr><td><b>${esc(c.nome_social || c.nome_completo)}</b>${c.nome_social ? "<br><span class='muted'>" + esc(c.nome_completo) + "</span>" : ""}</td>
        <td>${c.idade ?? "-"}</td><td>${esc(c.cpf || "-")}</td><td>${esc(c.cns || "-")}</td><td class="row-actions"></td></tr>`);
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

function cidadaoForm(c, reload) {
  formModal({
    title: c ? "Editar cidadão" : "Novo cidadão",
    values: c || {},
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
    ],
    onSubmit: async (d) => {
      if (c) await api(`/cidadaos/${c.id}`, { method: "PUT", body: JSON.stringify(d) });
      else await api("/cidadaos", { method: "POST", body: JSON.stringify(d) });
      toast("Cidadão salvo"); reload();
    },
  });
}

async function fichaCidadao(cid) {
  const [c, alergias, meds] = await Promise.all([
    api(`/cidadaos/${cid}`), api(`/cidadaos/${cid}/alergias`), api(`/cidadaos/${cid}/medicamentos`),
  ]);
  const clinico = ["MEDICO", "ENFERMEIRO"].includes(user.perfil);
  const w = el(`<div>
    <p class="muted">${c.idade} anos · ${c.sexo} · nasc. ${fmtD(c.data_nascimento)} · CPF ${esc(c.cpf || "-")}</p>
    <h3>Alergias</h3><div id="fc-al"></div>
    ${clinico ? '<button class="btn small" id="fc-al-add" style="margin:6px 0">+ Alergia</button>' : ""}
    <h3 style="margin-top:14px">Medicamentos em uso</h3><div id="fc-md"></div>
    ${clinico ? '<button class="btn small" id="fc-md-add" style="margin:6px 0">+ Medicamento</button>' : ""}
  </div>`);
  const pinta = () => {
    $("#fc-al", w).innerHTML = alergias.length ? alergias.map((a) =>
      `<div class="alerta-vermelho">${esc(a.substancia)} · ${a.gravidade}${a.reacao ? " · " + esc(a.reacao) : ""}</div>`).join("") : '<p class="muted">Nenhuma.</p>';
    $("#fc-md", w).innerHTML = meds.length ? "<ul>" + meds.map((m) =>
      `<li>${esc(m.descricao)}${m.posologia ? " — " + esc(m.posologia) : ""}</li>`).join("") + "</ul>" : '<p class="muted">Nenhum.</p>';
  };
  pinta();
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
    const t = el(`<table><thead><tr><th>Nome</th><th>E-mail</th><th>Perfil</th><th>Conselho</th><th>Ativo</th><th></th></tr></thead><tbody></tbody></table>`);
    l.forEach((u) => {
      const tr = el(`<tr><td>${esc(u.nome)}</td><td>${esc(u.email)}</td><td><span class="badge">${u.perfil}</span></td>
        <td>${esc(u.conselho || "-")}</td><td>${u.ativo ? "sim" : "não"}</td><td></td></tr>`);
      const e = el('<button class="btn small sec">Editar</button>'); e.onclick = () => usuarioForm(u, carregar);
      tr.lastElementChild.appendChild(e); t.querySelector("tbody").appendChild(tr);
    });
    $("#lista").innerHTML = ""; $("#lista").appendChild(t);
  };
  $("#novo").onclick = () => usuarioForm(null, carregar);
  carregar();
};
function usuarioForm(u, reload) {
  formModal({
    title: u ? "Editar usuário" : "Novo usuário",
    values: u || {},
    fields: [
      { name: "nome", label: "Nome", required: true, full: true },
      { name: "email", label: "E-mail", type: "email", required: !u },
      { name: "perfil", label: "Perfil", type: "select", required: true, options: ["MEDICO", "ENFERMEIRO", "RECEPCAO", "ADMIN"].map((v) => ({ value: v, label: v })) },
      { name: "senha", label: u ? "Nova senha (vazio = manter)" : "Senha", type: "password", required: !u },
      { name: "conselho", label: "Conselho (CRM/COREN)" },
      { name: "cbo", label: "CBO" },
      { name: "cns", label: "CNS profissional" },
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

// boot
if (token && user) iniciar();
