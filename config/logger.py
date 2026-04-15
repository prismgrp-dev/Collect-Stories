import logging
import os
import glob


# --- 0) Limpieza de logs anteriores ---
os.makedirs("logs", exist_ok=True)
for path in glob.glob("logs/*.log"):
    try:
        os.remove(path)
    except PermissionError:
        # otro proceso lo tiene abierto, lo dejamos
        continue
    except OSError:
        # falla distinta (p.ej. ruta inválida), la volvemos a lanzar
        raise

# --- 1) Filtro para INFO - SIEMPRE permite todos los logs ---
class InfoFilter(logging.Filter):
    def filter(self, record):
        # Permitir TODOS los niveles de log (INFO, WARNING, ERROR, CRITICAL)
        return True

# --- 2) Formateador común ---
formatter = logging.Formatter(
    fmt="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# --- 3) Handler de consola (INFO+ con filtro) ---
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
console_handler.addFilter(InfoFilter())

class FileFilter(logging.Filter):
    def filter(self, record):
        # Permitir TODOS los niveles de log (INFO, WARNING, ERROR, CRITICAL)
        return True

# --- 4) Factory de loggers ---
def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    # FileHandler específico para este logger
    fh = logging.FileHandler(f"logs/{name}.log", mode="w", encoding="utf-8")
    fh.setLevel(logging.INFO)         # Guarda ERROR+ en el archivo
    fh.setFormatter(formatter)
    fh.addFilter(FileFilter())  
    logger.addHandler(fh)

    # Siempre opcional: la salida a consola
    logger.addHandler(console_handler)

    # 3) Flag para rastrear errores
    logger.error_occurred = False

    # 4) Un handler que levante ese flag
    class ErrorFlagHandler(logging.Handler):
        def emit(self, record):
            logger.error_occurred = True

    eh = ErrorFlagHandler()
    eh.setLevel(logging.ERROR)
    logger.addHandler(eh)

    return logger

# --- 5) Instancia tus 3 loggers ---
logger_traackr   = get_logger("traackr")
logger_lefty     = get_logger("lefty")
logger_talwalker = get_logger("talkwalker")
logger_general = get_logger("general")

