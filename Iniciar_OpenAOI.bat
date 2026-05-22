@echo off
title Open-AOI Launcher
color 0A

echo ==========================================
echo    INICIANDO SISTEMA OPEN-AOI (MES)
echo ==========================================
echo.

echo [1/5] Verificando motor do Docker...
docker info >nul 2>&1
if %errorlevel% equ 0 goto DOCKER_RUNNING

echo [!] Docker nao esta rodando. Iniciando Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
echo Aguardando o Docker inicializar (isso pode levar alguns segundos)...

:WAIT_DOCKER
timeout /t 3 /nobreak >nul
docker info >nul 2>&1
if errorlevel 1 goto WAIT_DOCKER
echo [OK] Docker iniciado com sucesso!
goto START_CONTAINER

:DOCKER_RUNNING
echo [OK] Docker ja esta em execucao.

:START_CONTAINER
echo.
echo [2/5] Iniciando o motor do Open-AOI...
docker start aoi-ros2 aoi-mysql aoi-minio aoi-adminer >nul 2>&1

echo.
echo [3/5] Aguardando o servidor web estabilizar...
timeout /t 6 /nobreak >nul

echo.
echo [4/5] Abrindo Interface do Operador...
start chrome --app=http://localhost:10006

echo.
echo [5/5] Vigiando a janela para desligamento automatico...

:MONITOR_JANELA
timeout /t 3 /nobreak >nul
tasklist /v /FI "IMAGENAME eq chrome.exe" | find /i "Automated Optical Inspection - Tecnnic" >nul
if %errorlevel% equ 0 goto MONITOR_JANELA

:: --- SE CHEGOU AQUI, A JANELA FECHOU ---
echo.
echo ==========================================
echo [!] Janela do aplicativo fechada.
echo Iniciando o desligamento do motor...
echo ==========================================

:: Removido o >nul 2>&1 para vermos o que o Docker vai responder
docker stop aoi-ros2 aoi-mysql aoi-minio aoi-adminer

echo.
echo [OK] Processo de encerramento finalizado. O terminal fechara em 5 segundos.
timeout /t 5 /nobreak >nul
exit