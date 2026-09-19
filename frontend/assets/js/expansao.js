// ═════════════════════════════════════════════════════════════
// EXPANSÃO — ondas 4/5 da Lean Inception: multiclínica (unidades).
// A confirmação por WhatsApp e a teleconsulta estão embutidas na Agenda
// (gestao.js); o portal do paciente é um mini-app à parte (portal.html).
// Depende dos utilitários definidos em core.js.
// ═════════════════════════════════════════════════════════════

// ═════════ UNIDADES (multiclínica) ═════════
views.unidades = async () => {
  viewEl.innerHTML = `<div class="page-head"><h1 class="title">Unidades</h1>
      <button class="btn" id="un-novo">+ Nova unidade</button></div>
    <div class="panel" id="un-lista"></div>`;
  const carregar = async () => {
    const l = await api("/unidades");
    const box = $("#un-lista"); box.innerHTML = "";
    if (!l.length) return (box.innerHTML = '<p class="empty">Nenhuma unidade cadastrada.</p>');
    const t = el(`<table><thead><tr><th>Nome</th><th>Endereço</th><th>CNPJ</th><th>Telefone</th><th>Ativa</th><th></th></tr></thead><tbody></tbody></table>`);
    l.forEach((u) => {
      const tr = el(`<tr><td><b>${esc(u.nome)}</b></td><td>${esc(u.endereco || "-")}</td>
        <td>${esc(u.cnpj || "-")}</td>
        <td>${esc(u.telefone || "-")}</td><td>${u.ativo ? "sim" : "não"}</td><td class="row-actions"></td></tr>`);
      const e = el('<button class="btn small sec">Editar</button>'); e.onclick = () => unidadeForm(u, carregar);
      $(".row-actions", tr).appendChild(e);
      t.querySelector("tbody").appendChild(tr);
    });
    box.appendChild(t);
  };
  $("#un-novo").onclick = () => unidadeForm(null, carregar);
  carregar();
};
function unidadeForm(u, reload) {
  formModal({
    title: u ? "Editar unidade" : "Nova unidade",
    values: u || {},
    fields: [
      { name: "nome", label: "Nome", required: true, full: true },
      { name: "endereco", label: "Endereço", full: true },
      { name: "cnpj", label: "CNPJ (só números — prestador na nota fiscal)" },
      { name: "telefone", label: "Telefone" },
      ...(u ? [{ name: "ativo", label: "Ativa", type: "select", options: [{ value: "true", label: "Sim" }, { value: "false", label: "Não" }] }] : []),
    ],
    onSubmit: async (d) => {
      if (d.ativo !== undefined) d.ativo = d.ativo === "true";
      if (u) await api(`/unidades/${u.id}`, { method: "PUT", body: JSON.stringify(d) });
      else await api("/unidades", { method: "POST", body: JSON.stringify(d) });
      toast("Unidade salva"); reload();
    },
  });
}
