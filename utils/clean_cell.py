import pandas as pd

# -------------------------------------------------
# Funcion para limpiar la celda
# ---------------------------------------------
def clean_cell(record):
    cleaned_record = {}
    for k, v in record.items():
        try:
            # Verificar si es None
            if v is None:
                cleaned_record[k] = None
                continue
            
            # Verificar si es un array NumPy vacío o problemático
            if hasattr(v, 'size') and hasattr(v, 'dtype'):
                # Es un array NumPy
                if v.size == 0:
                    cleaned_record[k] = None
                    continue
                elif v.size == 1:
                    # Array de un solo elemento, extraer el valor
                    try:
                        scalar_val = v.item() if hasattr(v, 'item') else v[0]
                        if pd.isna(scalar_val):
                            cleaned_record[k] = None
                        else:
                            cleaned_record[k] = scalar_val
                    except:
                        cleaned_record[k] = None
                    continue
                else:
                    # Array con múltiples elementos, convertir a lista
                    try:
                        cleaned_record[k] = v.tolist()
                    except:
                        cleaned_record[k] = str(v)
                    continue
            
            # Usar pandas isna para verificar valores NaN
            if pd.isna(v):
                cleaned_record[k] = None
            else:
                cleaned_record[k] = v
                
        except (ValueError, TypeError, AttributeError) as e:
            # Si hay cualquier error, intentar conservar el valor original
            try:
                if str(v).strip() in ['nan', 'NaN', '', 'None']:
                    cleaned_record[k] = None
                else:
                    cleaned_record[k] = v
            except:
                # Como último recurso, asignar None
                cleaned_record[k] = None
                print(f"⚠️ Advertencia: Error al limpiar campo '{k}': {e}")
            
    record = cleaned_record

    return record