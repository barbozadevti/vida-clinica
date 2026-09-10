# PostgreSQL portátil (C:\Users\rafap\pgsql / dados em C:\Users\rafap\pgdata)
param([ValidateSet("start","stop","status","restart","psql")] [string]$Acao = "status")
$PGBIN = "C:\Users\rafap\pgsql\bin"
$PGDATA = "C:\Users\rafap\pgdata"
$env:PGPASSWORD = "postgres"
switch ($Acao) {
  "start"   { & "$PGBIN\pg_ctl.exe" -D $PGDATA -l "$PGDATA\server.log" -o "-p 5432" start }
  "stop"    { & "$PGBIN\pg_ctl.exe" -D $PGDATA stop -m fast }
  "restart" { & "$PGBIN\pg_ctl.exe" -D $PGDATA -l "$PGDATA\server.log" -o "-p 5432" restart -m fast }
  "status"  { & "$PGBIN\pg_ctl.exe" -D $PGDATA status; & "$PGBIN\pg_isready.exe" -h 127.0.0.1 -p 5432 }
  "psql"    { & "$PGBIN\psql.exe" -h 127.0.0.1 -U postgres -d esus }
}
