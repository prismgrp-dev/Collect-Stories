import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class ExecutionPhase(Enum):
    IDLE = "idle"
    QUEUED = "queued"
    INITIALIZING = "initializing"
    DOWNLOADING = "downloading"
    UPLOAD_DIRECTORY = "Uploading directory"
    MAPPING = "mapping"
    UPLOADING = "uploading"
    PROCESSING_STORIES = "Processing stories"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class StoryProgress:
    current_row: int = 0
    total_rows: int = 0
    current_story_id: str = ""
    processed_stories: int = 0
    failed_stories: int = 0

@dataclass
class UploadProgress:
    posts_uploaded: int = 0
    total_posts: int = 0
    current_table: str = ""
    tables_completed: List[str] = None
    
    def __post_init__(self):
        if self.tables_completed is None:
            self.tables_completed = []

@dataclass
class DirectoryProgress:
    processed_rows: int = 0
    total_rows: int = 0

@dataclass
class PlatformProgress:
    platform: str
    phase: ExecutionPhase = ExecutionPhase.IDLE
    start_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    
    # Download progress
    downloads_completed: int = 0
    total_downloads: int = 0
    current_download: str = ""
    
    # Upload progress
    upload_progress: UploadProgress = None
    
    # Stories progress
    story_progress: StoryProgress = None

    # Stories progress
    directory_progress: DirectoryProgress = None
    
    # General info
    items_count: int = 0
    current_item: str = ""
    error_message: str = ""
    logs: List[str] = None
    
    # Timing tracking for adaptive estimates
    phase_start_times: Dict[str, datetime] = None
    phase_durations: Dict[str, float] = None  # En minutos
    
    def __post_init__(self):
        if self.upload_progress is None:
            self.upload_progress = UploadProgress()
        if self.story_progress is None:
            self.story_progress = StoryProgress()
        if self.directory_progress is None:
            self.directory_progress = DirectoryProgress()
        if self.logs is None:
            self.logs = []
        if self.phase_start_times is None:
            self.phase_start_times = {}
        if self.phase_durations is None:
            self.phase_durations = {}

class ProgressReporter:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.progress_file = os.path.join(os.getcwd(), "data", "progress_status.json")
            self.platforms: Dict[str, PlatformProgress] = {}
            self._file_lock = threading.Lock()
            self._initialized = True
            # Tiempos base estimados (en minutos por unidad)
            self.base_time_estimates = {
                "Lefty": {
                    ExecutionPhase.DOWNLOADING: 3.2,        # 10 minutos 20 segundos por item
                    ExecutionPhase.UPLOADING: 1.3,          # 1 minuto 30 segundos por fila
                    ExecutionPhase.PROCESSING_STORIES: 1.6, # 1 minuto 60 segundos (2 minutos) por fila
                    ExecutionPhase.UPLOAD_DIRECTORY: 3.4,   # 7 minutos 40 segundos por fila
                },
                "Traackr": {
                    ExecutionPhase.DOWNLOADING: 2.1,        # 2 minutos 10 segundos por fila
                    ExecutionPhase.UPLOADING: 1.6,          # 1 minuto 60 segundos (2 minutos) por fila  
                    ExecutionPhase.PROCESSING_STORIES: 2.7, # 3 minutos 70 segundos (4 min 10 seg) por fila
                    ExecutionPhase.UPLOAD_DIRECTORY: 2.5,   # 6 minutos 50 segundos por fila
                },
                "Talkwalker": {
                    ExecutionPhase.DOWNLOADING: 2.5,        # 2 minutos 50 segundos por fila
                    ExecutionPhase.UPLOADING: 1.4,          # 1 minuto 40 segundos por fila
                    ExecutionPhase.UPLOAD_DIRECTORY: 1.1,   # 5 minutos 10 segundos por fila
                }
            }
            
            # Tiempos predeterminados para cada fase cuando no hay datos (en formato M.SS)
            self.default_phase_times = {
                "Lefty": {
                    ExecutionPhase.DOWNLOADING: 4.4,        # 15 minutos
                    ExecutionPhase.UPLOADING: 2.33,          # 5 minutos 33 segundos
                    ExecutionPhase.PROCESSING_STORIES: 8.2, # 8 minutos 15 segundos
                    ExecutionPhase.UPLOAD_DIRECTORY: 2.10,  # 12 minutos 30 segundos
                },
                "Traackr": {
                    ExecutionPhase.DOWNLOADING: 10.2,        # 10 minutos
                    ExecutionPhase.UPLOADING: 5.45,          # 7 minutos 45 segundos
                    ExecutionPhase.PROCESSING_STORIES: 15.22,# 15 minutos 20 segundos
                    ExecutionPhase.UPLOAD_DIRECTORY: 2.0,   # 20 minutos
                },
                "Talkwalker": {
                    ExecutionPhase.DOWNLOADING: 2.30,        # 8 minutos 30 segundos
                    ExecutionPhase.UPLOADING: 1.15,          # 6 minutos 15 segundos
                    ExecutionPhase.UPLOAD_DIRECTORY: 1.2,  # 10 minutos 45 segundos
                }
            }
            
            # Tiempos adaptativos que se actualizan según el rendimiento real
            self.adaptive_time_estimates = self.base_time_estimates.copy()
            
            # Historial de rendimiento para mejorar estimaciones
            self.performance_history = {}
            
            # Cargar datos existentes al inicializar
            self._load_from_file()

    def _convert_time_format_to_minutes(self, time_value: float) -> float:
        """Convierte del formato M.SS a minutos decimales
        Ej: 2.5 (2 min 50 seg) -> 2.833333 minutos"""
        minutes = int(time_value)
        seconds = round((time_value - minutes) * 100)
        # Manejar casos donde los segundos sean 60 o más
        if seconds >= 60:
            minutes += seconds // 60
            seconds = seconds % 60
        return minutes + (seconds / 60.0)
    
    def _convert_minutes_to_time_format(self, minutes: float) -> Dict[str, int]:
        """Convierte minutos decimales a formato legible
        Ej: 2.833333 minutos -> {'minutes': 2, 'seconds': 50}"""
        total_seconds = int(minutes * 60)
        return {
            'minutes': total_seconds // 60,
            'seconds': total_seconds % 60
        }
    
    def _format_time_string(self, minutes: float) -> str:
        """Formatea minutos decimales a string legible
        Ej: 2.833333 -> "2m 50s"
        Ej: 123.57 -> "2h 3m 25s"
        """
        time_dict = self._convert_minutes_to_time_format(minutes)
        
        hours = time_dict.get('hours', 0)
        mins = time_dict['minutes']
        secs = time_dict['seconds']
        
        parts = []
        if hours:
            parts.append(f"{hours}h")
        if mins or hours:  # Mostrar minutos si hay horas, incluso si mins == 0
            parts.append(f"{mins}m")
        parts.append(f"{secs}s")
        
        return ' '.join(parts)

    
    def _save_to_file(self):
        """Guarda el estado actual a archivo JSON"""
        with self._file_lock:
            try:
                data = {}
                for platform, progress in self.platforms.items():
                    # Convertir datetime en phase_start_times para serialización
                    phase_start_times_iso = {}
                    if progress.phase_start_times:
                        for phase_key, dt in progress.phase_start_times.items():
                            phase_start_times_iso[phase_key] = dt.isoformat() if dt else None
                    
                    data[platform] = {
                        **asdict(progress),
                        'phase': progress.phase.value,
                        'start_time': progress.start_time.isoformat() if progress.start_time else None,
                        'last_update': progress.last_update.isoformat() if progress.last_update else None,
                        'phase_start_times': phase_start_times_iso,
                    }
                
                # Agregar estimaciones adaptativas y historial de rendimiento
                # Convertir enums a strings en adaptive_time_estimates
                serializable_estimates = {}
                for platform, phases in self.adaptive_time_estimates.items():
                    serializable_estimates[platform] = {}
                    for phase, time_val in phases.items():
                        phase_key = phase.value if hasattr(phase, 'value') else str(phase)
                        serializable_estimates[platform][phase_key] = time_val
                
                data['_adaptive_estimates'] = serializable_estimates
                data['_performance_history'] = self.performance_history
                
                # Validar que los datos son serializables antes de escribir
                json_str = json.dumps(data, ensure_ascii=False, indent=2)
                
                with open(self.progress_file, 'w', encoding='utf-8') as f:
                    f.write(json_str)
            except Exception as e:
                print(f"Error saving progress to file: {e}")
    
    def _load_from_file(self):
        """Carga el estado desde archivo JSON"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Cargar estimaciones adaptativas y historial de rendimiento
                if '_adaptive_estimates' in data:
                    estimates_data = data.pop('_adaptive_estimates')
                    self.adaptive_time_estimates = {}
                    for platform, phases in estimates_data.items():
                        self.adaptive_time_estimates[platform] = {}
                        for phase_str, time_val in phases.items():
                            # Convertir string de vuelta a enum
                            try:
                                phase_enum = ExecutionPhase(phase_str)
                                self.adaptive_time_estimates[platform][phase_enum] = time_val
                            except ValueError:
                                # Si no se puede convertir, mantener como string
                                self.adaptive_time_estimates[platform][phase_str] = time_val
                if '_performance_history' in data:
                    self.performance_history = data.pop('_performance_history')
                
                for platform, progress_data in data.items():
                    # Saltar claves especiales que no son plataformas
                    if platform.startswith('_'):
                        continue
                        
                    # Convertir datetime strings back to datetime objects
                    if progress_data.get('start_time'):
                        progress_data['start_time'] = datetime.fromisoformat(progress_data['start_time'])
                    if progress_data.get('last_update'):
                        progress_data['last_update'] = datetime.fromisoformat(progress_data['last_update'])
                    
                    # Convertir phase_start_times back to datetime objects
                    phase_start_times = {}
                    if progress_data.get('phase_start_times'):
                        for phase_key, iso_string in progress_data['phase_start_times'].items():
                            if iso_string:
                                phase_start_times[phase_key] = datetime.fromisoformat(iso_string)
                        progress_data['phase_start_times'] = phase_start_times
                    
                    # Convertir phase string back to enum
                    progress_data['phase'] = ExecutionPhase(progress_data['phase'])
                    
                    # Recrear objetos dataclass
                    upload_data = progress_data.pop('upload_progress', {})
                    story_data = progress_data.pop('story_progress', {})
                    directory_data = progress_data.pop('directory_progress', {})
                    
                    self.platforms[platform] = PlatformProgress(
                        **progress_data,
                        upload_progress=UploadProgress(**upload_data),
                        story_progress=StoryProgress(**story_data),
                        directory_progress=DirectoryProgress(**directory_data)
                    )
            except json.JSONDecodeError as e:
                print(f"Error loading progress from file - Invalid JSON: {e}")
                # Crear backup del archivo corrupto y reinicializar
                backup_file = f"{self.progress_file}.corrupted_{int(time.time())}"
                try:
                    os.rename(self.progress_file, backup_file)
                    print(f"Archivo corrupto movido a: {backup_file}")
                except Exception:
                    pass
            except Exception as e:
                print(f"Error loading progress from file: {e}")
    
    def initialize_platform(self, platform: str, items_count: int = 0):
        """Inicializa el progreso para una plataforma"""
        self.platforms[platform] = PlatformProgress(
            platform=platform,
            phase=ExecutionPhase.QUEUED,
            items_count=items_count,
            start_time=datetime.now(),
            last_update=datetime.now()
        )
        self._save_to_file()
    
    def update_phase(self, platform: str, phase: ExecutionPhase, message: str = ""):
        """Actualiza la fase actual de ejecución"""
        if platform in self.platforms:
            current_time = datetime.now()
            previous_phase = self.platforms[platform].phase
            
            # Registrar duración de la fase anterior si no es la primera fase
            if previous_phase != ExecutionPhase.IDLE and previous_phase != ExecutionPhase.QUEUED:
                phase_key = previous_phase.value
                if phase_key in self.platforms[platform].phase_start_times:
                    start_time = self.platforms[platform].phase_start_times[phase_key]
                    duration_minutes = (current_time - start_time).total_seconds() / 60
                    self.platforms[platform].phase_durations[phase_key] = duration_minutes
                    
                    # Actualizar estimaciones adaptativas
                    self._update_adaptive_estimates(platform, previous_phase, duration_minutes)
            
            # Actualizar a la nueva fase
            self.platforms[platform].phase = phase
            self.platforms[platform].last_update = current_time
            self.platforms[platform].phase_start_times[phase.value] = current_time
            
            if message:
                self.platforms[platform].logs.append(f"{current_time.strftime('%H:%M:%S')} - {message}")
            self._save_to_file()
    
    def update_download_progress(self, platform: str, completed: int, total: int, current_file: str = ""):
        """Actualiza el progreso de descargas"""
        if platform in self.platforms:
            self.platforms[platform].downloads_completed = completed
            self.platforms[platform].total_downloads = total
            self.platforms[platform].current_download = current_file
            self.platforms[platform].last_update = datetime.now()
            self._save_to_file()
    
    def update_upload_progress(self, platform: str, posts_uploaded: int, total_posts: int, current_table: str = ""):
        """Actualiza el progreso de subida"""
        if platform in self.platforms:
            self.platforms[platform].upload_progress.posts_uploaded = posts_uploaded
            self.platforms[platform].upload_progress.total_posts = total_posts
            self.platforms[platform].upload_progress.current_table = current_table
            self.platforms[platform].last_update = datetime.now()
            self._save_to_file()
    
    def complete_table_upload(self, platform: str, table_name: str):
        """Marca una tabla como completada"""
        if platform in self.platforms:
            if table_name not in self.platforms[platform].upload_progress.tables_completed:
                self.platforms[platform].upload_progress.tables_completed.append(table_name)
            self.platforms[platform].last_update = datetime.now()
            self._save_to_file()
    
    def update_story_progress(self, platform: str, current_row: int, total_rows: int, 
                            current_story_id: str = "", processed: int = 0, failed: int = 0):
        """Actualiza el progreso de procesamiento de stories"""
        if platform in self.platforms:
            story_progress = self.platforms[platform].story_progress
            story_progress.current_row = current_row
            story_progress.total_rows = total_rows
            story_progress.current_story_id = current_story_id
            story_progress.processed_stories = processed
            story_progress.failed_stories = failed
            self.platforms[platform].last_update = datetime.now()
            self._save_to_file()
    
    def update_stories_progress(self, platform: str, processed: int, total: int, message: str = ""):
        """Actualiza el progreso de Stories (versión simplificada)"""
        if platform in self.platforms:
            self.platforms[platform].story_progress.processed_stories = processed
            self.platforms[platform].story_progress.total_rows = total
            self.platforms[platform].last_update = datetime.now()
            if message:
                self.add_log(platform, message)
            self._save_to_file()

    def update_directory_progress(self, platform: str, processed: int, total: int, message: str = ""):
        """Actualiza el progreso del directorio"""
        if platform in self.platforms:
            self.platforms[platform].directory_progress.processed_rows = processed
            self.platforms[platform].directory_progress.total_rows = total
            self.platforms[platform].last_update = datetime.now()
            if message:
                self.add_log(platform, message)
            self._save_to_file()
    
    def add_log(self, platform: str, message: str, level: str = "info"):
        """Añade un log al progreso de la plataforma"""
        if platform in self.platforms:
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_entry = f"[{level.upper()}] {timestamp} - {message}"
            self.platforms[platform].logs.append(log_entry)
            
            # Mantener solo los últimos 50 logs
            if len(self.platforms[platform].logs) > 50:
                self.platforms[platform].logs = self.platforms[platform].logs[-50:]
            
            self.platforms[platform].last_update = datetime.now()
            self._save_to_file()
    
    def set_error(self, platform: str, error_message: str):
        """Marca la plataforma como error con mensaje"""
        if platform in self.platforms:
            self.platforms[platform].phase = ExecutionPhase.ERROR
            self.platforms[platform].error_message = error_message
            self.platforms[platform].last_update = datetime.now()
            self.add_log(platform, f"ERROR: {error_message}", "error")
            self._save_to_file()
    
    def complete_platform(self, platform: str, message: str = ""):
        """Marca la plataforma como completada"""
        if platform in self.platforms:
            self.platforms[platform].phase = ExecutionPhase.COMPLETED
            self.platforms[platform].last_update = datetime.now()
            if message:
                self.add_log(platform, f"COMPLETED: {message}", "success")
            self._save_to_file()
    
    def reset_platform(self, platform: str):
        """Resetea el estado de una plataforma"""
        if platform in self.platforms:
            del self.platforms[platform]
            self._save_to_file()
    
    def get_status(self, platform: str = None) -> Dict:
        """Obtiene el estado actual de una plataforma o todas"""
        self._load_from_file()  # Cargar estado más reciente
        
        if platform:
            if platform in self.platforms:
                progress = self.platforms[platform]
                
                # Calcular tiempo estimado restante
                estimated_remaining = self._calculate_estimated_time(progress)
                
                # Calcular progreso general
                overall_progress = self._calculate_overall_progress(progress)
                
                return {
                    'platform': progress.platform,
                    'phase': progress.phase.value,
                    'start_time': progress.start_time.isoformat() if progress.start_time else None,
                    'last_update': progress.last_update.isoformat() if progress.last_update else None,
                    'downloads': {
                        'completed': progress.downloads_completed,
                        'total': progress.total_downloads,
                        'current': progress.current_download,
                        'progress_percent': self._calculate_percent(progress.downloads_completed, progress.total_downloads)
                    },
                    'uploads': {
                        'posts_uploaded': progress.upload_progress.posts_uploaded,
                        'total_posts': progress.upload_progress.total_posts,
                        'current_table': progress.upload_progress.current_table,
                        'tables_completed': progress.upload_progress.tables_completed,
                        'progress_percent': self._calculate_percent(progress.upload_progress.posts_uploaded, progress.upload_progress.total_posts)
                    },
                    'stories': {
                        'current_row': progress.story_progress.current_row,
                        'total_rows': progress.story_progress.total_rows,
                        'current_story_id': progress.story_progress.current_story_id,
                        'processed': progress.story_progress.processed_stories,
                        'failed': progress.story_progress.failed_stories,
                        'progress_percent': self._calculate_percent(progress.story_progress.processed_stories, progress.story_progress.total_rows)
                    },
                    'directory' : {
                        'current_row': progress.directory_progress.processed_rows,
                        'total_rows': progress.directory_progress.total_rows
                    },
                    'items_count': progress.items_count,
                    'current_item': progress.current_item,
                    'error_message': progress.error_message,
                    'logs': progress.logs if progress.logs else [],  # Últimos 10 logs
                    'time_estimation': estimated_remaining,
                    'overall_progress_percent': overall_progress,
                    'execution_summary': self._get_execution_summary(progress),
                    'adaptive_estimates': {
                        phase.value if hasattr(phase, 'value') else str(phase): time_val
                        for phase, time_val in self.adaptive_time_estimates.get(progress.platform, {}).items()
                    },
                    'performance_history': self._get_recent_performance(progress.platform)
                }
            return {'platform': platform, 'phase': 'not_found'}
        else:
            # Retornar estado de todas las plataformas
            result = {}
            for plat, progress in self.platforms.items():
                result[plat] = self.get_status(plat)
            return result
    
    def _calculate_percent(self, completed: int, total: int) -> float:
        """Calcula el porcentaje de progreso"""
        if total == 0:
            return 0.0
        return round((completed / total) * 100, 2)
    
    def _calculate_estimated_time(self, progress: PlatformProgress) -> Optional[Dict[str, Any]]:
        """Calcula el tiempo estimado restante como cuenta regresiva"""
        if not progress.start_time or progress.phase in [ExecutionPhase.COMPLETED, ExecutionPhase.ERROR]:
            return None
        
        platform = progress.platform
        current_phase = progress.phase
        now = datetime.now()
        
        # Usar estimaciones adaptativas si están disponibles, sino usar base
        estimates = self.adaptive_time_estimates.get(platform, self.base_time_estimates.get(platform, {}))
        default_times = self.default_phase_times.get(platform, {})
        
        if not estimates:
            return None
            
        total_estimated_minutes = 0
        remaining_minutes = 0
        current_phase_remaining = 0
        
        # Si la fase actual está en los tiempos predeterminados y no hay datos de progreso
        if current_phase in default_times:
            # Verificar si hay datos de progreso para la fase actual
            has_progress_data = False
            
            if current_phase == ExecutionPhase.DOWNLOADING and progress.total_downloads > 0:
                has_progress_data = True
            elif current_phase == ExecutionPhase.UPLOADING and progress.upload_progress.total_posts > 0:
                has_progress_data = True
            elif current_phase == ExecutionPhase.PROCESSING_STORIES and progress.story_progress.total_rows > 0:
                has_progress_data = True
            elif current_phase == ExecutionPhase.UPLOAD_DIRECTORY and progress.directory_progress.total_rows > 0:
                has_progress_data = True
            
            # Si no hay datos de progreso, usar tiempo predeterminado
            if not has_progress_data:
                default_time = self._convert_time_format_to_minutes(default_times[current_phase])
                
                # Calcular tiempo transcurrido desde el inicio de la fase
                if current_phase.value in progress.phase_start_times:
                    start_time = progress.phase_start_times[current_phase.value]
                    elapsed_minutes = (now - start_time).total_seconds() / 60
                    current_phase_remaining = max(0, default_time - elapsed_minutes)
                else:
                    current_phase_remaining = default_time
        
        # Si hay datos de progreso, calcular basado en el progreso real
        if current_phase_remaining == 0:  # Solo si no se usó tiempo predeterminado
            if current_phase == ExecutionPhase.DOWNLOADING:
                completed = progress.downloads_completed
                total = progress.total_downloads
                time_per_unit = self._convert_time_format_to_minutes(estimates.get(ExecutionPhase.DOWNLOADING, 0))
                
                if total > 0:
                    print(current_phase_remaining)
                    current_phase_remaining = (total - completed) * time_per_unit
                    
            elif current_phase == ExecutionPhase.UPLOADING:
                completed = progress.upload_progress.posts_uploaded
                total = progress.upload_progress.total_posts
                time_per_unit = self._convert_time_format_to_minutes(estimates.get(ExecutionPhase.UPLOADING, 0))
                
                if total > 0:
                    current_phase_remaining = (total - completed) * time_per_unit
                    
            elif current_phase == ExecutionPhase.PROCESSING_STORIES:
                completed = progress.story_progress.processed_stories
                total = progress.story_progress.total_rows
                time_per_unit = self._convert_time_format_to_minutes(estimates.get(ExecutionPhase.PROCESSING_STORIES, 0))
                
                if total > 0:
                    current_phase_remaining = (total - completed) * time_per_unit

            elif current_phase == ExecutionPhase.UPLOAD_DIRECTORY:
                completed = progress.directory_progress.processed_rows
                total = progress.directory_progress.total_rows
                time_per_unit = self._convert_time_format_to_minutes(estimates.get(ExecutionPhase.UPLOAD_DIRECTORY, 0))
                
                if total > 0:
                    current_phase_remaining = (total - completed) * time_per_unit
        
        # Calcular tiempo para fases futuras
        future_phases_time = 0
        
        # Definir orden de fases
        phase_order = [
            ExecutionPhase.DOWNLOADING,
            ExecutionPhase.UPLOAD_DIRECTORY,
            ExecutionPhase.UPLOADING,
            ExecutionPhase.PROCESSING_STORIES,
        ]
        
        current_phase_index = None
        try:
            current_phase_index = phase_order.index(current_phase)
        except ValueError:
            current_phase_index = 0
            
        # Sumar tiempo estimado de fases futuras
        for i in range(current_phase_index + 1, len(phase_order)):
            future_phase = phase_order[i]
            
            # Saltar PROCESSING_STORIES para Talkwalker
            if platform == "Talkwalker" and future_phase == ExecutionPhase.PROCESSING_STORIES:
                continue
            
            # Verificar si hay datos para las fases futuras
            has_future_data = False
            future_total = 0
            
            if future_phase == ExecutionPhase.DOWNLOADING:
                has_future_data = progress.total_downloads > 0
                future_total = progress.total_downloads
            elif future_phase == ExecutionPhase.UPLOADING:
                has_future_data = progress.upload_progress.total_posts > 0
                future_total = progress.upload_progress.total_posts
            elif future_phase == ExecutionPhase.PROCESSING_STORIES:
                has_future_data = progress.story_progress.total_rows > 0
                future_total = progress.story_progress.total_rows
            elif future_phase == ExecutionPhase.UPLOAD_DIRECTORY:
                has_future_data = progress.directory_progress.total_rows > 0
                future_total = progress.directory_progress.total_rows
            
            # Si hay datos, usar cálculo basado en unidades, sino usar tiempo predeterminado
            if has_future_data and future_total > 0:
                time_per_unit = self._convert_time_format_to_minutes(estimates.get(future_phase, 0))
                future_phases_time += future_total * time_per_unit
            elif future_phase in default_times:
                future_phases_time += self._convert_time_format_to_minutes(default_times[future_phase])
        
        total_remaining = current_phase_remaining + future_phases_time
        
        # Calcular tiempo transcurrido desde el inicio de la fase actual
        current_phase_elapsed = 0
        if current_phase.value in progress.phase_start_times:
            start_time = progress.phase_start_times[current_phase.value]
            current_phase_elapsed = (now - start_time).total_seconds() / 60
        
        return {
            'total_remaining_minutes': total_remaining,
            'current_phase_remaining_minutes': round(current_phase_remaining, 1),
            'current_phase_elapsed_minutes': round(current_phase_elapsed, 1),
            'future_phases_minutes': round(future_phases_time, 1),
            'estimated_completion_time': (now + timedelta(minutes=total_remaining)).isoformat() if total_remaining > 0 else None,
            'breakdown': {
                'downloading': {
                    'completed': progress.downloads_completed,
                    'total': progress.total_downloads,
                    'time_per_unit': estimates.get(ExecutionPhase.DOWNLOADING, 0)
                },
                'directory': {
                    'completed': progress.directory_progress.processed_rows,
                    'total': progress.directory_progress.total_rows,
                    'time_per_unit': estimates.get(ExecutionPhase.DOWNLOADING, 0)
                },
                'uploading': {
                    'completed': progress.upload_progress.posts_uploaded,
                    'total': progress.upload_progress.total_posts,
                    'time_per_unit': estimates.get(ExecutionPhase.UPLOADING, 0)
                },
                'processing_stories': {
                    'completed': progress.story_progress.processed_stories,
                    'total': progress.story_progress.total_rows,
                    'time_per_unit': estimates.get(ExecutionPhase.PROCESSING_STORIES, 0)
                } if platform != "Talkwalker" else None
            }
        }
    
    def _calculate_overall_progress(self, progress: PlatformProgress) -> float:
        """Calcula el progreso general de la plataforma"""
        if progress.phase == ExecutionPhase.COMPLETED:
            return 100.0
        elif progress.phase == ExecutionPhase.ERROR:
            return 0.0
        
        # Pesos para cada fase
        phase_weights = {
            ExecutionPhase.QUEUED: 0,
            ExecutionPhase.INITIALIZING: 5,
            ExecutionPhase.DOWNLOADING: 10,
            ExecutionPhase.UPLOAD_DIRECTORY: 30,
            ExecutionPhase.MAPPING: 40,
            ExecutionPhase.UPLOADING: 45,
            ExecutionPhase.PROCESSING_STORIES: 60,
        }
        
        base_progress = phase_weights.get(progress.phase, 0)
        
        # Ajustar según el progreso específico de la fase
        if progress.phase == ExecutionPhase.DOWNLOADING and progress.total_downloads > 0:
            download_progress = (progress.downloads_completed / progress.total_downloads) * 25
            return base_progress + download_progress
        elif progress.phase == ExecutionPhase.UPLOADING and progress.upload_progress.total_posts > 0:
            upload_progress = (progress.upload_progress.posts_uploaded / progress.upload_progress.total_posts) * 30
            return base_progress + upload_progress
        elif progress.phase == ExecutionPhase.PROCESSING_STORIES and progress.story_progress.total_rows > 0:
            story_progress = (progress.story_progress.processed_stories / progress.story_progress.total_rows) * 15
            return base_progress + story_progress
        elif progress.phase == ExecutionPhase.UPLOAD_DIRECTORY and progress.directory_progress.total_rows > 0:
            directory_progress = (progress.directory_progress.processed_rows / progress.directory_progress.total_rows) * 15
            return base_progress + directory_progress
        
        return float(base_progress)
    
    def _get_execution_summary(self, progress: PlatformProgress) -> Dict:
        """Genera un resumen detallado de la ejecución"""
        summary = {
            'total_items': progress.items_count,
            'current_phase': progress.phase.value,
            'downloads': {
                'completed': progress.downloads_completed,
                'total': progress.total_downloads,
                'remaining': max(0, progress.total_downloads - progress.downloads_completed)
            },
            'posts': {
                'uploaded': progress.upload_progress.posts_uploaded,
                'total': progress.upload_progress.total_posts,
                'remaining': max(0, progress.upload_progress.total_posts - progress.upload_progress.posts_uploaded)
            },
            'stories': {
                'processed': progress.story_progress.processed_stories,
                'total': progress.story_progress.total_rows,
                'remaining': max(0, progress.story_progress.total_rows - progress.story_progress.processed_stories),
                'failed': progress.story_progress.failed_stories
            },
            'execution_time': self._get_execution_time(progress)
        }
        return summary
    
    def _get_execution_time(self, progress: PlatformProgress) -> Dict:
        """Calcula tiempos de ejecución"""
        if not progress.start_time:
            return {'elapsed_minutes': 0, 'status': 'not_started'}
        
        # Use last_update time if execution is finished (completed or error)
        # Otherwise use current time for running processes
        if progress.phase in [ExecutionPhase.COMPLETED, ExecutionPhase.ERROR]:
            end_time = progress.last_update if progress.last_update else datetime.now()
        else:
            end_time = datetime.now()
        
        elapsed_seconds = (end_time - progress.start_time).total_seconds()
        elapsed_minutes = round(elapsed_seconds / 60, 1)
        
        return {
            'elapsed_minutes': elapsed_minutes,
            'status': 'running' if progress.phase not in [ExecutionPhase.COMPLETED, ExecutionPhase.ERROR] else 'finished'
        }
    
    def is_platform_running(self, platform: str) -> bool:
        """Verifica si una plataforma está ejecutándose"""
        if platform in self.platforms:
            return self.platforms[platform].phase not in [
                ExecutionPhase.IDLE, 
                ExecutionPhase.COMPLETED, 
                ExecutionPhase.ERROR
            ]
        return False
    
    def _update_adaptive_estimates(self, platform: str, phase: ExecutionPhase, actual_duration: float):
        """Actualiza las estimaciones adaptativas basadas en el rendimiento real"""
        if platform not in self.adaptive_time_estimates:
            return
            
        if phase not in self.adaptive_time_estimates[platform]:
            return
            
        # Obtener el número de unidades procesadas en esta fase
        progress = self.platforms[platform]
        units_processed = 0
        
        if phase == ExecutionPhase.DOWNLOADING:
            units_processed = progress.downloads_completed
        elif phase == ExecutionPhase.UPLOADING:
            units_processed = progress.upload_progress.posts_uploaded
        elif phase == ExecutionPhase.PROCESSING_STORIES:
            units_processed = progress.story_progress.processed_stories
        elif phase == ExecutionPhase.UPLOAD_DIRECTORY:
            units_processed = progress.directory_progress.processed_rows
            
        if units_processed > 0:
            # Calcular tiempo real por unidad
            actual_time_per_unit = actual_duration / units_processed
            
            # Usar promedio ponderado para actualizar la estimación (70% histórico, 30% actual)
            current_estimate = self.adaptive_time_estimates[platform][phase]
            updated_estimate = (current_estimate * 0.7) + (actual_time_per_unit * 0.3)
            self.adaptive_time_estimates[platform][phase] = updated_estimate
            
            # Guardar en historial de rendimiento
            history_key = f"{platform}_{phase.value}"
            if history_key not in self.performance_history:
                self.performance_history[history_key] = []
            
            self.performance_history[history_key].append({
                'timestamp': datetime.now().isoformat(),
                'units_processed': units_processed,
                'duration_minutes': actual_duration,
                'time_per_unit': actual_time_per_unit
            })
            
            # Mantener solo los últimos 10 registros
            if len(self.performance_history[history_key]) > 10:
                self.performance_history[history_key] = self.performance_history[history_key][-10:]

    def _get_recent_performance(self, platform: str) -> Dict[str, List]:
        """Obtiene el historial de rendimiento reciente de una plataforma"""
        platform_history = {}
        for key, history in self.performance_history.items():
            if key.startswith(f"{platform}_"):
                phase = key.replace(f"{platform}_", "")
                platform_history[phase] = history[-3:] if history else []  # Últimos 3 registros
        return platform_history
    
    def get_time_estimates_summary(self, platform: str = None) -> Dict:
        """Obtiene un resumen de las estimaciones de tiempo"""
        if platform:
            if platform in self.adaptive_time_estimates:
                estimates = self.adaptive_time_estimates[platform]
                base_estimates = self.base_time_estimates.get(platform, {})
                
                return {
                    'platform': platform,
                    'current_estimates_minutes_per_unit': {
                        phase.value if hasattr(phase, 'value') else str(phase): round(time_val, 2) 
                        for phase, time_val in estimates.items()
                    },
                    'base_estimates_minutes_per_unit': {
                        phase.value if hasattr(phase, 'value') else str(phase): round(time_val, 2) 
                        for phase, time_val in base_estimates.items()
                    },
                    'performance_tracking': self._get_recent_performance(platform)
                }
            return {'platform': platform, 'error': 'Platform not found'}
        else:
            # Resumen de todas las plataformas
            summary = {}
            for plat in ['Lefty', 'Traackr', 'Talkwalker']:
                summary[plat] = self.get_time_estimates_summary(plat)
            return summary

    def cleanup_old_platforms(self, max_age_hours: int = 24):
        """Limpia plataformas completadas/errores más antiguas que max_age_hours"""
        current_time = datetime.now()
        to_remove = []
        
        for platform, progress in self.platforms.items():
            if progress.last_update:
                age = (current_time - progress.last_update).total_seconds() / 3600
                if age > max_age_hours and progress.phase in [ExecutionPhase.COMPLETED, ExecutionPhase.ERROR]:
                    to_remove.append(platform)
        
        for platform in to_remove:
            del self.platforms[platform]
        
        if to_remove:
            self._save_to_file()

# Singleton global para fácil acceso
progress_reporter = ProgressReporter()