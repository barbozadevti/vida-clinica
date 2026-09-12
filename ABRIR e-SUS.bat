@echo off
chcp 65001 >nul
title Vida+ Clinica  (feche esta janela para PARAR)
cd /d "%~dp0"

echo ============================================================
echo   Vida+ Clinica  -  Sistema de Gestao Clinica
echo ============================================================
echo.
echo [1/3] Iniciando o banco de dados PostgreSQL...
"C:\Users\rafap\pgsql\bin\pg_ctl.exe" -D "C:\Users\rafap\pgdata" -l "C:\Users\rafap\pgdata\server.log" -o "-p 5432" start >nul 2>&1
"C:\Users\rafap\pgsql\bin\pg_isready.exe" -h 127.0.0.1 -p 5432 -t 25 >nul 2>&1
timeout /t 3 /nobreak >nul
echo    OK.
echo.
echo [2/3] O navegador abrira em instantes...
start "" cmd /c "timeout /t 6 /nobreak >nul && start """" http://127.0.0.1:8010"
echo.
echo [3/3] Iniciando o sistema  (http://127.0.0.1:8010)
echo    Login:  medico@ubs.local   Senha: 123456
echo.
echo    >>> Para PARAR: feche esta janela <<<
echo ============================================================
echo.
cd backend
call .venv\Scripts\activate.bat
python -m uvicorn app.main:app --port 8010 --host 127.0.0.1

echo.
echo Sistema encerrado.
"C:\Users\rafap\pgsql\bin\pg_ctl.exe" -D "C:\Users\rafap\pgdata" stop -m fast >nul 2>&1
pause
