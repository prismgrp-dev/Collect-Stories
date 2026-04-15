import os
import time
from datetime import date
import numpy as np
import pandas as pd
from seatable_api import Base
from seatable_api.exception import AuthExpiredError
from config.config import SERVER_URL, TABLE_2025, TABLE_SOCIAL_ACCOUNT, LOCAL_FOLDER
from utils.helpers_seatable import identify_records, identify_records_2025, get_analysts_by_market, get_existing_urls_from_seatable, get_mh_collaborators, identify_records_to_delete
from utils.progress_reporter import progress_reporter, ExecutionPhase
from utils.clean_cell import clean_cell
from config.logger import logger_general

class Seatable:
    def __init__(self, api_token=None):
        self.server_url = SERVER_URL
        self.api_token = api_token
        self.base = None
        self.link_ids_cache = {}
        self.lookup_tables  = {}
        self.link_configs   = []

        # Initialize Traackr linking modules

    def base_auth(self, api_token=None):
        if api_token:
            self.api_token = api_token  # Actualiza el token si se proporciona uno nuevo

        self.base = Base(self.api_token, self.server_url)
        self.base.auth()
        return self.base
    
    def get_base(self):
        if not self.base:
            self.base_auth()
        return self.base

    def sql_query_one(self, query):
        max_retries = 3
        wait_seconds = 20

        for attempt in range(1, max_retries + 1):
            try:
                logger_general.info(f"⏳ Ejecutando query (intento {attempt}/{max_retries})")
                base = self.get_base()
                json_data = base.query(query)
                logger_general.info(f"✅ Datos obtenidos correctamente.")
                return json_data

            except AuthExpiredError:
                logger_general.info("🔑 Sesión expirada. Reautenticando...")
                time.sleep(2)  # Espera leve antes de reintentar autenticación
                continue

            except Exception as e:
                if "502" in str(e):
                    logger_general.info(f"⚠️ Error 502 (Bad Gateway). Reintentando en {wait_seconds} segundos...")
                    time.sleep(wait_seconds)
                else:
                    logger_general.info(f"❌ Error inesperado al ejecutar query: {e}")
                    break

        logger_general.info("❗ No se pudo obtener datos luego de varios intentos.")
        return []

    def sql_query(self, query, batch=10000):
        offset = 0
        all_data = []
        max_retries = 3
        wait_seconds = 30

        while True:
            paged_query = f"{query} LIMIT {batch} OFFSET {offset}"
            attempts = 0

            while attempts < max_retries:
                try:
                    base = self.get_base()
                    json_data = base.query(paged_query)
                    break  # éxito → salimos del bucle de reintentos

                except AuthExpiredError:
                    logger_general.info("🔑 Token expirado. Reautenticando...")
                    self.get_base()
                    time.sleep(2)

                except Exception as e:
                    attempts += 1
                    if "502" in str(e):
                        logger_general.info(f"⚠️ Error 502 (Bad Gateway). Esperando {wait_seconds} segundos antes de reintentar...")
                        time.sleep(wait_seconds)
                    elif attempts < max_retries:
                        logger_general.info(f"⚠️ Error: {e}. Reintentando en {wait_seconds} segundos...")
                        time.sleep(wait_seconds)
                    else:
                        logger_general.info(f"❌ Error persistente tras {max_retries} intentos: {e}")
                        raise

            else:
                # Si salimos del bucle sin romperlo (fallaron todos los intentos)
                logger_general.info("❗ No se pudo recuperar este bloque de datos. Finalizando consulta.")
                break

            if not json_data:
                logger_general.info("✅ No hay más datos por procesar.")
                break

            all_data.extend(json_data)
            offset += batch

        return all_data

    
    def perform_table_operation(self, table_name, row_data=None, type_batch="", row_id=""):
        logger_general.info(f"📗 Table to insert {table_name}")
        def run_operation(base):
            method_map = {
                "append_row": base.append_row,
                "update_row": base.update_row,
                "delete_row": base.batch_update_rows,
            }

            method = method_map.get(type_batch)
            if not method:
                raise ValueError(f"Tipo de batch '{type_batch}' no es válido.")
            row = ""

            if type_batch == "append_row":
                row = method(table_name, row_data, apply_default=True)
                logger_general.info("🟩 Registro subido")
            elif type_batch == "update_row":
                row = method(table_name, row_id, row_data)
                logger_general.info("🟩 Registro actualizado")
            elif type_batch == "delete_row":
                row = method(table_name, row_id)
                logger_general.info("🟩 Registro eliminado")
            return row

        max_retries = 3

        for retry in range(1, max_retries + 1):
            try:
                logger_general.info(f"Procesando {type_batch} (intento {retry}/{max_retries})")
                base = self.get_base()
                return run_operation(base)

            except (AuthExpiredError, ConnectionResetError) as e:
                logger_general.info(f"{type(e).__name__}: {e}. Reintentando en 20s...")
                time.sleep(20)

            except Exception as e:
                if "502" in str(e):
                    #logger_general.error(f"⚠️ Error 502 (Bad Gateway): intento {retry}/{max_retries}. Esperando 30s antes de reintentar...")
                    logger_general.info(f"⚠️ Error 502 (Bad Gateway): intento {retry}/{max_retries}. Esperando 30s antes de reintentar...")
                    time.sleep(30)
                else:
                    #logger_general.error(f"❌ Error al ejecutar '{type_batch}': {e}: intento {retry}/{max_retries}. Esperando 30s antes de reintentar...")
                    logger_general.info(f"❌ Error al ejecutar '{type_batch}': {e}: intento {retry}/{max_retries}. Esperando 30s antes de reintentar...")
                    time.sleep(30)

        return "✅ Finalizado"
    
    def get_column_link_id(self, table_name, column_name):
        base = self.get_base()

        link_id = base.get_column_link_id(table_name, column_name)
        time.sleep(1)

        return link_id
    
    def perform_link_operation(self, link_id, row_id, other_row_id, table_name, other_table_name):
        logger_general.info(f"🔗 link_id {link_id}")
        logger_general.info(f"🔗 row_id {row_id}")
        logger_general.info(f"🔗 other_row_id {other_row_id}")
        logger_general.info(f"🔗 table_name {table_name}")
        logger_general.info(f"🔗 other_table_name {other_table_name}")
        def run_operation(base):
            link = base.add_link(
                link_id,
                table_name,
                other_table_name,
                row_id,
                other_row_id
            )
            logger_general.info(f"🔗 Link creado: {row_id} → {other_row_id}")
            logger_general.info(f"🔎 Respuesta de add_link: {link} (tipo: {type(link)})")
            time.sleep(0.5)
            return link

        max_retries = 3
        for intento in range(max_retries):
            try:
                logger_general.info(f"Procesando creación de link (intento {intento + 1})")
                base = self.get_base()
                link = run_operation(base)
                return link
            except (AuthExpiredError, ConnectionResetError) as e:
                logger_general.info(f"{type(e).__name__}: {e}. Reintentando... en 30s")
                time.sleep(30)
            except Exception as e:
                #logger_general.error(f"❌ Error al crear link: {e}. Reintentando... en 30s")
                logger_general.info(f"❌ Error al crear link: {e}. Reintentando... en 30s")
                time.sleep(30)

        return None

    def perform_unlink_operation(self, link_id, row_id, other_row_id, table_name, other_table_name):
        logger_general.info(f"🔗 Desvinculando link_id {link_id}")
        logger_general.info(f"🔗 row_id {row_id}")
        logger_general.info(f"🔗 other_row_id {other_row_id}")
        logger_general.info(f"🔗 table_name {table_name}")
        logger_general.info(f"🔗 other_table_name {other_table_name}")
        def run_operation(base):
            link = base.remove_link(
                link_id,
                table_name,
                other_table_name,
                row_id,
                other_row_id
            )
            logger_general.info(f"🔗 Link removido: {row_id} -X- {other_row_id}")
            time.sleep(0.5)
            return link

        max_retries = 3
        for intento in range(max_retries):
            try:
                base = self.get_base()
                link = run_operation(base)
                return link
            except (AuthExpiredError, ConnectionResetError) as e:
                logger_general.info(f"{type(e).__name__}: {e}. Reintentando... en 30s")
                time.sleep(30)
            except Exception as e:
                logger_general.info(f"❌ Error al remover link: {e}. Reintentando... en 30s")
                time.sleep(30)

        return None
    
    def batch_query(self, table_name, rows_data, type_batch="", batch=50):
        base = self.get_base()
        offset = 0
        method_map = {
            "batch_append_rows": base.batch_append_rows,
            "big_data_insert_rows": base.big_data_insert_rows,
            "batch_update_rows": base.batch_update_rows,
            "batch_delete_rows": base.batch_delete_rows,
        }

        method = method_map.get(type_batch)
        if not method:
            raise ValueError(f"Tipo de batch '{type_batch}' no es válido.")

        while offset < len(rows_data):
            batch_data = rows_data[offset:offset + batch]
            retry_count = 0
            success = False

            while retry_count < 3 and not success:
                try:
                    logger_general.info(f"🔄 Procesando lote desde {offset} hasta {offset + len(batch_data)} ({len(batch_data)} registros)")
                    method(table_name, batch_data)
                    logger_general.info(f"🟩 Registros subidos correctamente: {len(batch_data)} filas")
                    time.sleep(5)
                    success = True  # Marcamos como exitoso para salir del bucle interno
                    offset += batch

                except (AuthExpiredError, ConnectionResetError) as err:
                    retry_count += 1
                    logger_general.info(f"⚠️ Error de conexión ({type(err).__name__}): intento {retry_count}/3. Reintentando en 30s...")
                    time.sleep(30)
                    base = self.get_base()
                    method = method_map.get(type_batch)

                except Exception as e:
                    if "502" in str(e) or "500" in str(e):
                        retry_count += 1
                        logger_general.info(f"⚠️ Error 502/500 (Bad Gateway/Internal Server Error): intento {retry_count}/3. Esperando 30s antes de reintentar...")
                        time.sleep(30)
                        # No cambia offset, se reintenta
                    else:
                        logger_general.info(f"❌ Error no controlado: {e}")
                        return "❌ Fallo inesperado"

            if not success:
                logger_general.info(f"⛔ Falló el lote desde {offset} hasta {offset + len(batch_data)} tras 3 intentos.")
                break  # Salimos del bucle principal si no se logró insertar el batch

        return None


    def insert_from_excel_or_csv_to_seatable(self, file, table_name, sheet_name):
        df = self.excel_or_csv_to_dataframe(file, sheet_name)

        """ collaborators = [
        "333079364233403fb0b35dd278d24486@auth.local",
        "6fd33907093e4741a72714710434adf1@auth.local",
        "ca7503a5722141e4a8efa9b357265b3d@auth.local"
        ]

        df["Collaborators"] = [collaborators] * len(df) """


        payload = self.create_payload_insert(df)

        result = self.batch_query(table_name, rows_data=payload, type_batch="batch_append_rows")
        return result
    
    def build_reference_data(self, link_configs):
        """
        Inicializa completamente el cache de referencias.
        Llama internamente a add_reference_data, reseteando antes.
        """
        self.link_ids_cache = {}
        self.lookup_tables  = {}
        self.link_configs   = []
        self.add_reference_data(link_configs)

    def add_reference_data(self, link_configs, force_refresh=False, handle_comma_separated_ids=False):
        """
        Añade SOLO las nuevas configuraciones de enlace que aún no existan.

        Args:
            link_configs: Lista de configuraciones de enlace
            force_refresh: Si es True, refresca la referencia aunque ya exista
            handle_comma_separated_ids: Si es True, maneja IDs separados por comas en la referencia
        """
        for cfg in link_configs:
            # si ya lo procesamos, saltamos (a menos que force_refresh sea True)
            if not force_refresh and any(existing["table_name"] == cfg["table_name"] for existing in self.link_configs):
                continue

            logger_general.info(f"☑️ Haciendo referencia a la tabla: {cfg['table_name']}")

            # 1) link_id
            link_id = self.get_column_link_id(
                cfg["other_table_name"],
                cfg["link_id_name"]
            )
            self.link_ids_cache[cfg["table_name"]] = link_id

            # 2) lookup table
            query = f"SELECT `{cfg['column_name']}` AS name, _id FROM `{cfg['table_name']}`"
            time.sleep(2)  # si lo necesitas
            self.lookup_tables[cfg["table_name"]] = self.sql_query(query)

            # 3) marcamos que ya lo procesamos (solo si no existe ya)
            if not any(existing["table_name"] == cfg["table_name"] for existing in self.link_configs):
                # Store if this config handles comma-separated IDs
                cfg_copy = cfg.copy()
                cfg_copy["handle_comma_separated_ids"] = handle_comma_separated_ids
                self.link_configs.append(cfg_copy)
        

    def upload_new_records_to_seatable_2025(self, new_data, existing_data_2025, table_name, columns_to_check_status, role="Agencias", key_columns_new=None, key_columns_existing=None, column_mapping=None, platform=""):
        """
        Identifica registros nuevos y los sube a Seatable, asegurándose de que las URLs no estén duplicadas.
        
        Parámetros:
        - new_data: DataFrame con los nuevos datos
        - existing_data: DataFrame con los datos existentes
        - table_name: Nombre de la tabla en Seatable
        - key_columns_new: Columnas clave en new_data para identificar registros únicos
        - key_columns_existing: Columnas clave en existing_data para identificar registros únicos
        - column_mapping: Diccionario con el mapeo de nombres de columnas {nombre_en_new_data: nombre_en_seatable_2025}
        """
        # Paso 1: Identificar los registros nuevos
        new_records = identify_records_2025(new_data, existing_data_2025, key_columns_new, key_columns_existing)
        
        # Extraer año del table_name (asumiendo que table_name es el año como string, ej: "2025", "2026")
        try:
            print("🟩 Obteniendo año...")
            print(table_name)
            year = int(table_name)
            years = [year]
        except ValueError:
            # Si table_name no es un año válido, usar lista vacía
            years = []
        
        # Paso 2: Obtener todas las URLs existentes en la tabla de Seatable 
        existing_urls = get_existing_urls_from_seatable(years)
        
        # Paso 3: Filtrar los nuevos registros para eliminar los que ya tienen URLs existentes
        new_records_filtered = new_records[~new_records['URL'].isin(existing_urls)]  # Excluir URLs duplicadas

        total_rows = len(new_records_filtered)

        progress_reporter.update_upload_progress(platform, 0, total_rows, f"Tabla 2025 - {total_rows} filas a procesar")

        date_columns = ["Date", "Date Excel", "Date Other"]

        for col in date_columns:
            if col in new_records_filtered.columns:
                new_records_filtered[col] = new_records_filtered[col].map(
                    lambda d: d.isoformat() if isinstance(d, date) else str(d)
                )

        new_records_filtered = new_records_filtered.astype(object)

        for col in new_records_filtered.columns:
            try:
                new_records_filtered[col] = new_records_filtered[col].where(pd.notnull(new_records_filtered[col]), None)
            except (ValueError, TypeError):
                # Método alternativo para columnas problemáticas
                new_records_filtered[col] = new_records_filtered[col].apply(
                    lambda x: None if pd.isna(x) else x
                )
        
        if new_records_filtered.empty:
            logger_general.info("No hay nuevos registros para subir a Seatable.")
            return 0, []
        
        analysts_by_market = get_analysts_by_market(years=years)
        responsables_by_market = get_analysts_by_market(role, years=years)
        mh_collaborators = get_mh_collaborators(years=years)
        # Aplicar el mapeo de columnas si se proporciona
        if column_mapping:
            records_to_upload = []
            for _, row in new_records_filtered.iterrows():
                record = {}
                row = clean_cell(row)
                for col_original, value in row.items():
                    # Si la columna está en el mapeo, usar el nombre correspondiente en Seatable 2025
                    col_seatable = column_mapping.get(col_original, col_original)
                    record[col_seatable] = value

                    country = record.get("_Country_")

                    if country and country in responsables_by_market:
                        record["Responsable"] = responsables_by_market[country]
                    else:
                        record["Responsable"] = []

                    if columns_to_check_status:
                        has_empty = any(
                            record.get(col) is None or record.get(col) == "" or record.get(col) == []
                            for col in columns_to_check_status
                        )
                        record["Status"] = "Nuevo" if has_empty else "Listo para analizar"
                        

                        if record.get("Status") == "Listo para analizar":
                            if country and country in analysts_by_market:
                                record["Analista"] = analysts_by_market[country]
                            else:
                                record["Analista"] = []
                    else:
                        record["Analista"] = []

                    record["Collaborators"] = mh_collaborators

                records_to_upload.append(record)
        else:
            # Si no hay mapeo, usar los nombres originales
            records_to_upload = new_records_filtered.to_dict(orient='records')

        total_records = len(records_to_upload)
        logger_general.info(f"🟩 TOTAL RECORDS: {total_records} ......")
        uploaded_count = 0

        link_ids_cache = self.link_ids_cache
        lookup_tables  = self.lookup_tables
        
        # Diccionario para mapear unique_id -> _id insertado
        id_mapping = {}

        table_year = table_name

        # 🔁 3. Insertar registros y realizar enlaces
        for record in records_to_upload:
            uploaded_count += 1
            progress_reporter.update_upload_progress(platform, uploaded_count, total_rows, f"Tabla {table_year} - Procesando fila {uploaded_count}/{total_rows}")

            created = self.perform_table_operation(table_year, record, type_batch="append_row")
            
            # Validar que la operación fue exitosa y retornó un diccionario válido
            if not created or not isinstance(created, dict) or "_id" not in created:
                logger_general.error(f"❌ Error al crear registro en {table_year}: {created}")
                logger_general.error(f"📝 Registro problemático: {record}")
                continue  # Saltar este registro y continuar con el siguiente
            
            other_row_id = created["_id"]
            
            # Guardar mapeo: usar la primera columna de key_columns_new como clave
            if key_columns_existing and len(key_columns_existing) > 0:
                unique_id_value = record.get(key_columns_existing[0])
                if unique_id_value:
                    id_mapping[unique_id_value] = created["0000"]
            
            for cfg in self.link_configs:
                table_name = cfg["table_name"]
                other_table_name = cfg["other_table_name"]
                match_value = record.get(cfg["other_column_name"])

                # Buscar el row_id de la tabla de referencia según valor
                row_id = next(
                    (item["_id"] for item in lookup_tables[table_name] if item["name"] == match_value),
                    None
                )

                if row_id:
                    link_id = link_ids_cache[table_name]
                    self.perform_link_operation(link_id, row_id, other_row_id, table_name, other_table_name)
                else:
                    logger_general.info(f"⚠️ No se encontró '{match_value}' en {table_name}")


 
        progress_reporter.update_upload_progress(platform, total_rows, total_rows, f"Tabla {table_year} - Subida completada: {total_rows} filas")
        logger_general.info(f"🟩 Proceso completado. Total de registros nuevos subidos: {total_records}")
        message = f"Filas subidas: {uploaded_count} / {total_records}"
        data_to_return = {
            "records_to_upload": records_to_upload,
            "upload_2025": message,
            "id_mapping": id_mapping,  # Agregar el mapeo de IDs
        }


        return data_to_return
    
    def upload_single_record_to_seatable_2025(self, record_data, table_name, columns_to_check_status=None, role=None, column_mapping=None, enable_link=False):
        link_ids_cache = self.link_ids_cache
        lookup_tables  = self.lookup_tables

        table_year = table_name

        # 🔁 3. Insertar registros y realizar enlaces
        for record in records_to_upload:
            uploaded_count += 1
            progress_reporter.update_upload_progress(platform, uploaded_count, total_rows, f"Tabla {table_year} - Procesando fila {uploaded_count}/{total_rows}")

            created = self.perform_table_operation(table_year, record, type_batch="append_row")
            
            # Validar que la operación fue exitosa y retornó un diccionario válido
            if not created or not isinstance(created, dict) or "_id" not in created:
                logger_general.error(f"❌ Error al crear registro en {table_year}: {created}")
                logger_general.error(f"📝 Registro problemático: {record}")
                continue  # Saltar este registro y continuar con el siguiente
            
            other_row_id = created["_id"]
            
            for cfg in self.link_configs:
                table_name = cfg["table_name"]
                other_table_name = cfg["other_table_name"]
                match_value = record.get(cfg["other_column_name"])

                # Buscar el row_id de la tabla de referencia según valor
                row_id = next(
                    (item["_id"] for item in lookup_tables[table_name] if item["name"] == match_value),
                    None
                )

                if row_id:
                    link_id = link_ids_cache[table_name]
                    self.perform_link_operation(link_id, row_id, other_row_id, table_name, other_table_name)
                else:
                    logger_general.info(f"⚠️ No se encontró '{match_value}' en {table_name}")


 
        progress_reporter.update_upload_progress(platform, total_rows, total_rows, f"Tabla {table_year} - Subida completada: {total_rows} filas")
        logger_general.info(f"🟩 Proceso completado. Total de registros nuevos subidos: {total_records}")
        message = f"Filas subidas: {uploaded_count} / {total_records}"
        data_to_return = {
            "records_to_upload": records_to_upload,
            "upload_2025": message,
            "row": created
        }


        return data_to_return
    
    def upload_single_record_to_seatable_2025(self, record_data, table_name, columns_to_check_status=None, role=None, column_mapping=None, enable_link=False):
        """
        Sube un solo registro a Seatable con el mismo procesamiento que upload_new_records_to_seatable_2025
        pero sin identificar registros nuevos ni verificar URLs existentes.
        
        Parámetros:
        - record_data: DataFrame con una sola fila o dict con los datos del registro
        - table_name: Nombre de la tabla en Seatable
        - columns_to_check_status: Columnas para verificar si el registro está completo
        - role: Rol para asignar responsables
        - column_mapping: Diccionario con el mapeo de nombres de columnas
        """
        # Convertir a dict si es DataFrame
        if isinstance(record_data, pd.DataFrame):
            if len(record_data) != 1:
                raise ValueError("record_data debe contener exactamente una fila")
            record = record_data.iloc[0].to_dict()
        else:
            record = record_data.copy()
        
        # Procesar fecha si existe
        date_keys = ["Date", "Date Excel", "Date Other"]

        for key in date_keys:
            if key in record and record[key] is not None:
                if hasattr(record[key], "isoformat"):
                    record[key] = record[key].isoformat()
                else:
                    record[key] = str(record[key])
        
        record = clean_cell(record)
        
        # Extraer año del table_name
        try:
            year = int(table_name)
            years = [year]
        except ValueError:
            years = []
        
        # Obtener datos de referencia
        analysts_by_market = get_analysts_by_market(years=years)
        responsables_by_market = get_analysts_by_market(role, years=years) if role else {}
        mh_collaborators = get_mh_collaborators(years=years)
        
        # Aplicar el mapeo de columnas si se proporciona
        if column_mapping:
            mapped_record = {}
            for col_original, value in record.items():
                # Si la columna está en el mapeo, usar el nombre correspondiente en Seatable 2025
                col_seatable = column_mapping.get(col_original, col_original)
                mapped_record[col_seatable] = value
            record = mapped_record
        
        # Asignar responsable por país
        country = record.get("_Country_")
        if country and country in responsables_by_market:
            record["Responsable"] = responsables_by_market[country]
        else:
            record["Responsable"] = []
        
        record["Status"] = "Copiada"
        
        # Verificar status y asignar analista
        if columns_to_check_status:
            has_empty = any(
                record.get(col) is None or record.get(col) == "" or record.get(col) == []
                for col in columns_to_check_status
            )
            record["Status"] = "Nuevo" if has_empty else "Listo para analizar"
            
            if record.get("Status") == "Listo para analizar":
                if country and country in analysts_by_market:
                    record["Analista"] = analysts_by_market[country]
                else:
                    record["Analista"] = []
        else:
            record["Analista"] = []
        
        # Asignar colaboradores
        record["Collaborators"] = mh_collaborators
        
        # Insertar registro
        created = self.perform_table_operation(table_name, record, type_batch="append_row")
        
        if not created or not isinstance(created, dict) or "_id" not in created:
            raise Exception(f"Error al crear registro en Seatable: {created}")
        
        other_row_id = created["_id"]

        if enable_link == True:
            # Realizar enlaces si están configurados
            link_ids_cache = self.link_ids_cache
            lookup_tables = self.lookup_tables
            
            for cfg in self.link_configs:
                table_name_link = cfg["table_name"]
                other_table_name = cfg["other_table_name"]
                match_value = record.get(cfg["other_column_name"])
                
                # Buscar el row_id de la tabla de referencia según valor
                row_id = next(
                    (item["_id"] for item in lookup_tables[table_name_link] if item["name"] == match_value),
                    None
                )
                
                
                if row_id:
                    link_id = link_ids_cache[table_name_link]
                    self.perform_link_operation(link_id, row_id, other_row_id, table_name_link, other_table_name)
        
        return created
    
    def _try_enhanced_linking(self, record, cfg, lookup_tables, alternative_ids_column, successful_group_mappings=None):
        """
        Try enhanced linking with multiple TraackrIDs, ensuring all group members use the same successful ID

        Args:
            record: Record dictionary
            cfg: Link configuration
            lookup_tables: Lookup tables for references
            alternative_ids_column: Column name containing alternative IDs
            successful_group_mappings: Dictionary to track successful TraackrIDs by group

        Returns:
            tuple (row_id, successful_traackr_id) if successful, (None, None) otherwise
        """
        table_name = cfg["table_name"]
        original_traackr_id = record.get(cfg["other_column_name"], "")
        alternative_ids_str = record.get(alternative_ids_column, "")

        # Build list of IDs to try: original first, then alternatives
        ids_to_try = [original_traackr_id] if original_traackr_id else []

        if alternative_ids_str:
            alternative_ids = [id.strip() for id in alternative_ids_str.split(',') if id.strip()]
            ids_to_try.extend(alternative_ids)

        if not ids_to_try:
            logger_general.info(f"⚠️ No hay TraackrID disponible para enhanced linking")
            return None, None

        # Create group identifier for this record (all IDs that belong to the same group)
        group_ids = set([original_traackr_id] + ([id.strip() for id in alternative_ids_str.split(',') if id.strip()] if alternative_ids_str else []))
        group_key = tuple(sorted([id for id in group_ids if id]))  # Sort for consistent key

        # Check if we already found a successful TraackrID for this group
        if successful_group_mappings and group_key in successful_group_mappings:
            successful_id = successful_group_mappings[group_key]
            lookup_table = lookup_tables.get(table_name, [])

            # Search for successful_id in lookup_table, handling both string and array formats
            row_id = None
            for item in lookup_table:
                name_value = item.get("name")

                # If name is a string, do direct comparison
                if isinstance(name_value, str) and name_value == successful_id:
                    row_id = item["_id"]
                    break
                # If name is a list/array, search within the array
                elif isinstance(name_value, list):
                    # Check if any element in the array matches successful_id
                    for element in name_value:
                        # Handle different possible array element formats
                        if isinstance(element, str) and element == successful_id:
                            row_id = item["_id"]
                            break
                        elif isinstance(element, dict) and element.get("display_value") == successful_id:
                            row_id = item["_id"]
                            break
                    if row_id:
                        break
            if row_id:
                logger_general.info(f"✅ Usando TraackrID previamente exitoso para el grupo: {successful_id}")
                return row_id, successful_id
            else:
                logger_general.info(f"⚠️ TraackrID previamente exitoso {successful_id} ya no está disponible")
                # Remove from successful mappings and try again
                del successful_group_mappings[group_key]

        logger_general.info(f"🔍 Enhanced linking: probando {len(ids_to_try)} TraackrIDs para tabla {table_name}")

        # Try each TraackrID until one works
        lookup_table = lookup_tables.get(table_name, [])

        for traackr_id in ids_to_try:
            if not traackr_id:
                continue

            # Look for this TraackrID in the lookup table
            # Handle both string and array formats for the "name" field
            row_id = None
            for item in lookup_table:
                name_value = item.get("name")

                # If name is a string, do direct comparison
                if isinstance(name_value, str) and name_value == traackr_id:
                    row_id = item["_id"]
                    break
                # If name is a list/array, search within the array
                elif isinstance(name_value, list):
                    # Check if any element in the array matches traackr_id
                    for element in name_value:
                        # Handle different possible array element formats
                        if isinstance(element, str) and element == traackr_id:
                            row_id = item["_id"]
                            break
                        elif isinstance(element, dict) and element.get("display_value") == traackr_id:
                            row_id = item["_id"]
                            break
                    if row_id:
                        break

            if row_id:
                logger_general.info(f"✅ Enhanced linking exitoso con TraackrID: {traackr_id}")
                # Store successful TraackrID for this group
                if successful_group_mappings is not None:
                    successful_group_mappings[group_key] = traackr_id
                    logger_general.info(f"📝 Almacenado TraackrID exitoso {traackr_id} para el grupo {list(group_key)}")
                return row_id, traackr_id
            else:
                logger_general.info(f"❌ TraackrID {traackr_id} no encontrado en tabla {table_name}")

        logger_general.info(f"⚠️ Enhanced linking falló: ningún TraackrID funcionó. Probados: {ids_to_try}")
        return None, None

    def _try_enhanced_linking_talkwalker(self, record, cfg, lookup_tables):
        """
        Try enhanced linking for TalkwalkerID - simplified version without groups

        Args:
            record: Record dictionary
            cfg: Link configuration
            lookup_tables: Lookup tables for references

        Returns:
            tuple (row_id, successful_talkwalker_id) if successful, (None, None) otherwise
        """
        table_name = cfg["table_name"]
        original_talkwalker_id = record.get(cfg["other_column_name"], "")

        # Build list of IDs to try - for Talkwalker we look for comma-separated values in the lookup table
        ids_to_try = [original_talkwalker_id] if original_talkwalker_id else []

        if not ids_to_try:
            logger_general.info(f"⚠️ No hay TalkwalkerID disponible para enhanced linking")
            return None, None

        logger_general.info(f"🔍 Enhanced linking Talkwalker: probando {len(ids_to_try)} TalkwalkerIDs para tabla {table_name}")

        # Try each TalkwalkerID until one works
        lookup_table = lookup_tables.get(table_name, [])

        for talkwalker_id in ids_to_try:
            if not talkwalker_id:
                continue

            # Look for this TalkwalkerID in the lookup table
            # Handle both string and array formats for the "name" field (same logic as TraackrID)
            row_id = None
            for item in lookup_table:
                name_value = item.get("name")

                # If name is a string, check if it contains the talkwalker_id (could be comma-separated)
                if isinstance(name_value, str):
                    if name_value == talkwalker_id:
                        row_id = item["_id"]
                        break
                    # Check if it's comma-separated and contains our ID
                    elif "," in name_value:
                        ids_in_field = [id.strip() for id in name_value.split(",") if id.strip()]
                        if talkwalker_id in ids_in_field:
                            row_id = item["_id"]
                            break
                # If name is a list/array, search within the array
                elif isinstance(name_value, list):
                    # Check if any element in the array matches talkwalker_id
                    for element in name_value:
                        # Handle different possible array element formats
                        if isinstance(element, str) and element == talkwalker_id:
                            row_id = item["_id"]
                            break
                        elif isinstance(element, dict) and element.get("display_value") == talkwalker_id:
                            row_id = item["_id"]
                            break
                    if row_id:
                        break

            if row_id:
                logger_general.info(f"✅ Enhanced linking exitoso con TalkwalkerID: {talkwalker_id}")
                return row_id, talkwalker_id
            else:
                logger_general.info(f"❌ TalkwalkerID {talkwalker_id} no encontrado en tabla {table_name}")

        logger_general.info(f"⚠️ Enhanced linking falló: ningún TalkwalkerID funcionó. Probados: {ids_to_try}")
        return None, None

    def set_network_priority_order(self, new_priority):
        """
        Configura el orden de prioridad para las redes sociales.

        Args:
            new_priority (List[str]): Nueva lista de prioridad ordenada
                                     (ej: ["instagram", "facebook", "tiktok", "youtube"])
        """
        self.network_priority_manager.set_priority_order(new_priority)

    def get_network_priority_order(self):
        """
        Obtiene el orden actual de prioridad de las redes sociales.

        Returns:
            List[str]: Orden actual de prioridad
        """
        return self.network_priority_manager.get_priority_order()
    
    def upload_new_records_to_seatable(self, new_data, existing_data, table_name, key_columns=None, enable_link: bool = False, table_to_insert=TABLE_SOCIAL_ACCOUNT, platform=None, custom_fn=None, alternative_ids_column=None, df_source=None):
        """
        Identifica registros nuevos y los sube a Seatable.
        """
        if platform:
            progress_reporter.add_log(platform, f"INICIANDO SUBIDA - Tabla: {table_name} - {len(new_data)} filas nuevas detectadas")
        # Identificar los registros nuevos
        new_records = identify_records(new_data, existing_data, key_columns)
        
        # Apply custom function only to new records if provided
        if callable(custom_fn):
            logger_general.info(f"🔄 Función personalizada detectada: {custom_fn}")
            if not new_records.empty:
                logger_general.info(f"🔄 Aplicando función personalizada a {len(new_records)} registros nuevos...")
                new_records = custom_fn(new_records)
            else:
                logger_general.info("⚠️ No hay registros nuevos para aplicar la función personalizada")
        else:
            logger_general.info("⚠️ No se proporcionó función personalizada o no es callable")
        
        date_columns = ["Date", "Date Excel", "Date Other"]

        for col in date_columns:
            if col in new_records.columns:
                new_records[col] = new_records[col].map(
                    lambda d: d.isoformat() if isinstance(d, date) else str(d)
                )
    
        new_records = new_records.astype(object).where(pd.notnull(new_records), None)


        if new_records.empty:
            logger_general.info("No hay nuevos registros para subir a Seatable.")
            return 0, []
        
        if table_name not in ["Influencer Info", "Influencers Perfs", "Channel"]:
            # Agrupar los registros por URL
            try:
                print("🟩 Obteniendo año...")
                print(table_name)
                if "Lefty Perfs" == table_name or "Traackr Perfs" == table_name or "Talkwalker Perfs" == table_name:
                    print("🟩 Convertido a 2025")
                    years = [2025]
                else:
                    print("🟩 Convertido a año")
                    year = int(table_name)
                    years = [year]
            except ValueError:
                years = []
            existing_urls = get_existing_urls_from_seatable(years)

            # Establecer Status inicial como 'Nuevo'
            new_records['Status'] = 'Nuevo'
            
            # Marcar como 'Copiada' solo los que tengan valor en 'Brand PR ID'
            for i, row in new_records.iterrows():
                id_2025 = row.get('Brand PR ID')
                if pd.notna(id_2025) and id_2025 != "" and id_2025 != []:
                    new_records.loc[i, 'Status'] = 'Copiada'
            
            # Revisar URLs duplicadas (esto sobrescribe el Status si es necesario)
            for i, row in new_records.iterrows():
                url = row.get('URL')
                if pd.notna(url) and url != "" and url in existing_urls:
                    new_records.loc[i, 'Status'] = 'URL Duplicada'
        
        # Convertir los registros nuevos a una lista de diccionarios
        records_to_upload = new_records.to_dict(orient='records')
        total_records = len(records_to_upload)
        logger_general.info(f"🟩 TOTAL RECORDS: {total_records}")
    
        # Subir los registros en lotes
        logger_general.info("⏳ Haciendo subida de filas...")
        link_ids_cache = self.link_ids_cache
        lookup_tables  = self.lookup_tables

        directory = False
        if table_name == "Influencer Info" and platform == "Lefty" or table_name == "Channel" and platform == "Talkwalker" or table_name == "Channel" and platform == "Traackr":
            directory = True

        count_rows = 0
        total_rows = len(records_to_upload)

        # Dictionary to track successful TraackrIDs by group for enhanced linking
        successful_group_mappings = {}

        # Cache to avoid creating duplicate Source records for the same TraackrID
        created_source_cache = {}

        # Cache to store successful Source linking for groups
        group_source_cache = {}

        if enable_link:
            if directory:
                    progress_reporter.update_directory_progress(platform, count_rows, total_rows, "")
            for record in records_to_upload:
                count_rows += 1
                created = self.perform_table_operation(table_to_insert, record, type_batch="append_row")
                other_row_id = created["_id"]
                if directory:
                    progress_reporter.update_directory_progress(platform, count_rows, total_rows, "")

                for cfg in self.link_configs:
                    table_name = cfg["table_name"]
                    other_table_name = cfg["other_table_name"]
                    match_value = record.get(cfg["other_column_name"])

                    # Enhanced linking: try multiple TraackrIDs if alternative_ids_column is provided
                    if alternative_ids_column and alternative_ids_column in record and cfg["other_column_name"] == "TraackrID":
                        # Use enhanced linking with auto-creation capability
                        row_id, successful_traackr_id = self.auto_source_creator.try_enhanced_linking_with_auto_creation(
                            record, cfg, lookup_tables, alternative_ids_column, successful_group_mappings,
                            self._try_enhanced_linking, self.perform_table_operation, df_source, None, platform or "traackr", self, group_source_cache
                        )
                        if row_id and successful_traackr_id:
                            logger_general.info(f"✅ Enhanced linking exitoso usando TraackrID: {successful_traackr_id}")
                            # Update lookup table after successful auto-creation
                            if successful_traackr_id not in [item.get("name") for item in lookup_tables.get("Source", [])]:
                                self.auto_source_creator.update_source_lookup_table(
                                    successful_traackr_id, row_id, self.lookup_tables
                                )
                    # Enhanced linking for TalkwalkerID: with URL extraction and Channel search
                    elif cfg["other_column_name"] == "TalkwalkerID" and cfg.get("handle_comma_separated_ids", False):
                        logger_general.info("🗣️ Enhanced linking para Talkwalker: probando múltiples TalkwalkerIDs")

                        # Try enhanced linking with auto-creation (includes URL extraction and Channel search)
                        row_id, successful_talkwalker_id = self.auto_source_creator.try_enhanced_linking_with_auto_creation(
                            record, cfg, lookup_tables, None, None,
                            self._try_enhanced_linking_talkwalker, self.perform_table_operation, df_source, created_source_cache, "talkwalker", self, None
                        )

                        if row_id and successful_talkwalker_id:
                            logger_general.info(f"✅ Enhanced linking exitoso con TalkwalkerID: {successful_talkwalker_id}")
                            # Update lookup table if needed
                            if successful_talkwalker_id not in [item.get("name") for item in lookup_tables.get("Source", [])]:
                                self.auto_source_creator.update_source_lookup_table(
                                    successful_talkwalker_id, row_id, self.lookup_tables
                                )
                    else:
                        # Búsqueda estándar
                        row_id = None

                        # Check if this config handles comma-separated IDs
                        if cfg.get("handle_comma_separated_ids", False) and match_value:
                            # Handle comma-separated IDs for Traackr Lookup
                            if isinstance(match_value, str) and "," in match_value:
                                # Split by comma and try each ID separately
                                ids_to_try = [id.strip() for id in match_value.split(",") if id.strip()]
                                logger_general.info(f"🔍 Probando IDs separados por comas: {ids_to_try}")
                                logger_general.info(lookup_tables)

                                for single_id in ids_to_try:
                                    row_id = next(
                                        (item["_id"] for item in lookup_tables[table_name] if item["name"] == single_id),
                                        None
                                    )
                                    if row_id:
                                        logger_general.info(f"✅ Match encontrado con ID: {single_id}")
                                        break
                            else:
                                # Single ID, normal search
                                row_id = next(
                                    (item["_id"] for item in lookup_tables[table_name] if item["name"] == match_value),
                                    None
                                )
                        else:
                            # Robust search: handle direct strings, missing spaces, arrays (from formulas), and comma-separated strings
                            row_id = None
                            match_str = str(match_value).strip() if pd.notna(match_value) else ""
                            if match_str:
                                for item in lookup_tables[table_name]:
                                    item_name = item.get("name")
                                    if not item_name:
                                        continue
                                    
                                    found = False
                                    if isinstance(item_name, list):
                                        # If formula returns list of strings
                                        for n in item_name:
                                            if not n: continue
                                            n_str = str(n).strip()
                                            if n_str == match_str or match_str in [part.strip() for part in n_str.split(",")]:
                                                found = True
                                                break
                                    else:
                                        # If it's a plain string or number
                                        item_str = str(item_name).strip()
                                        if item_str == match_str or match_str in [part.strip() for part in item_str.split(",")]:
                                            found = True
                                    
                                    if found:
                                        row_id = item["_id"]
                                        break

                    if row_id:
                        link_id = link_ids_cache[table_name]
                        self.perform_link_operation(link_id, row_id, other_row_id, table_name, other_table_name)
                        if alternative_ids_column and cfg["other_column_name"] == "TraackrID":
                            logger_general.info(f"✅ Enhanced linking exitoso para registro")
                    else:
                        logger_general.info(f"⚠️ No se encontró '{match_value}' en {table_name}")
                

            if platform:
                progress_reporter.add_log(platform, f"SUBIDA COMPLETADA - Tabla: {table_name} - AÑADIDAS: {len(records_to_upload)} filas con enlaces")
        else:
            logger_general.info(f"🟩 Proceso completado. Total de registros nuevos subidos: {total_records}")
            self.batch_query(table_name, rows_data=records_to_upload, type_batch="batch_append_rows")
            if platform:
                progress_reporter.add_log(platform, f"SUBIDA COMPLETADA - Tabla: {table_name} - AÑADIDAS: {len(records_to_upload)} filas (batch)")

        
        logger_general.info(f"🟩 Proceso completado. Total de registros nuevos subidos: {total_records}")
        return records_to_upload

    def excel_or_csv_to_dataframe(self, file_path, sheet_name=None):
        """
        Lee un archivo CSV o Excel y lo retorna como dataframe, limpia las columnas nan y inf por None.
        """
        # Detectar la extensión del archivo
        _, ext = os.path.splitext(file_path.lower())

        # Leer el archivo según su tipo
        if ext == '.csv':
            df = pd.read_csv(file_path, encoding='UTF-8')
        elif ext in ['.xlsx', '.xls']:
            # Leer el archivo Excel, si se pasa un sheet_name, se lee esa hoja
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            raise ValueError("Formato de archivo no soportado. Usa CSV o Excel.")

        # Reemplazar NaN o Inf por None
        df = df.replace([np.nan, np.inf], None)
        df = df.map(lambda d: d.isoformat() if isinstance(d, date) else str(d) if pd.notnull(d) else d)

        return df

    def create_payload_insert(self, dataframe):
        """
        Lee un dataframe y genera una lista de diccionarios para inserciones:
        [{<columna>: <valor>, ...}, ...]
        """
        return dataframe.to_dict(orient='records')

    def create_payload_update(self, dataframe, unique_key):
        """
        Lee un dataframe y genera una lista de diccionarios con la estructura:
        {
            "row_id": <valor_de_unique_key>,
            "row": {<columna>: <>, ...}  # sin la columna unique_key
        }
        """
        payload_list = []
        for _, row in dataframe.iterrows():
            row_id = row[unique_key]
            row_data = {col: row[col] for col in dataframe.columns if col != unique_key}
            row_data = {k: (v if v is not None else "") for k, v in row_data.items()}

            entry = {
                "row_id": row_id,
                "row": row_data
            }
            payload_list.append(entry)

        return payload_list
    
    def delete_rows_seatable(self, new_data, existing_data, table_name, tab, key_columns, condition=None, platform=None):
        """
        Elimina de SeatTable las filas que aparecen en existing_data y no en new_data,
        salvo aquellas cuyo Contract Count tenga un valor (no vacío, no '0').
        """

        if platform:
            progress_reporter.add_log(platform, f"INICIANDO ELIMINACIÓN - Tabla: {table_name} - Analizando {len(existing_data)} filas existentes", level="info")

        # 1) Identificar candidatos al borrado
        to_delete = identify_records_to_delete(existing_data, new_data, key_columns)
        # Asegurar que key_columns sea lista
        keys = [key_columns] if isinstance(key_columns, str) else list(key_columns)
        
        # 2) Si hay condición y estamos en la pestaña "Infos", filtramos por contract count
        if condition is not None and "Infos" in tab:
            # Tomamos solo las columnas clave + Contract Count de existing_data
            cols = keys + ["Contract Count"]
            df = to_delete.merge(
                existing_data[cols],
                on=keys,
                how="left",
                suffixes=("", "_orig")
            )
            # Detectar filas con contrato (no NaN, no '', no '0', no 0)
            has_contract = (
                df["Contract Count"].notna() &
                (df["Contract Count"].astype(str).str.strip() != "") &
                (df["Contract Count"].astype(str).str.strip() != "0") &
                (df["Contract Count"] != 0)
            )
            # Nos quedamos solo con las filas que NO tienen contrato
            df_to_update = df.loc[has_contract, :]
            df_to_delete = df.loc[~has_contract, :]
        else:
            df_to_update = pd.DataFrame(columns=to_delete.columns)
            df_to_delete = to_delete

        # 3) Extraer los _id de las filas a borrar
        rows_ids = df_to_delete["_id"].tolist()

        # 4) Ejecutar el batch delete si hay algo que borrar
        if rows_ids:
            logger_general.info("")
            self.batch_query(
                table_name,
                rows_data=rows_ids,
                type_batch="batch_delete_rows"
            )
            if platform:
                progress_reporter.add_log(platform, f"ELIMINACIÓN COMPLETADA - Tabla: {table_name} - ELIMINADAS: {len(rows_ids)} filas")
        
        # Procesar actualizaciones (Skip Monitoring Status as it is being removed)
        if not df_to_update.empty:
            logger_general.info(f"⚠️ {len(df_to_update)} filas tienen contratos y no se eliminarán (actualización de status omitida ya que no hay campo Monitoring Status)")
            pass # No actualizamos Monitoring Status ya que será eliminado

    
    def update_rows_seatable(self, df, prev_data, table_name, FIELDS_TO_UPDATE, unique_id="MetaId", unique_id_prev=None, platform=None, enable_link=False, alternative_ids_column=None, df_source=None):
        FIELDS_TO_UPDATE = list(dict.fromkeys(FIELDS_TO_UPDATE))
        unique_id_prev = unique_id_prev or unique_id

        # Filtrar solo las columnas que necesitamos actualizar
        try:
            df_filtered = df[FIELDS_TO_UPDATE]
            logger_general.info(f"df_filtered shape: {df_filtered.shape}")
            logger_general.info(f"Columnas en df_filtered: {df_filtered.columns.tolist()}")
        except KeyError as e:
            logger_general.info(f"ERROR al filtrar columnas: {e}")
            logger_general.info(f"Columnas faltantes: {set(FIELDS_TO_UPDATE) - set(df.columns)}")
            return
        
        # SI prev_data está vacío, no hay nada que actualizar
        if prev_data.empty:
            logger_general.info(f"⚠️ prev_data para la tabla '{table_name}' está vacío. No hay registros para actualizar.")
            return

        # DEBUGGING: Verificar antes del merge
        available_cols = prev_data.columns.tolist()
        logger_general.info(f"Columnas disponibles en prev_data: {available_cols}")
        
        if '_id' not in available_cols or unique_id_prev not in available_cols:
            logger_general.error(f"❌ Error: Columnas necesarias ['_id', '{unique_id_prev}'] no están en prev_data.")
            return
        
        # Filtrar solo las columnas que necesitamos actualizar
        df_filtered = df[FIELDS_TO_UPDATE]

        if platform:
            progress_reporter.add_log(platform, f"INICIANDO ACTUALIZACIÓN - Tabla: {table_name} - {len(df)} filas a verificar")

        # Asegúrate de que '_id' está presente en 'prev_data' para poder realizar la actualización
        if '_id' not in prev_data.columns:
            raise ValueError("La columna '_id' no está presente en prev_data.")
        
        # Realizar un 'merge' entre df y prev_data usando 'MetaId' para agregar la columna '_id' a df
        # También traemos las columnas de enlace para verificar si ya existen
        link_cols = [cfg["other_column_name"] for cfg in self.link_configs]
        cols_for_merge = ['_id', unique_id_prev] + [c for c in link_cols if c in prev_data.columns]
        
        df_with_ids = pd.merge(
            df_filtered, 
            prev_data[cols_for_merge].rename(columns={unique_id_prev: unique_id}), 
            on=unique_id, 
            how='left',
            suffixes=('', '_prev')
        )

        # Crear una lista de diccionarios para enviar a batch_update_rows
        rows_to_update = []

        # Recorremos cada fila de df_filtered
        for _, row in df_with_ids.iterrows():
            row_id = row["_id"]  # Ahora obtenemos el _id de la columna que se unió

            if pd.isna(row_id):  # Si no existe _id ()
                continue  # Saltar esta fila si no tiene _id

            # Filtrar los datos de la fila de df para solo incluir las columnas que vamos a actualizar
            row_data = {col: row[col] for col in FIELDS_TO_UPDATE if col != unique_id}

            row_data = {
                col: (None if pd.isna(row[col]) else row[col])
                for col in FIELDS_TO_UPDATE if col != unique_id
            }

            # Crear el diccionario para batch_update_rows
            row_entry = {
                "row_id": row_id,  # El ID de la fila que se va a actualizar (ahora lo obtenemos de '_id')
                "row": row_data   # Los campos que se actualizarán
            }

            rows_to_update.append(row_entry)

            # --- Lógica de Linkeo durante Actualización ---
            if enable_link:
                for cfg in self.link_configs:
                    other_col = cfg["other_column_name"]
                    # Columna en el DF original (valor nuevo)
                    match_value = row.get(other_col)
                    # Columna previa (para ver si ya tiene link)
                    prev_link_col = f"{other_col}_prev" if f"{other_col}_prev" in row else other_col
                    existing_link = row.get(prev_link_col)

                    # Si no tiene link previo o queremos asegurar que esté linkeado
                    # (Como pidió el usuario: si no tenga el market debería hacer tambien el linkeo)
                    if not existing_link or existing_link == [] or existing_link == "" or (isinstance(existing_link, float) and pd.isna(existing_link)):
                        
                        # Buscar el row_id de la tabla de referencia según valor
                        link_table = cfg["table_name"]
                        other_table = cfg["other_table_name"]
                        
                        row_id_ref = None
                        match_str = str(match_value).strip() if pd.notna(match_value) else ""
                        if match_str:
                            for item in self.lookup_tables.get(link_table, []):
                                item_name = item.get("name")
                                if not item_name:
                                    continue
                                
                                found = False
                                if isinstance(item_name, list):
                                    for n in item_name:
                                        if not n: continue
                                        n_str = str(n).strip()
                                        if n_str == match_str or match_str in [part.strip() for part in n_str.split(",")]:
                                            found = True
                                            break
                                else:
                                    item_str = str(item_name).strip()
                                    if item_str == match_str or match_str in [part.strip() for part in item_str.split(",")]:
                                        found = True
                                
                                if found:
                                    row_id_ref = item["_id"]
                                    break

                        if row_id_ref:
                            link_id = self.link_ids_cache.get(link_table)
                            if link_id:
                                logger_general.info(f"🔗 Linkeo en actualización: {row_id} ({table_name}) -> {row_id_ref} ({link_table})")
                                self.perform_link_operation(link_id, row_id_ref, row_id, link_table, other_table)
                            else:
                                logger_general.info(f"⚠️ No se encontró link_id para {link_table}")
                        else:
                            logger_general.info(f"⚠️ No se encontró match_value '{match_value}' en tabla {link_table} para linkeo en actualización")


        # Realizar la actualización en lotes
        if rows_to_update:
            logger_general.info(f"🔴 Se van a actualizar {len(rows_to_update)} filas.")
            self.batch_query(table_name, rows_data=rows_to_update, type_batch="batch_update_rows", batch=1000)
            if platform:
                progress_reporter.add_log(platform, f"ACTUALIZACIÓN COMPLETADA - Tabla: {table_name} - ACTUALIZADAS: {len(rows_to_update)} filas")
        else:
            logger_general.info("No hay filas para actualizar.")


    def crud(self, df, prev_data, columns_to_update, tab, enable_link, key_columns, condition, table_name, table_to_insert=None, platform="", delete=True, custom_fn=None, insert_only=False, add_key=None, alternative_ids_column=None, df_source=None):
        if insert_only != True:
            if True == delete:
                self.delete_rows_seatable(
                    df,
                    prev_data,
                    table_name,
                    tab,
                    key_columns,
                    condition
                ) 
            self.update_rows_seatable(
                df,
                prev_data,
                table_name,
                columns_to_update,
                unique_id=key_columns[0],
                unique_id_prev=None,
                platform=platform,
                enable_link=enable_link
            )
        if add_key:
            key_columns.append(add_key)
        logger_general.info(alternative_ids_column)
        self.upload_new_records_to_seatable(
            new_data=df,
            existing_data=prev_data,
            table_name=table_name,
            key_columns=key_columns,
            enable_link=enable_link,
            table_to_insert=table_to_insert,
            platform=platform,
            custom_fn=custom_fn,
            alternative_ids_column=alternative_ids_column,
            df_source=df_source
        )
        
