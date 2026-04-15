import asyncio
import sys
import os
from pathlib import Path

# Añadir la raíz al path para asegurar que las importaciones funcionen
root_path = os.path.dirname(os.path.abspath(__file__))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# Importar la función principal del script de refresco
# Asegurarse de que el directorio del script esté en el path
script_dir = os.path.join(root_path, "source", "lefty", "refresh_profiles")
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from refresh_profiles.refresh_profiles import main

if __name__ == "__main__":
    # Configuración de plataformas a visitar
    platforms = ["instagram"]
    
    print(f"🚀 Iniciando proceso de refresco de perfiles para: {', '.join(platforms)}")
    
    try:
        asyncio.run(main(platforms))
    except KeyboardInterrupt:
        print("\n🛑 Proceso interrumpido por el usuario.")
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
