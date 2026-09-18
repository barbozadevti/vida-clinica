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
      & "$PGBIN\pg_ctl.exe" -D $PGDATA -l "$PGDATA\server.log" -o "-p 5432" start
    }
  }
  "stop"    { & "$PGBIN\pg_ctl.exe" -D $PGDATA stop -m fast }
  "restart" { & "$PGBIN\pg_ctl.exe" -D $PGDATA -l "$PGDATA\server.log" -o "-p 5432" restart -m fast }
  "status"  { & "$PGBIN\pg_ctl.exe" -D $PGDATA status; & "$PGBIN\pg_isready.exe" -h 127.0.0.1 -p 5432 }
  "psql"    { & "$PGBIN\psql.exe" -h 127.0.0.1 -U postgres -d esus }
}
