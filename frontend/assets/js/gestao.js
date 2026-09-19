// ═════════════════════════════════════════════════════════════
// GESTÃO — MVP 2 da Lean Inception (12/09): agenda, convênios,
// financeiro e estoque — o fechamento do dia da clínica.
// Depende dos utilitários definidos em core.js.
// ═════════════════════════════════════════════════════════════

// nota fiscal de serviço (Financeiro) — substitui o recibo: por lei, todo
// procedimento/consulta precisa de nota fiscal, PF ou PJ. window.open()
// síncrono no clique (mesma correção do imprimir() do atendimento), senão
// o navegador bloqueia a aba por não reconhecer mais o clique original.
function imprimirNotaFiscal(cid) {
  const w = window.open("", "_blank");
  if (!w) return toast("Permita pop-ups para imprimir", true);
  w.document.write('<p style="font:14px sans-serif;padding:20px">Emitindo nota fiscal…</p>');
  api(`/financeiro/cobrancas/${cid}/nota-fiscal`)
    .then(({ html }) => { w.document.open(); w.document.write(html); w.document.close(); })
    .catch((e) => { w.close(); toast(e.message, true); });
}
async function baixarNotaFiscalPdf(cid) {
  try {
    const r = await fetch(`${API}/financeiro/cobrancas/${cid}/nota-fiscal.pdf`, { headers: { Authorization: `Bearer ${token}` } });
    if (!r.ok) { const d = await r.json().catch(() => null); throw new Error((d && d.detail) || `Erro ${r.status}`); }
    const blob = await r.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "nota-fiscal.pdf"; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  } catch (e) { toast(e.message, true); }
}

// ═════════ RELATÓRIOS ═════════
views.relatorios = async () => {
  const hoje = hojeInput();
  const mes = hoje.slice(0, 8) + "01";
  const ehAdmin = user.perfil === "ADMIN";
  viewEl.innerHTML = `<div class="page-head"><h1 class="title">Relatório de produção</h1></div>
    <div class="panel"><div class="toolbar">
      <label class="fld">De <input type="date" id="r_de" value="${mes}"></label>
      <label class="fld">Até <input type="date" id="r_ate" value="${hoje}"></label>
      ${ehAdmin ? '<label class="fld">Unidade <select id="r_unidade"><option value="">Todas as unidades</option></select></label>' : ""}
      <button class="btn" id="r_go">Gerar</button>
      <button class="btn sec" id="r_pdf">Baixar PDF</button>
      <button class="btn sec" id="r_xlsx">Baixar Excel</button>
    </div></div>
    <div id="r_out"></div>`;
  if (ehAdmin) {
    try {
      const unidades = await api("/unidades");
      const sel = $("#r_unidade");
      unidades.forEach((u) => sel.appendChild(el(`<option value="${u.id}">${esc(u.nome)}</option>`)));
    } catch (e) { /* multiclínica ainda sem unidades cadastradas — mantém "Todas" */ }
  }
  const qs = () => {
    const p = new URLSearchParams({ de: $("#r_de").value, ate: $("#r_ate").value });
    const uid = ehAdmin ? $("#r_unidade").value : "";
    if (uid) p.set("unidade_id", uid);
    return p.toString();
  };
  const tabela = (titulo, linhas, cols) => `<div class="panel"><h3>${titulo}</h3>
    ${linhas.length ? `<table><tbody>${linhas.map((r) => `<tr>${cols(r)}</tr>`).join("")}</tbody></table>` : '<p class="muted">Sem dados.</p>'}</div>`;
  const gerar = async () => {
    const d = await api(`/relatorios/producao?${qs()}`);
    $("#r_out").innerHTML = `
      <div class="cards"><div class="card"><div class="k">Atendimentos finalizados</div><div class="v">${d.total}</div></div></div>
      ${tabela("Por profissional", d.por_profissional, (r) => `<td>${esc(r.nome)}</td><td><b>${r.total}</b></td>`)}
      ${tabela("Por desfecho", d.por_desfecho, (r) => `<td>${esc(r.nome.replace(/_/g, " "))}</td><td><b>${r.total}</b></td>`)}
      ${tabela("Por classificação de risco", d.por_risco, (r) => `<td>${esc(r.nome)}</td><td><b>${r.total}</b></td>`)}
      ${tabela("CID/CIAP mais frequentes", d.por_cid, (r) => `<td>${esc(r.codigo)}</td><td>${esc(r.descricao)}</td><td><b>${r.total}</b></td>`)}`;
  };
  $("#r_go").onclick = gerar;
  $("#r_xlsx").onclick = async () => {
    try {
      const r = await fetch(`/api/relatorios/producao.xlsx?${qs()}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) { const d = await r.json().catch(() => null); throw new Error((d && d.detail) || `Erro ${r.status}`); }
      const blob = await r.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = `producao_${$("#r_de").value}_${$("#r_ate").value}.xlsx`; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    } catch (e) { toast(e.message, true); }
  };
  $("#r_pdf").onclick = async () => {
    try {
      const r = await fetch(`/api/relatorios/producao.pdf?${qs()}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) { const d = await r.json().catch(() => null); throw new Error((d && d.detail) || `Erro ${r.status}`); }
      const blob = await r.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = `producao_${$("#r_de").value}_${$("#r_ate").value}.pdf`; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    } catch (e) { toast(e.message, true); }
  };
  if (ehAdmin) $("#r_unidade").onchange = gerar;
  gerar();
};

// Onda 4 — confirmação por WhatsApp: link "click-to-chat" (wa.me), sem custo
// e sem precisar de conta de API — a recepção revisa e envia a mensagem.
function linkWhatsApp(telefone, mensagem) {
  const digitos = (telefone || "").replace(/\D/g, "");
  if (!digitos) return null;
  const comDDI = digitos.length <= 11 ? "55" + digitos : digitos;
  return `https://wa.me/${comDDI}?text=${encodeURIComponent(mensagem)}`;
}

// Onda 5 — teleconsulta: sala de vídeo via Jitsi Meet (gratuito, sem conta,
// sem chave de API) — valida a hipótese sem construir infraestrutura de vídeo própria.
const linkTeleconsulta = (agendamentoId) => `https://meet.jit.si/VidaClinica-${agendamentoId}`;

// ═════════ AGENDA ═════════
views.agenda = async () => {
  const gerencia = ["RECEPCAO", "ADMIN"].includes(user.perfil);
  const podeChegada = ["RECEPCAO", "ENFERMEIRO"].includes(user.perfil);
  viewEl.innerHTML = `<div class="page-head"><h1 class="title">Agenda</h1>
      ${gerencia ? '<button class="btn" id="ag-novo">+ Novo agendamento</button>' : ""}</div>
    <div class="panel"><label class="fld" style="max-width:220px">Data<input type="date" id="ag-data" value="${hojeInput()}"></label></div>
    <div class="panel" id="ag-lista"></div>`;
  const carregar = async () => {
    const l = await api(`/agenda?data=${$("#ag-data").value}`);
    const box = $("#ag-lista"); box.innerHTML = "";
    if (!l.length) return (box.innerHTML = '<p class="empty">Nenhum agendamento nesta data.</p>');
    const t = el(`<table><thead><tr><th>Hora</th><th>Paciente</th><th>Profissional</th><th>Tipo</th><th>Status</th><th></th></tr></thead><tbody></tbody></table>`);
    l.forEach((a) => {
      const c = a.cidadao || {};
      const tr = el(`<tr><td><b>${esc(a.hora)}</b><br><span class="muted">${a.duracao_min} min</span></td>
        <td>${esc(c.nome_social || c.nome_completo || "-")}</td>
        <td>${esc(a.profissional ? a.profissional.nome : "-")}</td>
        <td>${esc((a.tipo || "").replace(/_/g, " "))}${a.observacao ? "<br><span class='muted'>" + esc(a.observacao) + "</span>" : ""}</td>
        <td>${stBadge(a.status)}</td><td class="row-actions"></td></tr>`);
      const acts = $(".row-actions", tr);
      if (gerencia && a.status === "AGENDADO") {
        const cf = el('<button class="btn small sec">Confirmar</button>');
        cf.onclick = async () => { await api(`/agenda/${a.id}/status?status=CONFIRMADO`, { method: "POST" }); carregar(); };
        acts.appendChild(cf);
      }
      if (gerencia && ["AGENDADO", "CONFIRMADO"].includes(a.status)) {
        const link = linkWhatsApp(c.telefone,
          `Olá, ${c.nome_social || c.nome_completo}! Sua consulta na Vida+ Clínica está marcada para ${fmtD(a.data)} às ${a.hora}` +
          `${a.profissional ? " com " + a.profissional.nome : ""}. Responda para confirmar. Se precisar remarcar, é só nos avisar.`);
        if (link) {
          const wa = el('<button class="btn small sec">📲 WhatsApp</button>');
          wa.onclick = () => window.open(link, "_blank");
          acts.appendChild(wa);
        }
      }
      if (a.tipo === "TELECONSULTA" && ["AGENDADO", "CONFIRMADO"].includes(a.status)) {
        const tv = el('<button class="btn small sec">🎥 Videochamada</button>');
        tv.onclick = () => window.open(linkTeleconsulta(a.id), "_blank");
        acts.appendChild(tv);
      }
      if (podeChegada && ["AGENDADO", "CONFIRMADO"].includes(a.status)) {
        const ch = el('<button class="btn small">Paciente chegou</button>');
        ch.onclick = async () => {
          try { await api(`/agenda/${a.id}/enviar-fila`, { method: "POST" }); toast("Enviado para a fila de atendimento"); carregar(); }
          catch (e) { toast(e.message, true); }
        };
        acts.appendChild(ch);
      }
      if (gerencia && !["ATENDIDO", "CANCELADO"].includes(a.status)) {
        const nc = el('<button class="btn small sec">Faltou</button>');
        nc.onclick = async () => { await api(`/agenda/${a.id}/status?status=FALTOU`, { method: "POST" }); carregar(); };
        const x = el('<button class="btn small danger">Cancelar</button>');
        x.onclick = async () => { if (!confirm("Cancelar agendamento?")) return; await api(`/agenda/${a.id}`, { method: "DELETE" }); carregar(); };
        acts.append(nc, x);
      }
      t.querySelector("tbody").appendChild(tr);
    });
    box.appendChild(t);
  };
  $("#ag-data").onchange = carregar;
  if ($("#ag-novo")) $("#ag-novo").onclick = () => agendamentoForm(carregar, $("#ag-data").value);
  carregar();
};

async function agendamentoForm(reload, dataPadrao) {
  const [cids, profs] = await Promise.all([api("/cidadaos"), api("/usuarios").catch(() => [])]);
  const clinicos = profs.filter((u) => ["MEDICO", "ENFERMEIRO"].includes(u.perfil) && u.ativo);
  formModal({
    title: "Novo agendamento",
    values: { data: dataPadrao || hojeInput(), duracao_min: 30, hora: "08:00" },
    fields: [
      { name: "cidadao_id", label: "Paciente", required: true, type: "select", full: true,
        options: cids.map((c) => ({ value: c.id, label: `${c.nome_completo}${c.cpf ? " — " + c.cpf : ""}` })) },
      { name: "profissional_id", label: "Profissional", required: true, type: "select",
        options: clinicos.map((u) => ({ value: u.id, label: `${u.nome} (${u.perfil})` })) },
      { name: "tipo", label: "Tipo", type: "select",
        options: ["CONSULTA", "RETORNO", "PRE_NATAL", "PROCEDIMENTO", "URGENCIA", "TELECONSULTA"].map((v) => ({ value: v, label: v.replace(/_/g, " ") })) },
      { name: "data", label: "Data", type: "date", required: true },
      { name: "hora", label: "Hora (HH:MM)", required: true },
      { name: "duracao_min", label: "Duração (min)", type: "number", cast: "int" },
      { name: "observacao", label: "Observação", type: "textarea", full: true },
    ],
    onSubmit: async (d) => { await api("/agenda", { method: "POST", body: JSON.stringify(d) }); toast("Agendamento criado"); reload(); },
  });
}

// ═════════ CONVÊNIOS ═════════
views.convenios = async () => {
  const gerencia = ["RECEPCAO", "ADMIN"].includes(user.perfil);
  viewEl.innerHTML = `<div class="page-head"><h1 class="title">Convênios</h1>
      ${gerencia ? '<button class="btn" id="cv-novo">+ Novo convênio</button>' : ""}</div>
    <div class="panel" id="cv-lista"></div>`;
  const carregar = async () => {
    const l = await api("/convenios");
    const box = $("#cv-lista"); box.innerHTML = "";
    if (!l.length) return (box.innerHTML = '<p class="empty">Nenhum convênio cadastrado.</p>');
    const t = el(`<table><thead><tr><th>Nome</th><th>Registro ANS</th><th>CNPJ</th><th>Telefone</th><th>Ativo</th><th></th></tr></thead><tbody></tbody></table>`);
    l.forEach((c) => {
      const tr = el(`<tr><td><b>${esc(c.nome)}</b></td><td>${esc(c.registro_ans || "-")}</td>
        <td>${esc(c.cnpj || "-")}</td>
        <td>${esc(c.telefone || "-")}</td><td>${c.ativo ? "sim" : "não"}</td><td class="row-actions"></td></tr>`);
      if (gerencia) { const e = el('<button class="btn small sec">Editar</button>'); e.onclick = () => convenioForm(c, carregar); $(".row-actions", tr).appendChild(e); }
      t.querySelector("tbody").appendChild(tr);
    });
    box.appendChild(t);
  };
  if ($("#cv-novo")) $("#cv-novo").onclick = () => convenioForm(null, carregar);
  carregar();
};
function convenioForm(c, reload) {
  formModal({
    title: c ? "Editar convênio" : "Novo convênio",
    values: c || {},
    fields: [
      { name: "nome", label: "Nome", required: true, full: true },
      { name: "registro_ans", label: "Registro ANS" },
      { name: "cnpj", label: "CNPJ (pessoa jurídica, só números — usado na nota fiscal)" },
      { name: "telefone", label: "Telefone" },
      ...(c ? [{ name: "ativo", label: "Ativo", type: "select", options: [{ value: "true", label: "Sim" }, { value: "false", label: "Não" }] }] : []),
    ],
    onSubmit: async (d) => {
      if (d.ativo !== undefined) d.ativo = d.ativo === "true";
      if (c) await api(`/convenios/${c.id}`, { method: "PUT", body: JSON.stringify(d) });
      else await api("/convenios", { method: "POST", body: JSON.stringify(d) });
      toast("Convênio salvo"); reload();
    },
  });
}

// ═════════ FINANCEIRO ═════════
views.financeiro = async () => {
  const hoje = hojeInput();
  const mes = hoje.slice(0, 8) + "01";
  viewEl.innerHTML = `<div class="page-head"><h1 class="title">Financeiro</h1>
      <button class="btn" id="fn-novo">+ Nova cobrança</button></div>
    <div class="panel"><div class="toolbar">
      <label class="fld">De <input type="date" id="fn_de" value="${mes}"></label>
      <label class="fld">Até <input type="date" id="fn_ate" value="${hoje}"></label>
      <button class="btn sec" id="fn_go">Atualizar</button>
    </div></div>
    <div id="fn_resumo"></div>
    <div class="panel"><h3>Cobranças recentes</h3><div id="fn_lista"></div></div>`;
  const carregarResumo = async () => {
    const de = $("#fn_de").value, ate = $("#fn_ate").value;
    const r = await api(`/financeiro/resumo?de=${de}&ate=${ate}`);
    $("#fn_resumo").innerHTML = `<div class="cards">
      <div class="card"><div class="k">Faturado no período</div><div class="v">R$ ${r.total_faturado.toFixed(2).replace(".", ",")}</div></div>
      <div class="card"><div class="k">Recebido</div><div class="v">R$ ${r.total_pago.toFixed(2).replace(".", ",")}</div></div>
      <div class="card"><div class="k">A receber</div><div class="v">R$ ${r.total_pendente.toFixed(2).replace(".", ",")}</div></div>
    </div>
    ${r.por_forma.length ? `<div class="panel"><h3>Por forma de pagamento</h3><table><tbody>${r.por_forma.map((f) => `<tr><td>${esc(f.forma.replace(/_/g, " "))}</td><td><b>R$ ${f.total.toFixed(2).replace(".", ",")}</b></td></tr>`).join("")}</tbody></table></div>` : ""}`;
  };
  const carregarLista = async () => {
    const l = await api("/financeiro/cobrancas");
    const box = $("#fn_lista"); box.innerHTML = "";
    if (!l.length) return (box.innerHTML = '<p class="empty">Nenhuma cobrança lançada.</p>');
    const t = el(`<table><thead><tr><th>Data</th><th>Paciente</th><th>Descrição</th><th>Valor</th><th>Forma</th><th>Status</th><th></th></tr></thead><tbody></tbody></table>`);
    l.forEach((c) => {
      const tr = el(`<tr><td>${fmtD(c.criado_em)}</td>
        <td>${esc(c.cidadao ? (c.cidadao.nome_social || c.cidadao.nome_completo) : "-")}</td>
        <td>${esc(c.descricao)}</td><td><b>R$ ${c.valor.toFixed(2).replace(".", ",")}</b></td>
        <td>${esc(c.forma_pagamento.replace(/_/g, " "))}${c.convenio ? "<br><span class='muted'>" + esc(c.convenio.nome) + "</span>" : ""}</td>
        <td>${stBadge(c.status)}${c.numero_nf ? "<br><span class='muted'>NF " + esc(c.numero_nf) + "</span>" : ""}</td>
        <td class="row-actions"></td></tr>`);
      const acts = $(".row-actions", tr);
      if (c.status === "PENDENTE") {
        const p = el('<button class="btn small">Marcar pago</button>');
        p.onclick = async () => { await api(`/financeiro/cobrancas/${c.id}/pagar`, { method: "POST" }); toast("Pagamento registrado"); carregarLista(); carregarResumo(); };
        const x = el('<button class="btn small danger">Cancelar</button>');
        x.onclick = async () => { if (!confirm("Cancelar cobrança?")) return; await api(`/financeiro/cobrancas/${c.id}/cancelar`, { method: "POST" }); carregarLista(); carregarResumo(); };
        acts.append(p, x);
      }
      if (c.status === "PAGO") {
        const r1 = el(`<button class="btn small sec">🖨️ ${c.numero_nf ? "Nota Fiscal" : "Emitir Nota Fiscal"}</button>`); r1.onclick = () => imprimirNotaFiscal(c.id);
        const r2 = el('<button class="btn small sec">PDF</button>'); r2.onclick = () => baixarNotaFiscalPdf(c.id);
        acts.append(r1, r2);
      }
      if (c.forma_pagamento === "CONVENIO" && c.convenio) {
        const g = el('<button class="btn small sec">Guia TISS</button>'); g.onclick = () => imprimirGuiaTiss(c.id);
        acts.appendChild(g);
      }
      t.querySelector("tbody").appendChild(tr);
    });
    box.appendChild(t);
  };
  $("#fn_go").onclick = carregarResumo;
  $("#fn-novo").onclick = () => cobrancaForm(() => { carregarLista(); carregarResumo(); });
  carregarResumo(); carregarLista();
};

async function cobrancaForm(reload) {
  const [cids, convs] = await Promise.all([api("/cidadaos"), api("/convenios").catch(() => [])]);
  formModal({
    title: "Nova cobrança",
    values: { descricao: "Consulta", forma_pagamento: "DINHEIRO" },
    fields: [
      { name: "cidadao_id", label: "Paciente", required: true, type: "select", full: true,
        options: cids.map((c) => ({ value: c.id, label: `${c.nome_completo}${c.cpf ? " — " + c.cpf : ""}` })) },
      { name: "descricao", label: "Descrição", required: true, full: true },
      { name: "valor", label: "Valor (R$)", required: true, type: "number", step: "0.01", cast: "number" },
      { name: "forma_pagamento", label: "Forma de pagamento", type: "select",
        options: ["DINHEIRO", "PIX", "CARTAO_DEBITO", "CARTAO_CREDITO", "CONVENIO", "BOLETO"].map((v) => ({ value: v, label: v.replace(/_/g, " ") })) },
      { name: "convenio_id", label: "Convênio (se aplicável)", type: "select",
        options: [{ value: "", label: "—" }, ...convs.map((v) => ({ value: v.id, label: v.nome }))] },
      { name: "codigo_tuss", label: "Código TUSS (para guia do convênio)" },
    ],
    onSubmit: async (d) => { await api("/financeiro/cobrancas", { method: "POST", body: JSON.stringify(d) }); toast("Cobrança lançada"); reload(); },
  });
}

// Guia TISS simplificada (Onda 5) — impressão/PDF de cobranças por convênio
function imprimirGuiaTiss(cid) {
  const w = window.open("", "_blank");
  if (!w) return toast("Permita pop-ups para imprimir", true);
  fetch(`${API}/financeiro/cobrancas/${cid}/guia-tiss.pdf`, { headers: { Authorization: `Bearer ${token}` } })
    .then(async (r) => {
      if (!r.ok) { const d = await r.json().catch(() => null); throw new Error((d && d.detail) || `Erro ${r.status}`); }
      const blob = await r.blob();
      w.location.href = URL.createObjectURL(blob);
    })
    .catch((e) => { w.close(); toast(e.message, true); });
}

// ═════════ ESTOQUE ═════════
views.estoque = async () => {
  const gerencia = ["ADMIN", "ENFERMEIRO", "RECEPCAO"].includes(user.perfil);
  viewEl.innerHTML = `<div class="page-head"><h1 class="title">Estoque</h1>
      ${gerencia ? '<button class="btn" id="es-novo">+ Novo item</button>' : ""}</div>
    <div class="panel" id="es-lista"></div>`;
  const carregar = async () => {
    const l = await api("/estoque/itens");
    const box = $("#es-lista"); box.innerHTML = "";
    if (!l.length) return (box.innerHTML = '<p class="empty">Nenhum item cadastrado.</p>');
    const t = el(`<table><thead><tr><th>Item</th><th>Categoria</th><th>Quantidade</th><th>Mínimo</th><th></th></tr></thead><tbody></tbody></table>`);
    l.forEach((it) => {
      const baixo = it.quantidade <= it.quantidade_minima;
      const tr = el(`<tr${baixo ? ' style="background:#fef2f2"' : ""}>
        <td><b>${esc(it.nome)}</b></td><td>${esc(it.categoria)}</td>
        <td>${it.quantidade} ${esc(it.unidade)} ${baixo ? '<span class="badge risco-VERMELHO">baixo</span>' : ""}</td>
        <td>${it.quantidade_minima} ${esc(it.unidade)}</td><td class="row-actions"></td></tr>`);
      if (gerencia) {
        const m = el('<button class="btn small">Movimentar</button>'); m.onclick = () => movimentoForm(it, carregar);
        const e = el('<button class="btn small sec">Editar</button>'); e.onclick = () => itemEstoqueForm(it, carregar);
        $(".row-actions", tr).append(m, e);
      }
      t.querySelector("tbody").appendChild(tr);
    });
    box.appendChild(t);
  };
  if ($("#es-novo")) $("#es-novo").onclick = () => itemEstoqueForm(null, carregar);
  carregar();
};
function itemEstoqueForm(it, reload) {
  formModal({
    title: it ? "Editar item" : "Novo item de estoque",
    values: it || { unidade: "un" },
    fields: [
      { name: "nome", label: "Nome", required: true, full: true },
      { name: "categoria", label: "Categoria", type: "select", options: ["MEDICAMENTO", "MATERIAL", "INSUMO"].map((v) => ({ value: v, label: v })) },
      { name: "unidade", label: "Unidade" },
      { name: "quantidade_minima", label: "Quantidade mínima", type: "number", cast: "number" },
      ...(it ? [{ name: "ativo", label: "Ativo", type: "select", options: [{ value: "true", label: "Sim" }, { value: "false", label: "Não" }] }] : []),
    ],
    onSubmit: async (d) => {
      if (d.ativo !== undefined) d.ativo = d.ativo === "true";
      if (it) await api(`/estoque/itens/${it.id}`, { method: "PUT", body: JSON.stringify(d) });
      else await api("/estoque/itens", { method: "POST", body: JSON.stringify(d) });
      toast("Item salvo"); reload();
    },
  });
}
function movimentoForm(it, reload) {
  formModal({
    title: `Movimentar — ${it.nome}`,
    submitLabel: "Registrar",
    fields: [
      { name: "tipo", label: "Tipo", type: "select", options: [{ value: "ENTRADA", label: "Entrada" }, { value: "SAIDA", label: "Saída" }, { value: "AJUSTE", label: "Ajuste (define o total)" }] },
      { name: "quantidade", label: "Quantidade", required: true, type: "number", step: "0.01", cast: "number" },
      { name: "motivo", label: "Motivo", full: true },
    ],
    onSubmit: async (d) => { await api(`/estoque/itens/${it.id}/movimentar`, { method: "POST", body: JSON.stringify(d) }); toast("Estoque atualizado"); reload(); },
  });
}
