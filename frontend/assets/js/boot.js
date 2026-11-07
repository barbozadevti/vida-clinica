// ═════════════════════════════════════════════════════════════
// BOOT — carregado por último, depois que core/prontuario/gestao
// já registraram todas as views.
// ═════════════════════════════════════════════════════════════

// Atalho "abrir como <usuário>": /?login=katia@ubs.local encerra a sessão guardada no
// navegador (a do último usuário que entrou) e deixa o e-mail pronto na tela de login.
// Não entra sozinho nem pula a senha — só poupa digitar o e-mail.
const _loginParam = new URLSearchParams(location.search).get("login");
if (_loginParam) {
  sair();
  const campo = $("#login-form").elements.email;
  campo.value = _loginParam;
  $("#login-form").elements.senha.focus();
  history.replaceState(null, "", location.pathname);
} else if (token && user) iniciar();
