@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo ERRO: Python nao encontrado. Instale Python 3.10 ou mais recente.
  pause
  exit /b 1
)
py -c "import requests, yaml" >nul 2>nul
if errorlevel 1 (
  echo Instalando dependencias do radar...
  py -m pip install -r requirements.txt
  if errorlevel 1 (echo Falha ao instalar. & pause & exit /b 1)
)
echo Abrindo RADAR no navegador: http://127.0.0.1:8765
start "" /min cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8765"
py dashboard.py %*
echo.
echo Radar encerrado.
pause
