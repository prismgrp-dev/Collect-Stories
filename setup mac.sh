#!/bin/bash

# Cambié 'env' a '.venv' para mantener la consistencia con tu archivo iniciar.sh
VENV_PATH=".venv"

echo "[LOG] Verificando instalación de Python 3..."
# En Mac/Linux se utiliza python3 en lugar de python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 no está instalado o no está agregado al PATH del sistema."
    echo "Por favor, instala Python 3 antes de continuar."
    read -p "Presiona Enter para salir..."
    exit 1
fi

# 2. Crear el entorno virtual si no existe
if [ ! -d "$VENV_PATH" ]; then
    echo "[LOG] Creando entorno virtual en $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
else
    echo "[LOG] El entorno virtual ya existe."
fi

# 3. Activar el entorno virtual
echo "[LOG] Activando entorno virtual..."
source "$VENV_PATH/bin/activate"

# 4. Actualizar pip e instalar librerías
echo "[LOG] Actualizando pip..."
python3 -m pip install --upgrade pip

echo "[LOG] Instalando librerías desde requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "[ALERTA] No se encontró requirements.txt. Asegúrate de tenerlo en la misma carpeta."
fi

# 5. Instalar navegadores de Playwright
echo "[LOG] Instalando navegadores de Playwright..."
# Si tu Mac se congela igual que el PC, cambia esta línea por: playwright install chromium
playwright install

echo ""
echo "[LOG] Setup completado con éxito. Ya puedes iniciar el programa."
read -p "Presiona Enter para salir..."