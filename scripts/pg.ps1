# PostgreSQL portatil (C:\Users\rafap\pgsql / dados em C:\Users\rafap\pgdata)
# Usado pelo atalho "ABRIR e-SUS.bat" e manualmente (start|stop|status|restart|psql|encerrar).
# Texto sem acento de proposito: o console do Windows/PowerShell 5.1 estraga acentos.
param([ValidateSet("start","stop","status","restart","psql","encerrar")] [string]$Acao = "status")
$PGBIN = "C:\Users\rafap\pgsql\bin"
$PGDATA = "C:\Users\rafap\pgdata"
$SERVICO = "PostgresVidaClinica"
$env:PGPASSWORD = "postgres"
$script:codigo = 0

# pg_isready: 0 = aceitando conexoes | 1 = subindo/recuperando | 2 = sem resposta | 3 = sem tentativa
function Test-Pronto {
  & "$PGBIN\pg_isready.exe" -h 127.0.0.1 -p 5432 -t 2 *> $null
  return $LASTEXITCODE
}

# todos os postgres.exe DESTA instalacao (postmaster + filhos, inclusive orfaos)
function Get-ProcessosPg {
  Get-CimInstance Win32_Process -Filter "Name='postgres.exe'" -ErrorAction SilentlyContinue |
    Where-Object { ($_.ExecutablePath -replace '/', '\') -like "$PGBIN\*" }
}

# o postmaster e o unico sem "--fork" na linha de comando (filhos/auxiliares tem)
function Get-Postmaster {
  Get-ProcessosPg | Where-Object { $_.CommandLine -notlike "*--fork*" }
}

# derruba tudo que sobrou (postmaster morto costuma deixar filho orfao) e apaga a trava velha.
# So e chamado quando NADA saudavel esta rodando.
function Limpar-Restos {
  Get-ProcessosPg | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  # confere que sairam de verdade (antes de subir um novo, senao brigam pelos mesmos arquivos)
  for ($i = 0; $i -lt 20 -and (Get-ProcessosPg); $i++) { Start-Sleep -Seconds 1 }
  Remove-Item "$PGDATA\postmaster.pid" -Force -ErrorAction SilentlyContinue
}

# IMPORTANTE: o banco sobe em janela PROPRIA e OCULTA. Antes ele nascia dentro da
# janela do atalho e recebia o Ctrl+C / o "fechar janela" dela -> desligava no meio da
# recuperacao e virava um ciclo de crash. "pg_ctl start" e chamado UMA UNICA VEZ (-W = nao
# espera); quem espera de verdade e o Esperar-Postgres, que so consulta o pg_isready.
function Iniciar-Destacado {
  Start-Process -FilePath "$PGBIN\pg_ctl.exe" -WindowStyle Hidden `
    -ArgumentList "-D `"$PGDATA`" -l `"$PGDATA\server.log`" -o `"-p 5432`" -W start"
}

# devolve: pronto | travado | morreu | tempo
function Esperar-Postgres {
  $inicio = Get-Date
  $semRespostaDesde = $null
  $ultimoAviso = 0
  while (((Get-Date) - $inicio).TotalSeconds -lt 300) {
    $c = Test-Pronto
    if ($c -eq 0) { Write-Host ""; return "pronto" }
    if ($c -eq 1) {
      # 1 = o banco esta vivo, so recuperando do ultimo desligamento: APENAS ESPERAR
      $semRespostaDesde = $null
    } else {
      if (-not $semRespostaDesde) { $semRespostaDesde = Get-Date }
      # o processo principal do banco demora a aparecer quando o antivirus esta escaneando
      # os executaveis: enquanto o pg_ctl (lancador) ou o postmaster existirem, da 60 s.
      $limite = 15
      if ((Get-Postmaster) -or (Get-Process -Name pg_ctl -ErrorAction SilentlyContinue)) { $limite = 60 }
      if (((Get-Date) - $semRespostaDesde).TotalSeconds -gt $limite) {
        Write-Host ""
        if (Get-Postmaster) { return "travado" }
        return "morreu"
      }
    }
    $seg = [int]((Get-Date) - $inicio).TotalSeconds
    if ($seg -ge ($ultimoAviso + 15)) { Write-Host " ${seg}s" -NoNewline; $ultimoAviso = $seg }
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 3
  }
  Write-Host ""
  return "tempo"
}

function Mostrar-Falha {
  Write-Host ""
  Write-Host "ERRO: o PostgreSQL nao respondeu. Ultimas linhas de $PGDATA\server.log:"
  Get-Content "$PGDATA\server.log" -Tail 12 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  $_" }
  $script:codigo = 1
}

function Iniciar-Banco {
  if ((Test-Pronto) -eq 0) { Write-Host "Ja estava rodando."; return }

  # se o banco foi instalado como servico do Windows (INSTALAR SERVICO DO BANCO.bat),
  # quem cuida dele e o Windows: aqui so esperamos.
  $svc = Get-Service -Name $SERVICO -ErrorAction SilentlyContinue
  if ($svc) {
    if ($svc.Status -ne "Running") {
      try { Start-Service -Name $SERVICO -ErrorAction Stop }
      catch { Write-Host "(servico do Windows parado e sem permissao para liga-lo aqui; subindo manualmente)" }
      $svc.Refresh()
    }
    if ($svc.Status -eq "Running") {
      Write-Host "Aguardando o servico do Windows do banco..." -NoNewline
      $r = @(Esperar-Postgres)[-1]
      if ($r -eq "pronto") { Write-Host "OK."; return }
      Mostrar-Falha; return
    }
  }

  if (Get-Postmaster) {
    # ja existe um banco subindo (ex.: voce clicou no atalho de novo): NAO matar, so esperar.
    Write-Host "O banco ja esta subindo (recuperando do ultimo desligamento). Aguarde e NAO aperte Ctrl+C nem feche esta janela." -NoNewline
  } else {
    Write-Host "Iniciando o banco (apos desligar o PC ele se recupera sozinho, leva ate ~1 minuto). Aguarde e NAO aperte Ctrl+C nem feche esta janela." -NoNewline
    Limpar-Restos
    Iniciar-Destacado
  }
  $r = @(Esperar-Postgres)[-1]
  if ($r -eq "travado" -or $r -eq "morreu") {
    Write-Host "O banco nao respondeu ($r). Limpando e tentando de novo, uma vez..." -NoNewline
    Limpar-Restos
    Iniciar-Destacado
    $r = @(Esperar-Postgres)[-1]
  }
  if ($r -eq "pronto") { Write-Host "OK."; return }
  Mostrar-Falha
}

function Parar-Banco {
  & "$PGBIN\pg_ctl.exe" -D $PGDATA stop -m fast *> $null
  # se algum processo teimar em ficar (orfao), derruba
  for ($i = 0; $i -lt 10 -and (Get-ProcessosPg); $i++) { Start-Sleep -Seconds 1 }
  if (Get-ProcessosPg) { Limpar-Restos }
}

switch ($Acao) {
  "start"    { Iniciar-Banco }
  "stop"     { Parar-Banco }
  "restart"  { Parar-Banco; Iniciar-Banco }
  "status"   { & "$PGBIN\pg_ctl.exe" -D $PGDATA status; & "$PGBIN\pg_isready.exe" -h 127.0.0.1 -p 5432 }
  "psql"     { & "$PGBIN\psql.exe" -h 127.0.0.1 -U postgres -d esus }
  "encerrar" {
    # chamado pelo atalho ao terminar: se o Windows cuida do banco (servico), deixa ligado
    $svc = Get-Service -Name $SERVICO -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq "Running") { Write-Host "Banco mantido ligado (gerenciado pelo servico do Windows)." }
    else { Parar-Banco }
  }
}
exit $script:codigo
