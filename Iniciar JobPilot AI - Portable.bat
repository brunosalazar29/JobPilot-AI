@echo off
setlocal

title JobPilot AI - Portable

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

echo.
echo ============================================================
echo  JobPilot AI
echo  Arranque portable: frontend, backend, worker, redis y SQL Server
echo ============================================================
echo.

if not exist "%PROJECT_DIR%\docker-compose.yml" (
  echo ERROR: No se encontro docker-compose.yml en:
  echo "%PROJECT_DIR%"
  echo.
  pause
  exit /b 1
)

where docker >nul 2>nul
if errorlevel 1 (
  echo ERROR: Docker no esta disponible en este equipo.
  echo Abre Docker Desktop y vuelve a ejecutar este archivo.
  echo.
  pause
  exit /b 1
)

docker compose version >nul 2>nul
if errorlevel 1 (
  echo ERROR: Tu instalacion de Docker no tiene disponible "docker compose".
  echo Actualiza Docker Desktop y vuelve a intentarlo.
  echo.
  pause
  exit /b 1
)

cd /d "%PROJECT_DIR%"

if not exist ".env" (
  if exist ".env.example" (
    copy ".env.example" ".env" >nul
    echo Archivo .env creado desde .env.example
  )
)

for /f %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=3000; while(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue){$p++}; $p"') do set "FRONTEND_PORT=%%P"
for /f %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=8011; while(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue){$p++}; $p"') do set "BACKEND_PORT=%%P"
for /f %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=1433; while(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue){$p++}; $p"') do set "SQLSERVER_PORT=%%P"
for /f %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=6379; while(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue){$p++}; $p"') do set "REDIS_PORT=%%P"

set "FRONTEND_URL=http://localhost:%FRONTEND_PORT%"
set "BACKEND_DOCS=http://localhost:%BACKEND_PORT%/docs"

echo Frontend: %FRONTEND_URL%
echo Backend docs: %BACKEND_DOCS%
echo.
echo Puertos asignados:
echo  frontend  localhost:%FRONTEND_PORT%  -> contenedor:3000
echo  backend   localhost:%BACKEND_PORT%   -> contenedor:8000
echo  sqlserver localhost:%SQLSERVER_PORT% -> contenedor:1433
echo  redis     localhost:%REDIS_PORT%     -> contenedor:6379
echo.
echo Presiona Ctrl+C en esta ventana para detener los servicios.
echo.

start "" powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 25; Start-Process '%FRONTEND_URL%'; Start-Sleep -Seconds 3; Start-Process '%BACKEND_DOCS%'"

docker compose up --build

echo.
echo Docker Compose finalizo.
pause
