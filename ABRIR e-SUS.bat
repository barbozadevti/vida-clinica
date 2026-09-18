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
rem (ex.: o Windows foi desligado com o banco ainda aberto -- isso NUNCA da
rem chance do Postgres encerrar direito, entao TODA inicializacao apos
rem desligar o PC faz uma recuperacao automatica, que pode levar dezenas de
rem segundos), pode sobrar processo "preso" e uma trava antiga
rem (postmaster.pid) que impedem o proximo start de funcionar. So fazemos
rem essa limpeza aqui porque o pg_isready ACIMA ja confirmou que nada esta
rem respondendo na porta 5432 -- ou seja, nao ha servidor saudavel para
rem atrapalhar.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq 'postgres.exe' -and $_.CommandLine -like '*pgdata*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
if exist "C:\Users\rafap\pgdata\postmaster.pid" del /f /q "C:\Users\rafap\pgdata\postmaster.pid" >nul 2>&1
echo    Isso pode levar ate alguns minutos apos desligar o computador (o
echo    banco precisa recuperar de um desligamento que nao foi limpo)...
rem IMPORTANTE: "pg_ctl start" e chamado UMA UNICA VEZ aqui (com -W, sem
rem esperar). Quem espera de verdade e o loop de pg_isready logo abaixo, que
rem so FICA CONFERINDO se o processo ja lancado terminou de subir -- ele
rem NUNCA chama "pg_ctl start" de novo. Chamar start uma segunda vez enquanto
rem o primeiro ainda esta recuperando lanca um SEGUNDO postgres.exe brigando
rem pela mesma pasta de dados, o que so atrapalha e ja causou problema aqui.
"C:\Users\rafap\pgsql\bin\pg_ctl.exe" -D "C:\Users\rafap\pgdata" -l "C:\Users\rafap\pgdata\server.log" -o "-p 5432" -W start >nul 2>&1
set PG_TENTATIVA=0

:start_pg_espera
"C:\Users\rafap\pgsql\bin\pg_isready.exe" -h 127.0.0.1 -p 5432 -t 5 >nul 2>&1
if not errorlevel 1 goto pg_ok
<nul set /p "=."
set /a PG_TENTATIVA+=1
if %PG_TENTATIVA% GEQ 60 goto pg_failed
timeout /t 5 /nobreak >nul 2>&1
goto start_pg_espera

:pg_ok
echo.
echo    OK.
goto pg_done

:pg_failed
echo.
echo    ERRO: o PostgreSQL nao respondeu. Veja C:\Users\rafap\pgdata\server.log
echo.
echo    DICA: isso acontece de novo a cada vez que o computador e desligado
echo    porque o banco nunca e encerrado de forma limpa. Para resolver de
echo    vez, veja "Instalar o PostgreSQL como servico do Windows" no README.
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
