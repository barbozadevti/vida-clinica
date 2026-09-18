@echo off
chcp 65001 >nul
title Vida+ Clinica  (feche esta janela para PARAR)
cd /d "%~dp0"

echo ============================================================
echo   Vida+ Clinica  -  Sistema de Gestao Clinica
echo ============================================================
echo.

rem --- o sistema (backend) ja esta rodando? so abre o navegador e sai ---
netstat -ano | findstr "0.0.0.0:8010 127.0.0.1:8010" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 goto need_start

echo O sistema ja esta rodando. Abrindo o navegador...
start "" http://127.0.0.1:8010
echo.
echo Se quiser PARAR o sistema, feche a janela onde ele foi aberto
echo originalmente ^(ou use o Gerenciador de Tarefas para encerrar
echo o processo "python" na porta 8010^).
pause
exit /b

:need_start
echo [1/3] Verificando o banco de dados PostgreSQL...
rem IMPORTANTE: so chamamos "pg_ctl start" se o Postgres NAO estiver pronto.
rem Chamar start com o servidor ja rodando trava (pg_ctl fica esperando
rem para sempre um postmaster novo que nunca sobe, pois a porta ja esta em uso).
"C:\Users\rafap\pgsql\bin\pg_isready.exe" -h 127.0.0.1 -p 5432 -t 2 >nul 2>&1
if errorlevel 1 goto start_pg
echo    Ja estava rodando.
goto pg_done

:start_pg
rem limpeza defensiva: se uma tentativa anterior travou no meio do caminho
rem (ex.: a janela foi fechada enquanto o banco ainda estava recuperando de
rem um desligamento anterior), pode sobrar processo "preso" e uma trava
rem antiga (postmaster.pid) que impedem o proximo start de funcionar. So
rem fazemos essa limpeza aqui porque o pg_isready ACIMA ja confirmou que
rem nada esta respondendo na porta 5432 -- ou seja, nao ha servidor saudavel
rem para atrapalhar.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq 'postgres.exe' -and $_.CommandLine -like '*pgdata*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
if exist "C:\Users\rafap\pgdata\postmaster.pid" del /f /q "C:\Users\rafap\pgdata\postmaster.pid" >nul 2>&1
"C:\Users\rafap\pgsql\bin\pg_ctl.exe" -D "C:\Users\rafap\pgdata" -l "C:\Users\rafap\pgdata\server.log" -o "-p 5432" start >nul 2>&1
"C:\Users\rafap\pgsql\bin\pg_isready.exe" -h 127.0.0.1 -p 5432 -t 25 >nul 2>&1
if errorlevel 1 goto pg_failed
echo    OK.
goto pg_done

:pg_failed
echo    ERRO: o PostgreSQL nao respondeu. Veja C:\Users\rafap\pgdata\server.log
pause
exit /b

:pg_done
echo.

if exist "backend\.venv\Scripts\python.exe" goto python_ok
echo ERRO: nao encontrei backend\.venv\Scripts\python.exe
echo O ambiente virtual do Python nao existe ou foi movido.
pause
exit /b

:python_ok
echo [2/3] O navegador abrira em instantes...
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 6; Start-Process 'http://127.0.0.1:8010'"
echo.
echo [3/3] Iniciando o sistema  (http://127.0.0.1:8010)
echo    Login:  medico@ubs.local   Senha: 123456
echo.
echo    ^>^>^> Para PARAR: feche esta janela ^<^<^<
echo ============================================================
echo.

"backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --port 8010 --host 127.0.0.1 --app-dir backend

echo.
echo Sistema encerrado.
"C:\Users\rafap\pgsql\bin\pg_ctl.exe" -D "C:\Users\rafap\pgdata" stop -m fast >nul 2>&1
pause
