#!/bin/bash

# 1. Obligar al terminal a ubicarse en la carpeta exacta de este script
cd "$(dirname "$0")" || exit

VENV_PATH=".venv"
# Asegúrate de que este nombre sea EXACTAMENTE igual al de tu archivo Python
SCRIPT_NAME="refresh_influencers.py"
MARKER_FILE="$VENV_PATH/instalacion_completa.txt"

echo "[LOG] Verificando archivos en: $(pwd)"

# 2. Verificar si existe el entorno virtual
# Nota: En Mac/Linux el activador está en la carpeta 'bin', no en 'Scripts'
if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "[ERROR] No se encontró el entorno virtual en $VENV_PATH."
    echo "Por favor, elimina la carpeta $VENV_PATH si existe y vuelve a crearla."
    read -p "Presiona Enter para salir..."
    exit 1
fi

# 3. Activar el entorno virtual
source "$VENV_PATH/bin/activate"

# 4. Verificar instalación (Marcador)
if [ ! -f "$MARKER_FILE" ]; then
    echo "[ALERTA] Primera ejecución detectada. Configurando dependencias..."
    python3 -m pip install --upgrade pip
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        echo "[ALERTA] No se encontró requirements.txt."
    fi

    playwright install chromium
    echo "Instalado correctamente el $(date)" > "$MARKER_FILE"
    echo "[OK] Configuración terminada."
fi

# 5. Ejecutar el programa principal
if [ -f "$SCRIPT_NAME" ]; then
    echo "[LOG] Iniciando $SCRIPT_NAME..."
    python3 "$SCRIPT_NAME"
else
    echo "[ERROR] CRÍTICO: No se encontró el archivo '$SCRIPT_NAME'."
    echo "Revisa que el nombre esté bien escrito y que el archivo esté en esta misma carpeta."
    read -p "Presiona Enter para salir..."
    exit 1
fi

echo ""
echo "[LOG] Proceso finalizado."
read -p "Presiona Enter para salir..."