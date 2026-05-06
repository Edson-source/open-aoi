@echo off
echo ===================================================
echo   Iniciando Servidor da Camera...
echo ===================================================


:: 1. Inicia o servidor da camera em uma nova janela (para você ver os logs, se quiser)
echo [1/1] Iniciando Camera Server...
start "Camera Server" cmd /c "python camera_server.py"

echo ===================================================
echo   Sistema Online!
echo   Acesse: http://127.0.0.1:5000/video
echo ===================================================
pause