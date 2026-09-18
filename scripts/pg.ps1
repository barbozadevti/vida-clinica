# PostgreSQL portátil (C:\Users\rafap\pgsql / dados em C:\Users\rafap\pgdata)
param([ValidateSet("start","stop","status","restart","psql")] [string]$Acao = "status")
$PGBIN = "C:\Users\rafap\pgsql\bin"
$PGDATA = "C:\Users\rafap\pgdata"
$env:PGPASSWORD = "postgres"
switch ($Acao) {
  "start"   {
    # IMPORTANTE: "pg_ctl start" com o servidor ja rodando trava para sempre
    # (fica esperando um postmaster novo que nunca sobe, pois a porta ja esta
    # em uso). Por isso so chamamos start se o pg_isready disser que nao ha
    # servidor respondendo ainda.
    & "$PGBIN\pg_isready.exe" -h 127.0.0.1 -p 5432 -t 2 *> $null
    if ($LASTEXITCODE -eq 0) {
      Write-Output "Ja estava rodando."
    } else {
      # limpeza defensiva: uma tentativa anterior pode ter deixado processo
      # preso + trava antiga (postmaster.pid) se a janela/console foi fechado
      # no meio de uma recuperacao. So limpamos aqui pois o pg_isready acima
      # ja confirmou que nada esta respondendo na porta.
      Get-CimInstance Win32_Process -Filter "Name='postgres.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*pgdata*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
      Remove-Item "$PGDATA\postmaster.pid" -Force -ErrorAction SilentlyContinue
      Write-Output "Isso pode levar ate alguns minutos apos desligar o computador (recuperacao de desligamento nao limpo)..."
      # IMPORTANTE: "pg_ctl start" e chamado UMA UNICA VEZ (-W = nao espera).
      # Quem espera de verdade e o loop de pg_isready abaixo, que so FICA
      # CONFERINDO se o processo ja lancado terminou de subir -- ele nunca
      # chama "pg_ctl start" de novo. Chamar start uma segunda vez enquanto o
      # primeiro ainda esta recuperando lanca um SEGUNDO postgres.exe brigando
      # pela mesma pasta de dados, o que so atrapalha (ja aconteceu aqui).
      & "$PGBIN\pg_ctl.exe" -D $PGDATA -l "$PGDATA\server.log" -o "-p 5432" -W start *> $null
      for ($tentativa = 1; $tentativa -le 60; $tentativa++) {
        & "$PGBIN\pg_isready.exe" -h 127.0.0.1 -p 5432 -t 5 *> $null
        if ($LASTEXITCODE -eq 0) { break }
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 5
      }
      Write-Host ""
    }
  }
  "stop"    { & "$PGBIN\pg_ctl.exe" -D $PGDATA stop -m fast }
  "restart" { & "$PGBIN\pg_ctl.exe" -D $PGDATA -l "$PGDATA\server.log" -o "-p 5432" restart -m fast }
  "status"  { & "$PGBIN\pg_ctl.exe" -D $PGDATA status; & "$PGBIN\pg_isready.exe" -h 127.0.0.1 -p 5432 }
  "psql"    { & "$PGBIN\psql.exe" -h 127.0.0.1 -U postgres -d esus }
}
