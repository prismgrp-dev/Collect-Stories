@echo off
TITLE Setup de Entorno - Script Python
SET VENV_PATH=env

:: 1. Verificar si Python esta instalado en el sistema
echo [LOG] Verificando instalacion de Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta agregado al PATH del sistema.
    echo Por favor, instala Python antes de continuar.
    pause
    exit /b
)

:: 2. Crear el entorno virtual si no existe
if not exist %VENV_PATH% (
    echo [LOG] Creando entorno virtual en %VENV_PATH%...
    python -m venv %VENV_PATH%
) else (
    echo [LOG] El entorno virtual ya existe.
)

:: 3. Activar el entorno virtual
echo [LOG] Activando entorno virtual...
call %VENV_PATH%\Scripts\activate

:: 4. Actualizar pip e instalar librerias
echo [LOG] Actualizando pip...
python -m pip install --upgrade pip

echo [LOG] Instalando librerias desde requirements.txt...
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo [ALERTA] No se encontro requirements.txt. Asegurate de tenerlo en la misma carpeta.
)

:: 5. Instalar navegadores de Playwright
echo [LOG] Instalando navegadores de Playwright...
playwright install

echo.
echo [LOG] Setup completado con exito. Ya puedes iniciar el programa.
pause