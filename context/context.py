
# Funciones públicas que mantienen la misma interfaz pero ahora requieren años
def table_user(years=None):
    """
    Retorna datos de usuarios combinados de los años especificados.
    Args:
        years (list): Lista de años a consultar.
    Returns:
        list: Lista combinada con datos de todas las fuentes
    """
    from utils.seatable_manager import SeatableManager
    
    if not years:
        return []

    all_data = []
    for year in years:
        data = SeatableManager.get_users(year)
        if data:
            all_data.extend(data)
    return all_data

def get_urls(years=None):
    """
    Retorna URLs combinadas de los años especificados.
    Args:
        years (list): Lista de años a consultar.
    Returns:
        list: Lista combinada con URLs de todas las fuentes
    """
    from utils.seatable_manager import SeatableManager
    
    if not years:
        return []
        
    all_urls = []
    for year in years:
        urls = SeatableManager.get_urls(year)
        if urls:
            all_urls.extend(urls)
    return all_urls
