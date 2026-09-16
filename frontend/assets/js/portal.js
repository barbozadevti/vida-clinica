// ═════════════════════════════════════════════════════════════
// PORTAL DO PACIENTE — Onda 4 (Lean Inception). Mini-app independente
// do sistema da equipe: login por CPF + data de nascimento (sem senha),
// acesso somente-leitura aos próprios agendamentos e documentos.
// ═════════════════════════════════════════════════════════════
const API = "/api";
let token = localStorage.getItem("portal_token") || null;
let paciente = JSON.parse(localStorage.getItem("portal_paciente") || "null");

const $ = (s, e = document) => e.querySelector(s);
const el = (h) => { const t = document.createElement("template"); t.innerHTML = h.trim(); return t.content.firstElementChild; };
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmtD = (i) => {
  if (!i) return "-";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(i);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : new Date(i).toLocaleDateString("pt-BR");
};
const fmtDT = (i) => i ? new Date(i).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "-";

async function api(path, opt = {}) {
  const h = { "Content-Type": "application/json", ...(opt.headers || {}) };
  if (token) h.Authorization = `Bearer ${token}`;
  const r = await fetch(API + path, { cache: "no-store", ...opt, headers: h });
  if (r.status === 401) { sair(); throw new Error("Sessão expirada. Entre novamente."); }
  const d = await r.json().catch(() => null);
  if (!r.ok) { const m = d && d.detail; throw new Error(typeof m === "string" ? m : `Erro ${r.status}`); }
  return d;
}

function toast(msg, err = false) {
  const t = $("#toast"); t.textContent = msg; t.classList.toggle("err", err); t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 3800);
}

async function baixarDocumento(atId, tipo, rotulo) {
  try {
    const r = await fetch(`${API}/portal/atendimentos/${atId}/pdf/${tipo}`, { headers: { Authorization: `Bearer ${token}` } });
    if (!r.ok) { const d = await r.json().catch(() => null); throw new Error((d && d.detail) || `Erro ${r.status}`); }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  } catch (e) { toast(e.message, true); }
}

$("#portal-login-form").onsubmit = async (e) => {
  e.preventDefault();
  const d = Object.fromEntries(new FormData(e.target).entries());
  $("#login-erro").hidden = true;
  try {
    const r = await api("/portal/entrar", { method: "POST", body: JSON.stringify(d) });
    token = r.access_token; paciente = r.paciente;
    localStorage.setItem("portal_token", token);
    localStorage.setItem("portal_paciente", JSON.stringify(paciente));
    iniciar();
  } catch (err) { $("#login-erro").textContent = err.message; $("#login-erro").hidden = false; }
};
function sair() {
  token = paciente = null;
  localStorage.removeItem("portal_token"); localStorage.removeItem("portal_paciente");
  $("#app").hidden = true; $("#login").hidden = false;
}
$("#sair").onclick = sair;

async function iniciar() {
  $("#login").hidden = true; $("#app").hidden = false;
  $("#user-info").textContent = paciente.nome_social || paciente.nome_completo;
  const view = $("#view");
  view.innerHTML = '<p class="muted">Carregando…</p>';
  try {
    const d = await api("/portal/mim");
    const ag = d.proximos_agendamentos, at = d.atendimentos_anteriores;
    view.innerHTML = `
      <div class="panel">
        <h3>Meus dados</h3>
        <p class="muted">${d.paciente.idade} anos · nasc. ${fmtD(d.paciente.data_nascimento)}
        ${d.paciente.convenio ? " · Convênio: " + esc(d.paciente.convenio.nome) : " · Particular"}</p>
      </div>
      <div class="panel">
        <h3>Próximos agendamentos</h3>
        <div id="p-ag">${ag.length ? "" : '<p class="empty">Nenhum agendamento futuro.</p>'}</div>
      </div>
      <div class="panel">
        <h3>Atendimentos anteriores</h3>
        <div id="p-at">${at.length ? "" : '<p class="empty">Nenhum atendimento finalizado ainda.</p>'}</div>
      </div>`;
    const boxAg = $("#p-ag");
    ag.forEach((a) => {
      boxAg.appendChild(el(`<div class="doc-card">
        <b>${fmtD(a.data)} às ${esc(a.hora)}</b> — ${esc((a.tipo || "").replace(/_/g, " "))}<br>
        <span class="muted">${a.profissional ? esc(a.profissional.nome) : ""} · ${esc(a.status)}</span>
        ${a.tipo === "TELECONSULTA" ? `<br><a href="https://meet.jit.si/VidaClinica-${a.id}" target="_blank">🎥 Entrar na videochamada</a>` : ""}
      </div>`));
    });
    const boxAt = $("#p-at");
    at.forEach((a) => {
      const card = el(`<div class="doc-card">
        <b>${fmtDT(a.fim_atendimento || a.criado_em)}</b> — ${esc(a.profissional ? a.profissional.nome : "")}<br>
        <span class="muted">Desfecho: ${esc((a.desfecho || "-").replace(/_/g, " "))}</span>
        <div class="row-actions" style="margin-top:8px"></div>
      </div>`);
      const acts = $(".row-actions", card);
      acts.appendChild(el('<button class="btn small sec">Resumo</button>')).onclick = () => baixarDocumento(a.id, "resumo");
      if (a.tem_receita) acts.appendChild(el('<button class="btn small sec">Receita</button>')).onclick = () => baixarDocumento(a.id, "receita");
      if (a.tem_atestado) acts.appendChild(el('<button class="btn small sec">Atestado</button>')).onclick = () => baixarDocumento(a.id, "atestado");
      if (a.tem_exames) acts.appendChild(el('<button class="btn small sec">Exames</button>')).onclick = () => baixarDocumento(a.id, "exames");
      boxAt.appendChild(card);
    });
  } catch (e) { view.innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
}

if (token && paciente) iniciar();
