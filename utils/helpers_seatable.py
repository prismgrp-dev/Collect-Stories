from collections import defaultdict
from context.context import get_urls, table_user
import pandas as pd

def get_mh_collaborators(years=None):
    """
    Devuelve una lista con todos los User IDs donde MH Collaborator == True.
    """
    rows = table_user(years)
    
    collaborators = []
    for u in rows:
        if u.get("MH Collaborator") is True and u.get("User"):
            user = u["User"]
            if isinstance(user, list):
                collaborators.extend(user)
            else:
                collaborators.append(user)
    
    return collaborators
    
def get_analysts_by_market(role="Analista", years=None):
    """
    Obtiene un diccionario de analistas agrupados por mercado/país.
    
    Args:
        role (str): Rol a filtrar en los usuarios
        years (list): Años a consultar
    
    Returns:
        dict: Diccionario con estructura {mercado: [lista_de_ids_de_analistas]}
    """
    
    # Consulta SQL para obtener usuarios
    target_rows = table_user(years)
    
    # Filtrar usuarios por rol y agrupar por mercado
    analysts_by_market = defaultdict(list)
    for u in target_rows:
        if u.get("Role") == role:
            collaborator_id = u.get("User")
            # 'Market' viene como lista de objetos; extraemos display_value de cada uno
            market_objs = u.get("Market", [])
            for m in market_objs:
                market = m.get("display_value")
                if market and collaborator_id:
                    if isinstance(collaborator_id, list):
                        analysts_by_market[market].extend(collaborator_id)
                    else:
                        analysts_by_market[market].append(collaborator_id)
    
    return analysts_by_market

def get_existing_urls_from_seatable(years=None):
    """
    Consulta Seatable para obtener todas las URLs existentes en la tabla,
    excluyendo aquellas que contengan el texto 'Thumbnail'.
    """
    try:
        print("🟩 Consultando Seatable para obtener URLs existentes...")
        print("🟩 Obteniendo URLs...")
        print(years)

        results = get_urls(years)
        print("🟩 Filtrando URLs...")
        # Filtramos las URLs que no contienen 'Thumbnail'
        existing_urls = [
            row['URL'] for row in results
            if row['URL'] and 'Thumbnail' not in row['URL']
        ]
        print("🟩 URLs encontradas: {}".format(len(existing_urls)))
        return existing_urls

    except Exception as e:
        print(f"Error al consultar Seatable: {e}")
        return []
    

def identify_records_2025(new_data, existing_data, key_columns_new=None, key_columns_existing=None):
    # 1) Si existing_data está vacío, todos los registros de new_data son nuevos
    if existing_data.empty:
        print("🟩 existing_data está vacío, todos los registros son nuevos.")
        return new_data.copy()

    # 1) Si no dan keys, tomo todas las de existing_data
    if key_columns_new is None:
        key_columns_new = list(new_data.columns)

    if key_columns_existing is None:
        key_columns_existing = list(existing_data.columns)

    # 2) Validar que las columnas clave existan en ambos DataFrames
    for col in key_columns_new:
        if col not in new_data.columns:
            raise ValueError(f"La columna '{col}' no existe en 'new_data'")
        
    for col in key_columns_existing:
        if col not in existing_data.columns:
            raise ValueError(f"La columna '{col}' no existe en 'existing_data'")

    # 3) Copias para no mutar los datos originales
    new = new_data.copy()
    exist = existing_data.copy()

    # 4) Convertir SOLO las columnas clave a string en ambos DataFrames
    for col in key_columns_new:
        new[col] = new[col].astype(str)
    for col in key_columns_existing:
        exist[col] = exist[col].astype(str)

    # 5) Eliminar duplicados en new, por si acaso hay filas idénticas
    new_unique = new.drop_duplicates(subset=key_columns_new)

    # 6) Merge para identificar los registros nuevos
    merged = new_unique.merge(
        exist[key_columns_existing],  # Solo necesitamos las columnas clave de 'existing_data'
        left_on=key_columns_new,  # Usamos la columna clave de 'new_data'
        right_on=key_columns_existing,  # Usamos la columna clave de 'existing_data'
        how="left",
        indicator=True
    )

    # 7) Filtrar registros que son solo de 'new_data'
    records = merged.loc[merged["_merge"] == "left_only", key_columns_new]

    # 8) Recuperar de 'new' todas las columnas correspondientes a los registros nuevos
    records = new.merge(
        records,
        left_on=key_columns_new,
        right_on=key_columns_new,
        how="inner"
    )

    print(f"🟩 Registros encontrados: {len(records)}")
    return records
def identify_records(new_data, existing_data, key_columns=None):
    # 1) Si existing_data está vacío, todos los registros de new_data son nuevos
    if existing_data.empty:
        print("🟩 existing_data está vacío, todos los registros son nuevos.")
        return new_data.copy()

    # 1) Si no dan keys, tomo todas las de existing_data
    if key_columns is None:
        key_columns = list(existing_data.columns)

    # 2) Validar que existan en ambos
    for col in key_columns:
        if col not in new_data.columns or col not in existing_data.columns:
            raise ValueError(f"La columna '{col}' no existe en ambos DataFrames")

    # 3) Copias para no mutar originales
    new = new_data.copy()
    exist = existing_data.copy()

    # 4) Convertir SOLO las columnas clave a string en ambos
    new[key_columns] = new[key_columns].astype(str)
    exist[key_columns] = exist[key_columns].astype(str)

    # 5) Eliminar duplicados en new, por si acaso hay filas idénticas
    new_unique = new.drop_duplicates(subset=key_columns)

    merged = new_unique.merge(
        exist[key_columns],
        on=key_columns,
        how="left",
        indicator=True
    )
    records = merged.loc[merged["_merge"] == "left_only", key_columns]

    # 7) Recuperar de 'new' todas las columnas correspondientes
    records = new.merge(
        records,
        on=key_columns,
        how="inner"
    )

    print(f"🟩 Registros encontrados: {len(records)}")
    return records

def identify_records_to_delete(existing_data, new_data, key_columns=None):
    """
    Identifica registros que están en existing_data pero NO en new_data.
    Estos son los registros que deberían ser eliminados.
    
    Args:
        existing_data: DataFrame con los datos actuales en la base de datos
        new_data: DataFrame con los datos nuevos/actualizados
        key_columns: Lista de columnas para usar como clave de comparación
    
    Returns:
        DataFrame con los registros que están en existing_data pero no en new_data
    """
    
    # 1) Si no dan keys, tomo todas las de existing_data
    if key_columns is None:
        key_columns = list(existing_data.columns)

    # 2) Validar que existan en ambos
    for col in key_columns:
        if col not in new_data.columns or col not in existing_data.columns:
            raise ValueError(f"La columna '{col}' no existe en ambos DataFrames")

    # 3) Copias para no mutar originales
    new = new_data.copy()
    exist = existing_data.copy()

    # 4) Convertir SOLO las columnas clave a string en ambos
    new[key_columns] = new[key_columns].astype(str)
    exist[key_columns] = exist[key_columns].astype(str)

    # 5) Eliminar duplicados en existing_data, por si acaso hay filas idénticas
    exist_unique = exist.drop_duplicates(subset=key_columns)

    # 6) Hacer merge desde existing_data hacia new_data
    merged = exist_unique.merge(
        new[key_columns],
        on=key_columns,
        how="left",
        indicator=True
    )
    
    # 7) Filtrar solo los que están en existing_data pero NO en new_data
    records = merged.loc[merged["_merge"] == "left_only", key_columns]

    # 8) Recuperar de 'existing_data' todas las columnas correspondientes
    records = exist.merge(
        records,
        on=key_columns,
        how="inner"
    )

    print(f"🗑️ Registros para eliminar encontrados: {len(records)}")
    return records

import pandas as pd

def find_missing_rows(df_validator: pd.DataFrame, df_compare: pd.DataFrame) -> pd.DataFrame:
    """
    Encuentra las filas en df_validator que no existen en df_compare,
    usando criterios diferentes según el tipo de publicación ("Post Type"):
    
    - Para "Post": se compara usando la columna "URL".
    - Para "Story": se compara usando la columna "Lefty Perfs Unique ID" (que corresponde a "Unique ID" en df_compare).
    
    Retorna un DataFrame solo con columnas: _id y "Missing in Lefty"
    """
    
    # Copias para no modificar originales
    df_validator_copy = df_validator.copy()
    df_compare_copy = df_compare.copy()
    
    # Limpiar NaNs y convertir a string
    for col in ["URL", "Unique ID"]:
        if col in df_validator_copy.columns:
            df_validator_copy[col] = df_validator_copy[col].fillna("").astype(str)
        if col in df_compare_copy.columns:
            df_compare_copy[col] = df_compare_copy[col].fillna("").astype(str)

    # Comparar todo lo que NO sea Story (Posts, Videos, etc.) usando URL
    posts_missing = df_validator_copy[df_validator_copy["Post Type"] != "Story"]
    posts_missing = posts_missing[~posts_missing["URL"].isin(df_compare_copy["URL"])]

    # Comparar Stories usando Unique ID
    stories_missing = df_validator_copy[df_validator_copy["Post Type"] == "Story"]
    stories_missing = stories_missing[~stories_missing["Unique ID"].isin(df_compare_copy["Unique ID"])]

    # Unir resultados
    missing_df = pd.concat([posts_missing, stories_missing], ignore_index=True)
    missing_df["Missing in Lefty"] = True
    
    return missing_df[["_id", "Unique ID", "Missing in Lefty"]]


