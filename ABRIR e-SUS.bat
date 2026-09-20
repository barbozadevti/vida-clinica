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
echo.
echo    Depois que o computador e desligado, o banco precisa se recuperar
echo    sozinho ao ligar (ate ~1 minuto). E NORMAL. Aguarde: NAO aperte
echo    Ctrl+C e NAO feche esta janela. Se clicar no atalho de novo, ele
echo    apenas espera o banco que ja esta subindo.
echo.
rem Toda a logica do banco esta em scripts\pg.ps1. Pontos importantes dela:
rem  - o banco sobe em janela PROPRIA e OCULTA (Ctrl+C / fechar esta janela nao o atinge;
rem    antes ele dividia esta janela e desligava junto -> ciclo de "recuperacao" sem fim);
rem  - um banco que esta so RECUPERANDO nunca e derrubado, apenas aguardado;
rem  - so limpa processo/trava orfaos quando nada saudavel esta rodando.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\pg.ps1" start
if errorlevel 1 goto pg_failed
echo.
goto pg_done

:pg_failed
echo.
echo    ERRO: o PostgreSQL nao respondeu ^(detalhes acima^).
echo.
echo    Tente de novo pelo atalho. Para acabar de vez com essa espera, de dois
echo    cliques em "INSTALAR SERVICO DO BANCO.bat" ^(pede permissao de administrador
echo    uma unica vez^) - veja o README, secao "PostgreSQL nao respondeu".
pause
exit /b

:pg_done
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
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\pg.ps1" encerrar
pause
