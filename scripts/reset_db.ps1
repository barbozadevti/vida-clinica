# Zera o banco e recria o esquema + dados de exemplo.
$PGBIN = "C:\Users\rafap\pgsql\bin"
$env:PGPASSWORD = "postgres"
& "$PGBIN\psql.exe" -h 127.0.0.1 -U postgres -c "CREATE DATABASE esus;" 2>$null
& "$PGBIN\psql.exe" -h 127.0.0.1 -U postgres -d esus -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
$backend = Resolve-Path (Join-Path $PSScriptRoot "..\backend")
Push-Location $backend
& ".\.venv\Scripts\python.exe" -c "from app.bootstrap import inicializar; inicializar()"
Pop-Location
Write-Host "Banco recriado."
