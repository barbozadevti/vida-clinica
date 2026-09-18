// ═════════════════════════════════════════════════════════════
// PRONTUÁRIO — MVP 1 da Lean Inception (10/09): fila, acolhimento,
// folha de rosto, SOAP, documentos e finalização do atendimento.
// Depende dos utilitários definidos em core.js.
// ═════════════════════════════════════════════════════════════

// abre o documento numa aba nova e manda imprimir
async function imprimir(atId, tipo) {
  try {
    const { html } = await api(`/atendimentos/${atId}/documento/${tipo}`);
    const w = window.open("", "_blank");
    if (!w) return toast("Permita pop-ups para imprimir", true);
    w.document.open(); w.document.write(html); w.document.close();
  } catch (e) { toast(e.message, true); }
}

// baixa o PDF do documento
async function baixarPdf(atId, tipo) {
  try {
    const r = await fetch(`${API}/atendimentos/${atId}/pdf/${tipo}`, { headers: { Authorization: `Bearer ${token}` } });
    if (!r.ok) { const d = await r.json().catch(() => null); throw new Error((d && d.detail) || `Erro ${r.status}`); }
    const blob = await r.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${tipo}.pdf`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  } catch (e) { toast(e.message, true); }
}

// par de botões Imprimir + PDF
function botoesDoc(atId, tipo, rotulo) {
  const w = el('<span class="row-actions" style="display:inline-flex;margin-right:6px"></span>');
  const i = el(`<button class="btn sec small">🖨️ ${rotulo}</button>`); i.onclick = () => imprimir(atId, tipo);
  const p = el('<button class="btn sec small">PDF</button>'); p.onclick = () => baixarPdf(atId, tipo);
  w.append(i, p);
  return w;
}

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
    const t = el(`<table><thead><tr><th>Risco</th><th>Paciente</th><th>Idade</th><th>Motivo / queixa</th><th>Acolh.</th><th>Status</th><th>Chegada</th><th></th></tr></thead><tbody></tbody></table>`);
    fila.forEach((a) => {
      const c = a.cidadao || {};
      const tr = el(`<tr>
        <td>${risco(a.classificacao_risco) || '<span class="badge">sem risco</span>'}</td>
        <td><b>${esc(c.nome_social || c.nome_completo)}</b></td>
        <td>${c.idade ?? "-"}${c.sexo ? " · " + c.sexo : ""}</td>
        <td>${esc(a.motivo || "-")}</td>
        <td>${a.acolhido_em ? "✔️" : '<span class="muted">—</span>'}</td>
        <td>${stBadge(a.status)}${a.profissional ? "<br><span class='muted'>" + esc(a.profissional.nome) + "</span>" : ""}</td>
        <td>${fmtDT(a.criado_em)}</td>
        <td class="row-actions"></td></tr>`);
      const acts = $(".row-actions", tr);
      if (user.perfil === "ENFERMEIRO" && a.status === "AGUARDANDO") {
        const ac = el(`<button class="btn small sec">${a.acolhido_em ? "Rever acolhimento" : "Acolhimento"}</button>`);
        ac.onclick = () => acolhimentoForm(a, carregar);
        acts.appendChild(ac);
      }
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
    title: "Adicionar paciente à fila",
    fields: [
      { name: "cidadao_id", label: "Paciente", required: true, type: "select", full: true,
        options: cids.map((c) => ({ value: c.id, label: `${c.nome_completo}${c.cpf ? " — " + c.cpf : ""}` })) },
      { name: "tipo", label: "Tipo", type: "select", options: ["CONSULTA", "RETORNO", "URGENCIA", "PROCEDIMENTO", "TELECONSULTA"].map((v) => ({ value: v, label: v })) },
      { name: "classificacao_risco", label: "Classificação de risco (opcional — a enfermagem pode fazer)", type: "select", full: true,
        options: [{ value: "", label: "— será classificado no acolhimento —" }, ...["AZUL", "VERDE", "AMARELO", "LARANJA", "VERMELHO"].map((v) => ({ value: v, label: v }))] },
      { name: "motivo", label: "Motivo / queixa", type: "textarea", full: true },
    ],
    onSubmit: async (d) => { await api("/fila", { method: "POST", body: JSON.stringify(d) }); toast("Adicionado à fila"); reload(); },
  });
}

// Acolhimento / pré-consulta da enfermagem
function acolhimentoForm(a, reload) {
  const w = el(`<form class="grid4">
    <div class="full"><label class="fld">Classificação de risco (Manchester) *</label>
      <select name="classificacao_risco" required>
        ${["AZUL","VERDE","AMARELO","LARANJA","VERMELHO"].map((v) => `<option value="${v}"${a.classificacao_risco === v ? " selected" : ""}>${v}</option>`).join("")}
      </select></div>
    <div><label class="fld">PA sistólica</label><input name="pa_sistolica" type="number" placeholder="mmHg"/></div>
    <div><label class="fld">PA diastólica</label><input name="pa_diastolica" type="number" placeholder="mmHg"/></div>
    <div><label class="fld">Temperatura</label><input name="temperatura" type="number" step="0.1" placeholder="°C"/></div>
    <div><label class="fld">FC</label><input name="freq_cardiaca" type="number" placeholder="bpm"/></div>
    <div><label class="fld">FR</label><input name="freq_respiratoria" type="number" placeholder="irpm"/></div>
    <div><label class="fld">SatO₂</label><input name="saturacao" type="number" placeholder="%"/></div>
    <div><label class="fld">Peso</label><input name="peso" type="number" step="0.1" placeholder="kg"/></div>
    <div><label class="fld">Altura</label><input name="altura" type="number" placeholder="cm"/></div>
    <div><label class="fld">Glicemia</label><input name="glicemia" type="number" placeholder="mg/dL"/></div>
    <div class="full"><label class="fld">Queixa / motivo</label><input name="motivo" value="${esc(a.motivo || "")}"/></div>
    <div class="full"><label class="fld">Anotação do acolhimento</label><textarea name="anotacao">${esc(a.acolhimento || "")}</textarea></div>
    <div class="modal-actions full"><button type="button" class="btn sec" id="ac-cancel">Cancelar</button><button type="submit" class="btn">Salvar acolhimento</button></div>
  </form>`);
  $("#ac-cancel", w).onclick = closeModal;
  w.onsubmit = async (e) => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(w).entries());
    ["pa_sistolica","pa_diastolica","temperatura","freq_cardiaca","freq_respiratoria","saturacao","peso","altura","glicemia"]
      .forEach((k) => { d[k] = d[k] === "" ? null : Number(d[k]); });
    Object.keys(d).forEach((k) => { if (d[k] === "") d[k] = null; });
    try { await api(`/fila/${a.id}/acolhimento`, { method: "POST", body: JSON.stringify(d) }); toast("Acolhimento registrado"); closeModal(); reload(); }
    catch (err) { toast(err.message, true); }
  };
  openModal("Acolhimento — " + (a.cidadao.nome_social || a.cidadao.nome_completo), w);
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

  const podeReabrir = bloqueado && user.perfil === "ADMIN";
  viewEl.innerHTML = `
    <div class="page-head">
      <div><h1 class="title">${esc(c.nome_social || c.nome_completo)}</h1>
        <span class="muted">${c.idade ?? "?"} anos · ${c.sexo || "-"} · nasc. ${fmtD(c.data_nascimento)} · ${stBadge(at.status)}
        ${at.assinado ? "· <b style='color:var(--ok)'>assinado ✔</b>" : ""}</span></div>
      <div class="row-actions">
        ${at.tipo === "TELECONSULTA" ? '<button class="btn ok" id="teleconsulta">🎥 Videochamada</button>' : ""}
        ${podeReabrir ? '<button class="btn sec" id="reabrir">Reabrir atendimento</button>' : ""}
        <button class="btn sec" id="voltar">← Voltar</button>
      </div>
    </div>
    ${at.tipo === "TELECONSULTA" ? `
    <div class="panel" id="video-panel" hidden style="position:sticky;top:8px;z-index:5;padding:10px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <b>🎥 Videochamada — fica aberta enquanto você preenche o prontuário abaixo</b>
        <div class="row-actions">
          <a href="https://meet.jit.si/VidaClinica-${aid}" target="_blank" class="btn sec small">Tela cheia (nova aba)</a>
          <button class="btn sec small" id="fechar-video">Fechar</button>
        </div>
      </div>
      <iframe id="video-iframe" style="width:100%;height:380px;border:1px solid var(--border);border-radius:8px"
        allow="camera; microphone; fullscreen; display-capture; autoplay"></iframe>
    </div>` : ""}
    ${at.acolhido_em ? `<div class="panel" style="background:#f0f7ff"><b>Acolhimento</b> — ${esc(at.acolhido_por ? at.acolhido_por.nome : "")} em ${fmtDT(at.acolhido_em)}${at.acolhimento ? "<br>" + esc(at.acolhimento) : ""}</div>` : ""}
    <div id="alertas"></div>
    <details class="panel" id="fr-panel" open><summary style="cursor:pointer;font-weight:600">Passo 2 — Folha de rosto</summary><div id="fr" style="margin-top:12px">carregando…</div></details>
    <div class="panel"><h3>Passo 3 — Registro clínico (SOAP)</h3><div id="soap"></div></div>
    <div class="panel"><h3>Passo 4 — Prescrição e documentos</h3><div id="docs"></div></div>
    <div class="panel" id="fim-panel"><h3>Passo 5 — Finalização</h3><div id="fim"></div></div>`;
  $("#voltar").onclick = () => setView("fila");
  if ($("#teleconsulta")) $("#teleconsulta").onclick = () => {
    const painel = $("#video-panel"), frame = $("#video-iframe");
    painel.hidden = false;
    if (!frame.src) frame.src = `https://meet.jit.si/VidaClinica-${aid}#config.prejoinPageEnabled=false`;
    painel.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  if ($("#fechar-video")) $("#fechar-video").onclick = () => { $("#video-panel").hidden = true; };
  if ($("#reabrir")) $("#reabrir").onclick = async () => {
    const motivo = prompt("Motivo da reabertura:");
    if (!motivo) return;
    try { await api(`/atendimentos/${aid}/reabrir`, { method: "POST", body: JSON.stringify({ motivo }) }); toast("Atendimento reaberto"); views.atendimento(aid); }
    catch (e) { toast(e.message, true); }
  };

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

  const hist = $("#fr-hist");
  if (!fr.consultas_anteriores.length) hist.innerHTML = '<p class="muted">Primeira consulta registrada.</p>';
  else fr.consultas_anteriores.forEach((h) => {
    const item = el(`<div style="border-bottom:1px solid var(--border);padding:6px 0;cursor:pointer">
      <div class="muted">${fmtD(h.fim_atendimento || h.criado_em)} · ${esc(h.profissional ? h.profissional.nome : "")}</div>
      ${esc((h.desfecho || "").replace(/_/g, " "))} <span class="muted">— ver</span></div>`);
    item.onclick = () => verAtendimento(h.id);
    hist.appendChild(item);
  });

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
  const va = at.vitais_acolhimento || {};
  const pv = (t) => (t in va ? ` value="${va[t]}"` : "");
  const nota = Object.keys(va).length && !at.subjetivo
    ? '<div class="muted" style="font-size:12px;margin-bottom:6px">Sinais vitais preenchidos a partir do acolhimento — ajuste se reaferir.</div>' : "";
  box.innerHTML = `<div class="soap">
    <div class="soap-bloco S"><h3><span class="soap-tag">S</span> Subjetivo</h3>
      <textarea id="s_sub" ${dis} placeholder="Queixa principal, história da doença atual, relato do paciente…">${esc(at.subjetivo || "")}</textarea></div>
    <div class="soap-bloco O"><h3><span class="soap-tag">O</span> Objetivo</h3>
      ${nota}
      <div class="grid4" style="margin-bottom:10px">
        <div><label class="fld">PA sistólica</label><input id="v_pas" type="number" ${dis}${pv("PA_SISTOLICA")} placeholder="mmHg"/></div>
        <div><label class="fld">PA diastólica</label><input id="v_pad" type="number" ${dis}${pv("PA_DIASTOLICA")} placeholder="mmHg"/></div>
        <div><label class="fld">Peso</label><input id="v_peso" type="number" step="0.1" ${dis}${pv("PESO")} placeholder="kg"/></div>
        <div><label class="fld">Altura</label><input id="v_alt" type="number" ${dis}${pv("ALTURA")} placeholder="cm"/></div>
        <div><label class="fld">Temperatura</label><input id="v_temp" type="number" step="0.1" ${dis}${pv("TEMPERATURA")} placeholder="°C"/></div>
        <div><label class="fld">FC</label><input id="v_fc" type="number" ${dis}${pv("FC")} placeholder="bpm"/></div>
        <div><label class="fld">SatO₂</label><input id="v_sat" type="number" ${dis}${pv("SATO2")} placeholder="%"/></div>
        <div><label class="fld">Glicemia</label><input id="v_glic" type="number" ${dis}${pv("GLICEMIA")} placeholder="mg/dL"/></div>
      </div>
      <textarea id="s_obj" ${dis} placeholder="Exame físico, achados objetivos…">${esc(at.objetivo || "")}</textarea></div>
    <div class="soap-bloco A"><h3><span class="soap-tag">A</span> Avaliação</h3>
      <div id="probs" class="pill-list" style="margin-bottom:8px"></div>
      ${editavel ? `<div id="cid-ac" style="margin-bottom:6px"></div><div id="ciap-ac" style="margin-bottom:8px"></div>
        <div style="display:flex;gap:6px;margin-bottom:8px">
          <input id="prob-livre" placeholder="ou digite um diagnóstico sem código…" style="flex:1"/>
          <button type="button" class="btn small sec" id="prob-livre-add">Adicionar</button>
        </div>` : ""}
      <textarea id="s_ava" ${dis} placeholder="Diagnóstico, hipóteses, avaliação clínica…">${esc(at.avaliacao || "")}</textarea></div>
    <div class="soap-bloco P"><h3><span class="soap-tag">P</span> Plano</h3>
      <textarea id="s_pla" ${dis} placeholder="Conduta, orientações ao paciente, plano terapêutico…">${esc(at.plano || "")}</textarea></div>
    ${editavel ? '<div><button class="btn" id="salvar-soap">Salvar registro clínico</button> <span class="muted" id="soap-status"></span></div>' : ""}
  </div>`;

  const renderProbs = () => {
    const p = $("#probs"); p.innerHTML = "";
    (at.problemas || []).forEach((pr) => {
      const pill = el(`<span class="pill">${pr.sistema}${pr.codigo ? " " + esc(pr.codigo) : ""} — ${esc(pr.descricao)}</span>`);
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
    $("#prob-livre-add").onclick = () => {
      const texto = $("#prob-livre").value.trim();
      if (!texto) return;
      addProb("LIVRE", { codigo: null, descricao: texto });
      $("#prob-livre").value = "";
    };

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
  const montaImpressao = () => {
    const imp = $("#presc-imp");
    if (!imp) return;
    imp.innerHTML = "";
    const todas = at.prescricoes || [];
    const simples = todas.filter((p) => !p.controle_especial);
    const controle = todas.filter((p) => p.controle_especial);
    if (simples.length) imp.appendChild(botoesDoc(at.id, "receita-simples", "Receita simples"));
    if (controle.length) imp.appendChild(botoesDoc(at.id, "receita-controle", "Receita de controle especial"));
  };
  const pinta = () => {
    lista.innerHTML = (at.prescricoes || []).length ? "" : '<p class="muted">Nenhum medicamento prescrito.</p>';
    (at.prescricoes || []).forEach((p) => {
      const row = el(`<div style="border-bottom:1px solid var(--border);padding:8px 0">
        <b>${esc(p.medicamento)}</b> — ${esc(p.posologia)} ${p.quantidade ? "· " + esc(p.quantidade) : ""} ${p.uso_continuo ? "· <span class='badge'>uso contínuo</span>" : ""} ${p.controle_especial ? "· <span class='badge' style='background:#b91c1c'>controle especial</span>" : ""}</div>`);
      if (editavel) { const x = el('<button class="btn small danger" style="margin-left:8px">remover</button>');
        x.onclick = async () => { await api(`/atendimentos/${at.id}/prescricoes/${p.id}`, { method: "DELETE" }); at.prescricoes = at.prescricoes.filter((y) => y.id !== p.id); docPresc(at, editavel); };
        row.appendChild(x); }
      lista.appendChild(row);
    });
    montaImpressao();
  };
  pinta(); b.appendChild(lista);
  b.appendChild(el('<div id="presc-imp" style="margin-top:10px"></div>'));
  montaImpressao();
  if (!editavel) return;
  const form = el(`<div class="grid3" style="margin-top:12px">
    <div class="full">
      <div class="tabs" style="margin-bottom:8px">
        <button type="button" class="tab active" id="p_tab_catalogo">Catálogo do SUS</button>
        <button type="button" class="tab" id="p_tab_livre">Nome livre</button>
      </div>
      <div id="med-ac"></div>
      <p id="med-livre-dica" class="muted" style="display:none;margin:0 0 10px">
        Digite qualquer medicamento no campo "Medicamento" abaixo — não precisa estar na lista do SUS.</p>
      <div id="p_sug_wrap" style="display:none;background:var(--accent-wash,#eef2f7);border-radius:8px;padding:8px 10px;margin:0 0 10px">
        <span class="muted" style="font-size:12.5px">Sugestão de posologia para este medicamento: <b id="p_sug_texto"></b></span>
        <button type="button" class="btn small sec" id="p_sug_usar" style="margin-left:8px">Usar esta</button>
      </div>
    </div>
    <div><label class="fld">Medicamento *</label><input id="p_med"/></div>
    <div><label class="fld">Posologia *</label><input id="p_pos" placeholder="ex.: 1 comp 12/12h por 7 dias"/></div>
    <div><label class="fld">Quantidade</label><input id="p_qtd" placeholder="ex.: 14 comprimidos"/></div>
    <div><label class="fld">Via</label><input id="p_via" placeholder="ex.: oral"/></div>
    <div><label class="fld">Duração (dias)</label><input id="p_dur" type="number"/></div>
    <div><label class="fld">Uso contínuo</label><select id="p_cont"><option value="false">Não</option><option value="true">Sim</option></select></div>
    <div><label class="fld">Receita</label><select id="p_controle">
      <option value="false">Simples</option>
      <option value="true">Controle especial (Portaria 344)</option>
    </select></div>
    <div class="full"><button class="btn" id="p_add">Adicionar à receita</button></div>
  </div>`);
  b.appendChild(form);
  $("#med-ac").appendChild(autocomplete("/catalogo/medicamentos", "Buscar no catálogo do SUS…", (it) => {
    $("#p_med").value = it.nome;
    // sugestão de posologia ao lado, pra aplicar com um clique — vale para
    // qualquer medicamento do catálogo, em qualquer especialidade
    if (it.posologia_usual) {
      $("#p_sug_texto").textContent = it.posologia_usual;
      $("#p_sug_wrap").style.display = "";
    } else {
      $("#p_sug_wrap").style.display = "none";
    }
  }));
  $("#p_sug_usar").onclick = () => { $("#p_pos").value = $("#p_sug_texto").textContent; };
  $("#p_tab_catalogo").onclick = () => {
    $("#p_tab_catalogo").classList.add("active"); $("#p_tab_livre").classList.remove("active");
    $("#med-ac").style.display = ""; $("#med-livre-dica").style.display = "none";
  };
  $("#p_tab_livre").onclick = () => {
    $("#p_tab_livre").classList.add("active"); $("#p_tab_catalogo").classList.remove("active");
    $("#med-ac").style.display = "none"; $("#med-livre-dica").style.display = "";
    $("#p_med").focus();
  };
  $("#p_add").onclick = async () => {
    const body = { medicamento: $("#p_med").value, posologia: $("#p_pos").value, quantidade: $("#p_qtd").value || null,
      via: $("#p_via").value || null, duracao_dias: $("#p_dur").value ? Number($("#p_dur").value) : null,
      uso_continuo: $("#p_cont").value === "true", controle_especial: $("#p_controle").value === "true" };
    if (!body.medicamento || !body.posologia) return toast("Informe medicamento e posologia", true);
    try { const novo = await api(`/atendimentos/${at.id}/prescricoes`, { method: "POST", body: JSON.stringify(body) });
      at.prescricoes.push(novo); docPresc(at, editavel);
      toast("Adicionado à receita");
    } catch (e) { toast(e.message, true); }
  };
}

function docAtest(at, editavel) {
  const b = $("#doc-body"); b.innerHTML = "";
  (at.atestados || []).forEach((a) => b.appendChild(el(`<div class="doc-preview" style="margin-bottom:10px">${esc(a.texto)}</div>`)));
  if (!(at.atestados || []).length) b.appendChild(el('<p class="muted">Nenhum atestado emitido.</p>'));
  if ((at.atestados || []).length) b.appendChild(botoesDoc(at.id, "atestado", "Imprimir atestado"));
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
  if ((at.solicitacoes_exame || []).length) b.appendChild(botoesDoc(at.id, "exames", "Imprimir requisição"));
  if (!editavel) return;
  const form = el(`<div style="margin-top:12px">
    <div id="ex-ac"></div>
    <p class="muted" style="font-size:12.5px;margin:4px 0 0">A busca acima é só um atalho — pode digitar
      qualquer exame direto na caixa abaixo, não precisa estar na lista do SUS.</p>
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

function botoesImpressao(at) {
  const wrap = el('<div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:6px"></div>');
  wrap.appendChild(botoesDoc(at.id, "resumo", "Resumo"));
  const presc = at.prescricoes || [];
  if (presc.some((p) => !p.controle_especial)) wrap.appendChild(botoesDoc(at.id, "receita-simples", "Receita simples"));
  if (presc.some((p) => p.controle_especial)) wrap.appendChild(botoesDoc(at.id, "receita-controle", "Receita controle especial"));
  if ((at.atestados || []).length) wrap.appendChild(botoesDoc(at.id, "atestado", "Atestado"));
  if ((at.solicitacoes_exame || []).length) wrap.appendChild(botoesDoc(at.id, "exames", "Requisição de exames"));
  if ((at.encaminhamentos || []).length) wrap.appendChild(botoesDoc(at.id, "encaminhamento", "Guia de encaminhamento"));
  return wrap;
}

function renderFinalizar(at, editavel) {
  const box = $("#fim");
  if (at.assinado || at.status === "FINALIZADO") {
    box.innerHTML = `<div class="doc-preview">Atendimento finalizado em ${fmtDT(at.fim_atendimento)}.
Desfecho: <b>${(at.desfecho || "").replace(/_/g, " ")}</b>${at.retorno_data ? " · retorno " + fmtD(at.retorno_data) : ""}
${at.desfecho_obs ? "\n" + esc(at.desfecho_obs) : ""}
Assinado por ${esc(at.profissional ? at.profissional.nome : "")} em ${fmtDT(at.assinado_em)}.</div>`;
    box.appendChild(botoesImpressao(at));
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
        <div><label class="fld">Tipo</label><select id="f_tipo">
          <option value="CONSULTA_ESPECIALIZADA">Consulta com especialista</option>
          <option value="AVALIACAO_CIRURGICA">Avaliação / procedimento cirúrgico</option>
          <option value="EXAMES_ESPECIALIZADOS">Exames especializados</option>
          <option value="URGENCIA">Urgência / emergência</option></select></div>
        <div><label class="fld">Especialidade / serviço</label><input id="f_esp" placeholder="ex.: Ortopedia / Coluna"/></div>
        <div><label class="fld">Prioridade</label><select id="f_pri"><option>ROTINA</option><option>PRIORITARIO</option><option>URGENTE</option></select></div>
        <div class="full" id="f_cid-ac"></div>
        <div class="full"><label class="fld">CID</label><input id="f_cid" placeholder="vazio = usa os CIDs da avaliação"/></div>
        <div class="full"><label class="fld">Motivo / resumo clínico</label><textarea id="f_mot"></textarea></div>
      </div></div>
    <div class="full"><label class="fld">Observações / orientações finais</label><textarea id="f_obs"></textarea></div>
    <div class="full"><button class="btn ok" id="f_fim">Finalizar atendimento e assinar</button></div>
  </div>`;
  box.appendChild(botoesImpressao(at));
  const sync = () => {
    const v = $("#f_des").value;
    $("#f_ret_w").hidden = v !== "RETORNO_AGENDADO";
    $("#f_enc_w").hidden = !v.startsWith("ENCAMINHAMENTO");
  };
  $("#f_des").onchange = sync; sync();
  $("#f_cid-ac").appendChild(autocomplete("/catalogo/cid10", "Buscar CID-10…", (it) => { $("#f_cid").value = `${it.codigo} — ${it.descricao}`; }));
  $("#f_fim").onclick = async () => {
    const v = $("#f_des").value;
    const enc = v.startsWith("ENCAMINHAMENTO");
    const body = { desfecho: v, desfecho_obs: $("#f_obs").value || null,
      retorno_data: v === "RETORNO_AGENDADO" ? ($("#f_ret").value || null) : null,
      encaminhamento_tipo: enc ? $("#f_tipo").value : "CONSULTA_ESPECIALIZADA",
      encaminhamento_especialidade: enc ? $("#f_esp").value : null,
      encaminhamento_cid: enc ? ($("#f_cid").value || null) : null,
      encaminhamento_motivo: enc ? $("#f_mot").value : null,
      encaminhamento_prioridade: enc ? $("#f_pri").value : "ROTINA" };
    if (!confirm("Finalizar e assinar? O prontuário ficará bloqueado para edição.")) return;
    try {
      await api(`/atendimentos/${at.id}/finalizar`, { method: "POST", body: JSON.stringify(body) });
      toast("Atendimento finalizado e assinado");
      setView("fila");
    } catch (e) { toast(e.message, true); }
  };
}

// visualização somente-leitura de um atendimento (histórico) — permite
// reimprimir qualquer documento já emitido e, se o paciente pedir depois,
// emitir um atestado retroativo (o prontuário em si continua travado)
async function verAtendimento(id) {
  const at = await api(`/atendimentos/${id}`);
  const probs = (at.problemas || []).map((p) => `${p.sistema}${p.codigo ? " " + esc(p.codigo) : ""} — ${esc(p.descricao)}`).join("<br>") || "—";
  const presc = (at.prescricoes || []).map((p) => `${esc(p.medicamento)} — ${esc(p.posologia)}`).join("<br>") || "—";
  const w = el(`<div>
    <p class="muted">${fmtDT(at.fim_atendimento || at.criado_em)} · ${esc(at.profissional ? at.profissional.nome : "")} · desfecho: <b>${esc((at.desfecho || "-").replace(/_/g, " "))}</b></p>
    <div class="soap-bloco S"><b>S</b> ${esc(at.subjetivo || "—")}</div>
    <div class="soap-bloco O" style="margin-top:8px"><b>O</b> ${esc(at.objetivo || "—")}</div>
    <div class="soap-bloco A" style="margin-top:8px"><b>A</b><br>${probs}<br>${esc(at.avaliacao || "")}</div>
    <div class="soap-bloco P" style="margin-top:8px"><b>P</b> ${esc(at.plano || "—")}</div>
    <p style="margin-top:10px"><b>Prescrição:</b><br>${presc}</p>
    <div id="va-imp"></div>
  </div>`);
  $("#va-imp", w).appendChild(botoesImpressao(at));

  if (["MEDICO", "ENFERMEIRO"].includes(user.perfil)) {
    const dataAtendimento = (at.fim_atendimento || at.criado_em || "").slice(0, 10) || hojeInput();
    const box = el(`<div class="panel" style="margin-top:14px;padding:12px">
      <h3 style="margin:0 0 8px">Emitir atestado</h3>
      <p class="muted" style="font-size:12.5px;margin:0 0 8px">
        Para quando o paciente volta pedindo um atestado depois que o atendimento já foi finalizado.</p>
      <div class="grid3">
        <div><label class="fld">Tipo</label><select id="va_tipo">
          <option value="COMPARECIMENTO">Comparecimento</option><option value="AFASTAMENTO">Afastamento</option></select></div>
        <div><label class="fld">Dias de afastamento</label><input id="va_dias" type="number"/></div>
        <div><label class="fld">CID (opcional)</label><input id="va_cid"/></div>
        <div><label class="fld">Data início</label><input id="va_ini" type="date" value="${dataAtendimento}"/></div>
        <div class="full"><button class="btn" id="va_add">Emitir atestado</button></div>
      </div>
    </div>`);
    w.appendChild(box);
    $("#va_add", box).onclick = async () => {
      const body = {
        tipo: $("#va_tipo", box).value,
        dias_afastamento: $("#va_dias", box).value ? Number($("#va_dias", box).value) : null,
        cid: $("#va_cid", box).value || null,
        data_inicio: $("#va_ini", box).value || null,
      };
      try {
        await api(`/atendimentos/${id}/atestados`, { method: "POST", body: JSON.stringify(body) });
        toast("Atestado emitido");
        closeModal();
        verAtendimento(id);
      } catch (e) { toast(e.message, true); }
    };
  }
  openModal("Atendimento anterior", w);
}

// ═════════ RETORNOS ═════════
views.retornos = async () => {
  viewEl.innerHTML = `<div class="page-head"><h1 class="title">Retornos agendados</h1>
    <select id="dias" style="width:auto"><option value="7">7 dias</option><option value="14" selected>14 dias</option><option value="30">30 dias</option><option value="90">90 dias</option></select></div>
    <div class="panel" id="lista"></div>`;
  const carregar = async () => {
    const l = await api(`/relatorios/retornos?dias=${$("#dias").value}`);
    const box = $("#lista"); box.innerHTML = "";
    if (!l.length) return (box.innerHTML = '<p class="empty">Nenhum retorno agendado no período.</p>');
    const recep = ["RECEPCAO", "ENFERMEIRO"].includes(user.perfil);
    const t = el(`<table><thead><tr><th>Data do retorno</th><th>Paciente</th><th>Profissional que agendou</th><th></th></tr></thead><tbody></tbody></table>`);
    l.forEach((a) => {
      const tr = el(`<tr><td><b>${fmtD(a.retorno_data)}</b></td>
        <td>${esc(a.cidadao ? (a.cidadao.nome_social || a.cidadao.nome_completo) : "-")}</td>
        <td>${esc(a.profissional ? a.profissional.nome : "-")}</td><td class="row-actions"></td></tr>`);
      if (recep && a.cidadao) {
        const b = el('<button class="btn small">Colocar na fila</button>');
        b.onclick = async () => {
          try { await api("/fila", { method: "POST", body: JSON.stringify({ cidadao_id: a.cidadao.id, tipo: "RETORNO", motivo: "Retorno agendado" }) }); toast("Adicionado à fila"); }
          catch (e) { toast(e.message, true); }
        };
        $(".row-actions", tr).appendChild(b);
      }
      t.querySelector("tbody").appendChild(tr);
    });
    box.appendChild(t);
  };
  $("#dias").onchange = carregar;
  carregar();
};
