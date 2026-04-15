@echo off
:: 1. Obligar al CMD a ubicarse en la carpeta exacta de este script
cd /d "%~dp0"
TITLE Iniciar Programa - Automatizado

SET VENV_PATH=.venv
:: Asegurate de que este nombre sea EXACTAMENTE igual al de tu archivo Python
SET SCRIPT_NAME=refresh_influencers.py
SET MARKER_FILE=%VENV_PATH%\instalacion_completa.txt

echo [LOG] Verificando archivos en: %CD%

:: 2. Verificar si existe el entorno virtual
if not exist %VENV_PATH%\Scripts\activate (
    echo [ERROR] No se encontro el entorno virtual en %VENV_PATH%.
    echo Por favor, elimina la carpeta %VENV_PATH% si existe y vuelve a ejecutar.
    pause
    exit /b
)

:: 3. Activar el entorno virtual
call %VENV_PATH%\Scripts\activate

:: 4. Verificar instalacion (Marcador)
if not exist "%MARKER_FILE%" (
    echo [ALERTA] Primera ejecucion detectada. Configurando dependencias...
    python -m pip install --upgrade pip
    
    if exist requirements.txt (
        pip install -r requirements.txt
    ) else (
        echo [ALERTA] No se encontro requirements.txt.
    )

    playwright install chromium
    echo Instalado correctamente el %date% > "%MARKER_FILE%"
    echo [OK] Configuracion terminada.
)

:: 5. Ejecutar el programa principal
if exist "%SCRIPT_NAME%" (
    echo [LOG] Iniciando %SCRIPT_NAME%...
    python "%SCRIPT_NAME%"
) else (
    echo [ERROR] CRITICO: No se encontro el archivo "%SCRIPT_NAME%". 
    echo Revisa que el nombre este bien escrito y que el archivo este en esta misma carpeta.
    pause
    exit /b
)

echo.
echo [LOG] Proceso finalizado.
pause