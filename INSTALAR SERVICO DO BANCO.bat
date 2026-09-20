@echo off
chcp 65001 >nul
title Instalar o banco do Vida+ Clinica como servico do Windows
cd /d "%~dp0"

rem --- precisa de administrador: se nao for, pede ao Windows (janela "Deseja permitir?" -> Sim) ---
net session >nul 2>&1
if errorlevel 1 (
  echo Pedindo permissao de administrador ao Windows... clique em SIM na janela que abrir.
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

set "PGBIN=C:\Users\rafap\pgsql\bin"
set "PGDATA=C:\Users\rafap\pgdata"
set "PGHOME=C:\Users\rafap\pgsql"
set "SVC=PostgresVidaClinica"
set "CRIEI=0"

echo ============================================================
echo   Banco do Vida+ Clinica como SERVICO do Windows
echo ============================================================
echo.
echo  Por que: hoje o banco e um programa comum. Quando o PC desliga, o Windows
echo  o mata sem aviso e, ao ligar, ele precisa se recuperar (a espera do atalho).
echo  Como SERVICO, o Windows o desliga direito e o liga sozinho no boot.
echo.
echo  O que este script faz, uma unica vez:
echo    1. Para o banco que estiver rodando "solto"
echo    2. Da a conta de servicos do Windows ^(Network Service^) acesso as
echo       pastas do banco ^(%PGDATA% e %PGHOME%^)
echo    3. Registra o servico %SVC% ^(inicio automatico^) e o liga
echo.
echo  Se algo falhar, ele desfaz o que fez e o atalho continua funcionando igual.
echo.
pause

sc query "%SVC%" >nul 2>&1
if not errorlevel 1 (
  echo.
  echo O servico %SVC% ja esta instalado. So vou garantir que esta ligado.
  goto ligar
)

echo.
echo [1/4] Parando o banco que esta rodando solto...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\pg.ps1" stop

echo [2/4] Liberando as pastas do banco para o servico do Windows...
rem *S-1-5-20 = Network Service (o SID funciona em qualquer idioma do Windows).
rem /Q so mostra falhas; se alguma for grave, o servico nao sobe e o passo 4 desfaz tudo.
icacls "%PGDATA%" /grant *S-1-5-20:(OI)(CI)F /T /C /Q
icacls "%PGHOME%" /grant *S-1-5-20:(OI)(CI)RX /T /C /Q

echo [3/4] Registrando o servico...
"%PGBIN%\pg_ctl.exe" register -N "%SVC%" -D "%PGDATA%" -S auto -o "-p 5432"
if errorlevel 1 goto falhou
set "CRIEI=1"

:ligar
echo [4/4] Ligando o servico e esperando o banco responder...
net start "%SVC%" >nul 2>&1
set "N=0"

:espera
"%PGBIN%\pg_isready.exe" -h 127.0.0.1 -p 5432 -t 2 >nul 2>&1
if not errorlevel 1 goto ok
rem servico que morreu na partida = falha imediata (nao esperar 2 minutos a toa)
powershell -NoProfile -Command "if ((Get-Service '%SVC%' -ErrorAction SilentlyContinue).Status -eq 'Stopped') { exit 1 }" >nul 2>&1
if errorlevel 1 goto falhou
set /a N+=1
if %N% GEQ 40 goto falhou
timeout /t 3 /nobreak >nul
goto espera

:ok
echo.
echo ============================================================
echo  PRONTO! O banco agora e um servico do Windows.
echo  De agora em diante: pode desligar o PC normalmente e usar o
echo  atalho "Vida+ Clinica" sempre que quiser - sem esperar.
echo ============================================================
echo.
echo  ^(Para desfazer um dia: pare o servico em "Servicos" do Windows e rode
echo   "%PGBIN%\pg_ctl.exe" unregister -N %SVC% ^)
echo.
pause
exit /b 0

:falhou
echo.
echo ============================================================
echo  NAO FOI POSSIVEL concluir a instalacao do servico.
echo ============================================================
if "%CRIEI%"=="1" (
  echo  Desfazendo o registro do servico para nao deixar nada pela metade...
  net stop "%SVC%" >nul 2>&1
  "%PGBIN%\pg_ctl.exe" unregister -N "%SVC%" >nul 2>&1
)
echo  Nada quebrou: o atalho "Vida+ Clinica" continua funcionando como antes.
echo  Copie o que apareceu nesta janela e me mande que eu resolvo.
echo.
pause
exit /b 1
